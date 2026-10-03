"""
m_scene.py -- i pezzi di scena che i video di M hanno in comune: il materiale
"dipinto", le mesh di M e del triangolo, l'icosaedro, la camera, la luce, e i
conti della griglia dell'esplosione.

Niente qui legge una configurazione: tutto quello che uno script decide (nomi,
colori, tempi) arriva come argomento. I tempi in particolare restano negli
script, che sono i soli a sapere quando succede cosa: queste funzioni creano
oggetti e materiali, e i keyframe li mette chi le chiama.

NB: richiede `bpy` e `mathutils` -> eseguibile solo dentro Blender.
"""

import math
import os

import bpy
import mathutils
import numpy as np

import geometry
import pieces
import bl_utils
import bl_anim


# =============================================================================
# COLORI
# =============================================================================

def srgb_to_linear(c):
    """Una componente sRGB 0..255 in lineare 0..1: i nodi lavorano in lineare."""
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_rgba(rgb):
    """Una terna sRGB 0..255 in RGBA lineare, come la vuole un socket colore."""
    return tuple(srgb_to_linear(c) for c in rgb) + (1.0,)


# =============================================================================
# IL KIT: NOMI, COLLECTION, PULIZIA
# =============================================================================

class Kit:
    """Il contesto di uno script: il prefisso dei nomi, la collection, la
    cartella delle immagini. Tutto quello che lo script crea si chiama
    PREFIX_qualcosa, ed e' cosi' che la corsa successiva lo ritrova e lo
    cancella; prefissi diversi permettono a due script di stare nello stesso
    .blend senza pestarsi."""

    def __init__(self, prefix, collection_name, assets_dir):
        self.prefix = prefix
        self.collection_name = collection_name
        self.assets_dir = assets_dir
        self.collection = None

    def name(self, suffix):
        return f"{self.prefix}_{suffix}"

    def clear_previous_run(self):
        collection = bpy.data.collections.get(self.collection_name)
        if collection is not None:
            for obj in list(collection.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.collections.remove(collection)
        for obj in list(bpy.data.objects):
            if obj.name.startswith(self.prefix + "_"):
                bpy.data.objects.remove(obj, do_unlink=True)
        for coll in (bpy.data.meshes, bpy.data.cameras, bpy.data.lights, bpy.data.materials):
            for block in list(coll):
                if block.name.startswith(self.prefix + "_") and block.users == 0:
                    coll.remove(block)

    def new_collection(self, scene):
        self.collection = bpy.data.collections.new(self.collection_name)
        scene.collection.children.link(self.collection)
        return self.collection

    def new_object(self, suffix, data=None, parent=None):
        obj = bpy.data.objects.new(self.name(suffix), data)
        self.collection.objects.link(obj)
        if parent is not None:
            obj.parent = parent
            # le pose sono gia' nel riferimento del padre: niente compensazione
            obj.matrix_parent_inverse = mathutils.Matrix.Identity(4)
        return obj

    def load_image(self, filename):
        path = os.path.join(self.assets_dir, filename)
        if not os.path.isfile(path):
            raise RuntimeError(f"immagine non trovata: {path}")
        return bpy.data.images.load(path, check_existing=True)

    def new_material(self, suffix):
        mat = bpy.data.materials.new(self.name(suffix))
        if mat.node_tree is None:        # fino a 4.x; da 5.0 i nodi ci sono sempre
            mat.use_nodes = True
        mat.node_tree.nodes.clear()
        return mat, mat.node_tree.nodes, mat.node_tree.links


def hide_from_light(obj):
    """L'oggetto si vede ma non fa ombra e non illumina gli altri: per i
    fondali e il quadro, che sono 'dipinti' e non stanno nella scena."""
    for attr in ("visible_shadow", "visible_diffuse", "visible_glossy"):
        if hasattr(obj, attr):
            setattr(obj, attr, False)


# =============================================================================
# LA TEXTURE DELLE FACCE E I MATERIALI DI M
# =============================================================================

def face_uvs(image, uv_px, inset):
    """Le UV dei tre vertici del triangolo canonico: `uv_px` sono i vertici
    del triangolo nell'immagine, in pixel (origine in alto a sinistra), che
    rientrano di `inset` verso il baricentro."""
    w, h = image.size
    uv = np.asarray([(x / w, 1.0 - y / h) for x, y in uv_px])
    uv = uv.mean(axis=0) + (uv - uv.mean(axis=0)) * (1.0 - inset)
    return [tuple(p) for p in uv]


def texture_mean_luminance(image, uvs):
    """Luminanza media (lineare) della texture dentro il triangolo UV: e' il
    valore per cui si divide, cosi' la grana in media vale 1 e non cambia il
    colore della tavolozza. I pixel di un'immagine a 8 bit arrivano in sRGB."""
    w, h = image.size
    px = np.asarray(image.pixels[:], dtype=float).reshape(h, w, -1)[:, :, :3]
    lin = np.where(px <= 0.04045, px / 12.92, ((px + 0.055) / 1.055) ** 2.4)
    lum = lin @ np.array([0.2126, 0.7152, 0.0722])
    # centri dei pixel in coordinate UV; la riga 0 di image.pixels e' in basso
    u, v = np.meshgrid((np.arange(w) + 0.5) / w, (np.arange(h) + 0.5) / h)
    (ax, ay), (bx, by), (cx, cy) = uvs
    def side(px_, py_, x0, y0, x1, y1):
        return (x1 - x0) * (py_ - y0) - (y1 - y0) * (px_ - x0)
    s0, s1, s2 = side(u, v, ax, ay, bx, by), side(u, v, bx, by, cx, cy), side(u, v, cx, cy, ax, ay)
    inside = ((s0 >= 0) & (s1 >= 0) & (s2 >= 0)) | ((s0 <= 0) & (s1 <= 0) & (s2 <= 0))
    return float(lum[inside].mean())


def physical_face_material(kit, image, roughness):
    """La texture sulle facce, attraverso un Principled opaco: il colore e'
    quello dipinto, l'ombreggiatura la fa la luce."""
    mat, nodes, links = kit.new_material("face")
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.extension = 'EXTEND'
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Roughness"].default_value = roughness
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.2
    mat.diffuse_color = (0.15, 0.55, 0.8, 1.0)
    return mat


def painted_face_material(kit, image, uvs, palette, light_direction, grain, fade=False):
    """I colori del quadro: la normale in coordinate mondo, scalare la
    direzione da cui arriva la luce, portata a [0, 1] con (n.l + 1) / 2, va in
    una Color Ramp con la tavolozza `palette` [(posizione, sRGB)]; il colore si
    moltiplica per la grana della texture (luminanza divisa per la sua media,
    dosata da `grain`) e si emette.

    La normale e' quella in coordinate mondo, quindi il colore di una faccia
    cambia mentre M gira, come se la luce fosse ferma.

    Con fade=True l'emissione passa per un Mix Shader col Transparent, nodo
    'Fade': ingresso 0 = trasparente, 1 = opaco. Il valore di partenza e' 1."""
    mat, nodes, links = kit.new_material("face")
    out = nodes.new("ShaderNodeOutputMaterial")

    geo = nodes.new("ShaderNodeNewGeometry")
    facing = nodes.new("ShaderNodeVectorMath")
    facing.operation = 'DOT_PRODUCT'
    toward_light = -mathutils.Vector(light_direction).normalized()
    facing.inputs[1].default_value = tuple(toward_light)
    lit = nodes.new("ShaderNodeMath")
    lit.operation = 'MULTIPLY_ADD'
    lit.inputs[1].default_value = 0.5
    lit.inputs[2].default_value = 0.5
    links.new(geo.outputs["Normal"], facing.inputs[0])
    links.new(facing.outputs["Value"], lit.inputs[0])

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.name = "Palette"
    elements = ramp.color_ramp.elements
    while len(elements) < len(palette):
        elements.new(0.5)
    for element, (pos, rgb) in zip(elements, palette):
        element.position = pos
        element.color = linear_rgba(rgb)
    ramp.color_ramp.interpolation = 'LINEAR'
    links.new(lit.outputs["Value"], ramp.inputs["Fac"])

    # la grana: luminanza della texture / sua media, poi 1 + grain * (g - 1)
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.extension = 'EXTEND'
    bw = nodes.new("ShaderNodeRGBToBW")
    norm = nodes.new("ShaderNodeMath")
    norm.operation = 'DIVIDE'
    norm.inputs[1].default_value = texture_mean_luminance(image, uvs)
    grain_node = nodes.new("ShaderNodeMath")
    grain_node.operation = 'MULTIPLY_ADD'
    grain_node.inputs[1].default_value = grain
    grain_node.inputs[2].default_value = 1.0 - grain
    links.new(tex.outputs["Color"], bw.inputs["Color"])
    links.new(bw.outputs["Val"], norm.inputs[0])
    links.new(norm.outputs["Value"], grain_node.inputs[0])

    scale = nodes.new("ShaderNodeVectorMath")
    scale.operation = 'SCALE'
    links.new(ramp.outputs["Color"], scale.inputs[0])
    links.new(grain_node.outputs["Value"], scale.inputs["Scale"])
    emit = nodes.new("ShaderNodeEmission")
    links.new(scale.outputs["Vector"], emit.inputs["Color"])
    if fade:
        clear = nodes.new("ShaderNodeBsdfTransparent")
        mix = nodes.new("ShaderNodeMixShader")
        mix.name = "Fade"
        mix.inputs["Fac"].default_value = 1.0
        links.new(clear.outputs["BSDF"], mix.inputs[1])
        links.new(emit.outputs["Emission"], mix.inputs[2])
        links.new(mix.outputs["Shader"], out.inputs["Surface"])
    else:
        links.new(emit.outputs["Emission"], out.inputs["Surface"])
    mat.diffuse_color = (0.15, 0.55, 0.8, 1.0)
    return mat


FADE_PATH = 'nodes["Fade"].inputs[0].default_value'


# =============================================================================
# MESH
# =============================================================================

def triangle_mesh(kit, material, uvs):
    """Il triangolo canonico, l'unica mesh dei 240 pezzi."""
    mesh = bpy.data.meshes.new(kit.name("triangle"))
    mesh.from_pydata([v.tup() for v in pieces.CANONICAL_TRIANGLE], [], [(0, 1, 2)])
    bl_utils.set_triangle_uvs(mesh, uvs)
    mesh.materials.append(material)
    mesh.update()
    return mesh


def merged_mesh(kit, md, material, uvs):
    """M come un'unica mesh. La UV si mette prima della saldatura
    (merge_by_distance, sull'oggetto): sta sui loop, e la saldatura la
    conserva."""
    mesh = bpy.data.meshes.new(kit.name("M"))
    mesh.from_pydata(md.vertices, [], md.faces)
    bl_utils.set_triangle_uvs(mesh, uvs)
    mesh.materials.append(material)
    mesh.update()
    return mesh


def build_ico(kit, parent, md, margin, color):
    """L'icosaedro-gabbia: lo stesso Polyhedron.ico su cui e' costruita M,
    ingrandito fino a contenerla (per `margin`), come telaio di tubi. Lo
    spessore dei tubi (modifiers["Wireframe"].thickness) lo anima chi chiama.
    Restituisce (oggetto, scala)."""
    ico = geometry.Polyhedron.ico
    scale = geometry.enclosing_scale(md.vertices, ico) * margin
    mesh_md = geometry.polyhedron_mesh(ico, scale)
    mesh = bpy.data.meshes.new(kit.name("ico"))
    mesh.from_pydata(mesh_md.vertices, [], mesh_md.faces)
    mesh.materials.append(bl_utils.set_material_look(kit.name("ico"), color, roughness=0.3))
    mesh.update()
    obj = kit.new_object("ico", mesh, parent=parent)
    mod = obj.modifiers.new(name="Wireframe", type='WIREFRAME')
    mod.offset = 0.0                 # tubo centrato sullo spigolo vero
    return obj, scale


WIRE_THICKNESS_PATH = 'modifiers["Wireframe"].thickness'


# =============================================================================
# LUCE E MONDO
# =============================================================================

def build_light(kit, direction, strength):
    """Un sole che va verso `direction`."""
    light = bpy.data.lights.new(kit.name("sun"), 'SUN')
    light.energy = strength
    obj = kit.new_object("sun", light)
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = mathutils.Vector(direction).to_track_quat('-Z', 'Y')
    return obj


def setup_world(kit, seen_srgb, ambient, ambient_srgb=None):
    """Il mondo: `seen_srgb` e' il colore che vede la camera, e lo stesso
    colore (o `ambient_srgb`) attenuato di `ambient` e' la luce d'ambiente.
    Cosi' quello che si vede e quanto illumina sono separati."""
    world = bpy.data.worlds.get(kit.name("world")) or bpy.data.worlds.new(kit.name("world"))
    if world.node_tree is None:      # fino a 4.x; da 5.0 i nodi ci sono sempre
        world.use_nodes = True
    nodes, links = world.node_tree.nodes, world.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputWorld")
    seen = nodes.new("ShaderNodeBackground")
    lit = nodes.new("ShaderNodeBackground")
    path = nodes.new("ShaderNodeLightPath")
    mix = nodes.new("ShaderNodeMixShader")
    seen.inputs["Color"].default_value = linear_rgba(seen_srgb)
    lit.inputs["Color"].default_value = linear_rgba(ambient_srgb or seen_srgb)
    lit.inputs["Strength"].default_value = ambient
    links.new(path.outputs["Is Camera Ray"], mix.inputs["Fac"])
    links.new(lit.outputs["Background"], mix.inputs[1])
    links.new(seen.outputs["Background"], mix.inputs[2])
    links.new(mix.outputs["Shader"], out.inputs["Surface"])
    bpy.context.scene.world = world
    return world


# =============================================================================
# LA CAMERA
# =============================================================================

class CameraRig:
    """I conti della camera, prospettica ('PERSP') o ortografica ('ORTHO'),
    che guarda lungo +Y da `distance` davanti al punto che inquadra.

    Lo "zoom" e' la focale in mm per la prospettica e ortho_scale per
    l'ortografica: tutt'e due, con sensor_fit AUTO, si riferiscono al lato
    lungo dell'inquadratura."""

    def __init__(self, kind, distance, sensor_width, resolution):
        if kind not in ('PERSP', 'ORTHO'):
            raise ValueError(f"tipo di camera dev'essere 'PERSP' o 'ORTHO', non {kind!r}")
        self.kind = kind
        self.distance = distance
        self.sensor_width = sensor_width
        self.aspect = resolution[0] / resolution[1]

    @property
    def zoom_path(self):
        return "ortho_scale" if self.kind == 'ORTHO' else "lens"

    def location(self, center_xz):
        return mathutils.Vector((center_xz[0], -self.distance, center_xz[1]))

    def project_on_plane(self, P, eye, plane_y):
        """Proietta i punti P sul piano y = plane_y come li vede la camera in
        `eye`: dal centro di proiezione se e' prospettica, lungo Y se e'
        ortografica. Il piano e' perpendicolare all'asse ottico, quindi quello
        che combacia sul piano combacia nell'immagine."""
        if self.kind == 'ORTHO':
            Q = P.copy()
            Q[:, 1] = plane_y
            return Q
        E = np.asarray(eye, dtype=float)
        t = (plane_y - E[1]) / (P[:, 1] - E[1])
        return E + (P - E) * t[:, None]

    def frame_width(self, zoom, depth):
        """Larghezza dell'inquadratura a distanza `depth` dalla camera."""
        long_side = zoom if self.kind == 'ORTHO' else depth * self.sensor_width / zoom
        return long_side if self.aspect >= 1.0 else long_side * self.aspect

    def zoom_for_width(self, width, depth):
        """L'inverso di frame_width: lo zoom che da' quella larghezza."""
        long_side = width if self.aspect >= 1.0 else width / self.aspect
        return long_side if self.kind == 'ORTHO' else depth * self.sensor_width / long_side

    def zoom_out(self, zoom, factor):
        """Lo zoom che allarga il campo di `factor`: l'ortografica ingrandisce
        ortho_scale, la prospettica accorcia la focale. La camera non si
        sposta: spostarla cambierebbe la prospettiva."""
        return zoom * factor if self.kind == 'ORTHO' else zoom / factor

    def build(self, kit, eye, clip_end):
        """La camera nella scena, in `eye`, senza zoom ne' keyframe: li mette
        chi chiama, sul datablock (obj.data) e sul path `zoom_path`."""
        cam_data = bpy.data.cameras.new(kit.name("camera"))
        cam_data.type = self.kind
        cam_data.sensor_fit = 'AUTO'
        cam_data.sensor_width = self.sensor_width
        cam_data.clip_start = 0.1
        cam_data.clip_end = clip_end
        cam = kit.new_object("camera", cam_data)
        cam.rotation_euler = (math.pi / 2, 0.0, 0.0)     # guarda lungo +Y
        cam.location = eye
        bpy.context.scene.camera = cam
        return cam


# =============================================================================
# L'ESPLOSIONE
# =============================================================================

class Tri:
    """Un triangolo di M: il pezzo (pieces.Piece) e la sua posa in M nel
    riferimento del padre, come location + quaternione."""

    __slots__ = ("piece", "loc", "quat", "obj")

    def __init__(self, piece):
        self.piece = piece
        self.loc, self.quat = bl_anim.pose_from_matrix(piece.matrix)
        self.obj = None


def fan_ranks(tris, orient_world):
    """Ordine dei 20 ventagli per distanza dalla camera (y mondo crescente),
    con M nella posa `orient_world`; a pari distanza decide l'indice, per
    avere sempre lo stesso ordine. Restituisce {fan: rango}, 0 = il piu'
    vicino."""
    centers = {}
    for tri in tris:
        centers.setdefault(tri.piece.fan, []).append(tri.piece.center)
    depth = {fan: (orient_world @ mathutils.Vector(np.mean(c, axis=0))).y
             for fan, c in centers.items()}
    order = sorted(depth, key=lambda fan: (round(depth[fan], 9), fan))
    return {fan: rank for rank, fan in enumerate(order)}


def grid_targets(tris, orient_world, center_xz, grid, grid_y, frame_w, frame_h, fill):
    """Per ogni triangolo, la posa finale nel riferimento del padre.

    La cella e' in coordinate mondo: piano y = grid_y, rivolto alla camera
    (rotazione identita': il triangolo canonico guarda verso -Y), centrata in
    `center_xz`, scalata perche' la griglia occupi `fill` di un'inquadratura
    larga frame_w e alta frame_h a quella distanza. Il piano e' perpendicolare
    all'asse ottico, quindi anche in prospettiva i 240 triangoli si vedono
    tutti uguali. Poi la si porta nel riferimento del padre con l'inversa della
    sua matrice mondo, che deve essere quella a perno fermo.

    Restituisce (pose [(location, quaternione, scala)], posizioni mondo, scala)."""
    gw, gh = grid.extent()
    s = fill * min(frame_w / gw, frame_h / gh)

    inv = orient_world.inverted()
    q_inv = inv.to_quaternion()
    targets, world = [], []
    for tri in tris:
        x, z = grid.cell(tri.piece.fan, tri.piece.slot)
        loc_w = mathutils.Vector((center_xz[0] + s * x, grid_y, center_xz[1] + s * z))
        targets.append((inv @ loc_w, q_inv, s))
        world.append(loc_w)
    return targets, world, s


def check_targets(tris, world_targets, scene, frame):
    """Al fotogramma `frame`, quanto i triangoli distano dalla posa voluta:
    (scarto di posizione, scarto di rotazione in gradi). Si misura sulla scena
    valutata, quindi controlla anche gerarchia e keyframe, non solo i conti."""
    scene.frame_set(frame)
    miss = max((t.obj.matrix_world.translation - w).length for t, w in zip(tris, world_targets))
    # q e -q sono la stessa rotazione: l'angolo va preso modulo il giro
    tilt = max(min(a, 2 * math.pi - a) for a in (
        t.obj.matrix_world.to_quaternion().rotation_difference(mathutils.Quaternion()).angle
        for t in tris))
    return miss, math.degrees(tilt)
