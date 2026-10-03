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
# LE MISURE PRESE SUL QUADRO
# =============================================================================
#
# Sono fatti delle due immagini in saffaro/assets, non scelte di uno script:
# stanno qui perche' ogni video le usa uguali.

# La tavolozza del quadro: (posizione, sRGB). Misurata su tutti i pixel del
# poliedro dipinto in m.jpg, ordinati per luminanza: la posizione e' il
# quantile, il colore e' la mediana dei pixel attorno a quel quantile. Nel
# quadro una faccia che si scurisce non diventa grigia: la tinta ruota dal ciano
# al blu (da 192 a 221 gradi) e la saturazione resta fra 0.85 e 0.95.
#
# Con painted_face_material la posizione di una faccia e' (n.l + 1) / 2: per
# normali sparse in tutte le direzioni n.l e' uniforme, quindi quella posizione
# ha la stessa distribuzione dei quantili, e la proporzione fra toni chiari e
# scuri torna con quella del quadro -- se la luce e' perpendicolare alla
# direzione di vista, perche' la camera vede solo le facce rivolte a lei.
PAINTING_PALETTE = [
    (0.00, (2, 13, 36)),
    (0.08, (4, 37, 74)),
    (0.20, (12, 67, 106)),
    (0.35, (19, 92, 130)),
    (0.50, (24, 121, 169)),
    (0.65, (26, 137, 186)),
    (0.80, (28, 150, 199)),
    (0.92, (26, 178, 226)),
    (1.00, (30, 188, 228)),
]

# I tre vertici del triangolo azzurro in m2face_texture.png, in pixel, nello
# stesso ordine dei vertici del triangolo canonico (in alto, in basso a
# sinistra, a destra). Nell'immagine il triangolo non e' equilatero perche' e'
# ritagliato dal quadro, dove e' dipinto di scorcio. La UV rientra di
# FACE_TEXTURE_UV_INSET verso il baricentro, per non pescare i bordi scuri.
FACE_TEXTURE_FILE     = "m2face_texture.png"
FACE_TEXTURE_UV_PX    = ((109, 12), (36, 496), (452, 277))
FACE_TEXTURE_UV_INSET = 0.04


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


def _texture_in_triangle(image, uvs):
    """I pixel della texture (RGB lineare) che cadono dentro il triangolo UV.
    I pixel di un'immagine a 8 bit arrivano in sRGB."""
    w, h = image.size
    px = np.asarray(image.pixels[:], dtype=float).reshape(h, w, -1)[:, :, :3]
    lin = np.where(px <= 0.04045, px / 12.92, ((px + 0.055) / 1.055) ** 2.4)
    # centri dei pixel in coordinate UV; la riga 0 di image.pixels e' in basso
    u, v = np.meshgrid((np.arange(w) + 0.5) / w, (np.arange(h) + 0.5) / h)
    (ax, ay), (bx, by), (cx, cy) = uvs
    def side(px_, py_, x0, y0, x1, y1):
        return (x1 - x0) * (py_ - y0) - (y1 - y0) * (px_ - x0)
    s0, s1, s2 = side(u, v, ax, ay, bx, by), side(u, v, bx, by, cx, cy), side(u, v, cx, cy, ax, ay)
    inside = ((s0 >= 0) & (s1 >= 0) & (s2 >= 0)) | ((s0 <= 0) & (s1 <= 0) & (s2 <= 0))
    return lin[inside]


def texture_mean_luminance(image, uvs):
    """Luminanza media (lineare) della texture dentro il triangolo UV: e' il
    valore per cui si divide, cosi' la grana in media vale 1 e non cambia il
    colore della tavolozza."""
    lum = _texture_in_triangle(image, uvs) @ np.array([0.2126, 0.7152, 0.0722])
    return float(lum.mean())


def texture_mean_color(image, uvs):
    """Colore medio (RGBA lineare) della texture dentro il triangolo UV: la
    stessa tinta della texture, senza la grana."""
    return tuple(float(c) for c in _texture_in_triangle(image, uvs).mean(axis=0)) + (1.0,)


def physical_face_material(kit, image, roughness, uniform_color=None):
    """La texture sulle facce, attraverso un Principled opaco: il colore e'
    quello dipinto, l'ombreggiatura la fa la luce.

    Con `uniform_color` (RGBA lineare) il colore passa per un Mix, nodo
    'TextureMix': ingresso 0 = il colore uniforme, 1 = la texture. Il valore di
    partenza e' 1; lo anima chi chiama, su TEXTURE_MIX_PATH."""
    mat, nodes, links = kit.new_material("face")
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.extension = 'EXTEND'
    if uniform_color is None:
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    else:
        mix = nodes.new("ShaderNodeMix")
        mix.name = "TextureMix"
        mix.data_type = 'RGBA'
        _socket(mix.inputs, "Factor_Float").default_value = 1.0
        _socket(mix.inputs, "A_Color").default_value = tuple(uniform_color)
        links.new(tex.outputs["Color"], _socket(mix.inputs, "B_Color"))
        links.new(_socket(mix.outputs, "Result_Color"), bsdf.inputs["Base Color"])
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
TEXTURE_MIX_PATH = 'nodes["TextureMix"].inputs[0].default_value'


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
# FILI CHE SI ACCENDONO
# =============================================================================

def wire_material(kit, suffix, color, roughness=0.4, glow_property=None,
                  glow_color=(1.0, 0.85, 0.45), glow_strength=6.0):
    """Un materiale per tubi e sferette: Principled del colore `color`.

    Con `glow_property` si aggiunge un'emissione di `glow_color`, la cui forza
    e' `glow_strength` per il valore della proprieta' personalizzata
    `glow_property` dell'oggetto (nodo Attribute, tipo Object): la stessa mesh
    puo' cosi' accendersi su un oggetto e restare spenta su un altro, e il
    valore si anima con un keyframe su '["nome"]'. Se l'oggetto non ha la
    proprieta' vale 0. Funziona in Cycles e in EEVEE; il bagliore attorno lo fa
    il compositor (setup_glare)."""
    mat, nodes, links = kit.new_material(suffix)
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = tuple(color[:3]) + (1.0,)
    bsdf.inputs["Roughness"].default_value = roughness
    mat.diffuse_color = tuple(color[:3]) + (1.0,)
    if glow_property is None:
        links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
        return mat
    attr = nodes.new("ShaderNodeAttribute")
    attr.attribute_type = 'OBJECT'
    attr.attribute_name = glow_property
    gain = nodes.new("ShaderNodeMath")
    gain.operation = 'MULTIPLY'
    gain.inputs[1].default_value = glow_strength
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = tuple(glow_color[:3]) + (1.0,)
    add = nodes.new("ShaderNodeAddShader")
    links.new(attr.outputs["Fac"], gain.inputs[0])
    links.new(gain.outputs["Value"], emit.inputs["Strength"])
    links.new(bsdf.outputs["BSDF"], add.inputs[0])
    links.new(emit.outputs["Emission"], add.inputs[1])
    links.new(add.outputs["Shader"], out.inputs["Surface"])
    return mat


def setup_glare(kit, scene, threshold=1.0, strength=1.0, size=0.5):
    """Il bagliore attorno a quello che e' piu' luminoso di `threshold`: un
    compositor Render Layers -> Glare (Bloom) -> uscita. API di Blender 5.x,
    dove il compositor e' un node group assegnato a scene.compositing_node_group.

    Sostituisce il compositor della scena: se ne avevi uno fatto a mano, va
    rimesso. Con threshold 1 i colori 'normali' non brillano; brillano le
    emissioni piu' forti di 1, cioe' i fili accesi."""
    if not hasattr(scene, "compositing_node_group"):
        raise RuntimeError("setup_glare richiede Blender 5.x (scene.compositing_node_group)")
    name = kit.name("compositor")
    ng = bpy.data.node_groups.get(name) or bpy.data.node_groups.new(name, 'CompositorNodeTree')
    ng.nodes.clear()
    ng.interface.clear()
    ng.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
    layers = ng.nodes.new("CompositorNodeRLayers")
    glare = ng.nodes.new("CompositorNodeGlare")
    out = ng.nodes.new("NodeGroupOutput")
    glare.inputs["Type"].default_value = 'Bloom'
    _socket(glare.inputs, "Highlights Threshold").default_value = threshold
    glare.inputs["Strength"].default_value = strength
    glare.inputs["Size"].default_value = size
    ng.links.new(layers.outputs["Image"], glare.inputs["Image"])
    ng.links.new(glare.outputs["Image"], out.inputs[0])
    scene.compositing_node_group = ng
    scene.render.use_compositing = True
    return ng


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


def sky_rotation(toward_sun):
    """Il sun_rotation del nodo Sky Texture che mette il sole nella direzione
    orizzontale di `toward_sun` (dal centro verso il sole).

    Convenzione misurata in Blender 5.1, renderizzando il cielo con una camera
    equirettangolare: con elevazione e e rotazione r il sole sta in direzione
    (cos e sin r, cos e cos r, sin e), cioe' r = 0 lo mette a +Y e r = 90 gradi
    a +X. La documentazione non lo dice, e la proprieta' sun_direction del nodo
    non c'entra (e' dei modelli di cielo vecchi)."""
    return math.atan2(toward_sun[0], toward_sun[1])


def setup_sky_world(kit, sun_elevation, sun_rotation, strength, sun_size=None):
    """Il mondo come cielo fisico (Sky Texture, il modello di default), con il
    sole all'elevazione e alla rotazione date (radianti; si veda sky_rotation).
    Il cielo illumina la scena e, dove non c'e' altro davanti, si vede.

    `strength` scala tutto: il cielo di Blender e' in unita' fisiche, e con
    strength 1 e la vista 'Standard' una superficie al sole e' molto piu'
    chiara di 1, quindi va tarata guardando i render."""
    world = bpy.data.worlds.get(kit.name("world")) or bpy.data.worlds.new(kit.name("world"))
    if world.node_tree is None:      # fino a 4.x; da 5.0 i nodi ci sono sempre
        world.use_nodes = True
    nodes, links = world.node_tree.nodes, world.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputWorld")
    sky = nodes.new("ShaderNodeTexSky")
    sky.sun_elevation = sun_elevation
    sky.sun_rotation = sun_rotation
    if sun_size is not None:
        sky.sun_size = sun_size
    bg = nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = strength
    links.new(sky.outputs["Color"], bg.inputs["Color"])
    links.new(bg.outputs["Background"], out.inputs["Surface"])
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
# IL FONDO SFUMATO
# =============================================================================

def _socket(sockets, identifier):
    return next(s for s in sockets if s.identifier == identifier)


def background_material(kit, corners_srgb):
    """Emissione della sfumatura bilineare fra i quattro angoli (chiavi
    top_left, top_right, bottom_left, bottom_right, colori sRGB), sulle UV del
    piano: 0,0 in basso a sinistra. La sfumatura e' fatta in colori lineari."""
    mat, nodes, links = kit.new_material("background")
    out = nodes.new("ShaderNodeOutputMaterial")
    coord = nodes.new("ShaderNodeTexCoord")
    xyz = nodes.new("ShaderNodeSeparateXYZ")
    links.new(coord.outputs["UV"], xyz.inputs[0])

    def mix(factor, a, b):
        node = nodes.new("ShaderNodeMix")
        node.data_type = 'RGBA'
        links.new(factor, _socket(node.inputs, "Factor_Float"))
        for socket, value in ((_socket(node.inputs, "A_Color"), a), (_socket(node.inputs, "B_Color"), b)):
            if isinstance(value, tuple):
                socket.default_value = value
            else:
                links.new(value, socket)
        return _socket(node.outputs, "Result_Color")

    c = {k: linear_rgba(v) for k, v in corners_srgb.items()}
    bottom = mix(xyz.outputs["X"], c["bottom_left"], c["bottom_right"])
    top = mix(xyz.outputs["X"], c["top_left"], c["top_right"])
    color = mix(xyz.outputs["Y"], bottom, top)
    emit = nodes.new("ShaderNodeEmission")
    links.new(color, emit.inputs["Color"])
    links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


def build_background(kit, rig, cam, zoom, depth, corners_srgb, bleed):
    """Il fondo: un piano figlio della camera, a distanza `depth` davanti a
    lei, grande esattamente quanto l'inquadratura con lo zoom `zoom` (piu'
    `bleed`, per non vederne il bordo), con la sfumatura dei quattro angoli.

    Un driver lo scala con lo zoom della camera, perche' resti grande quanto
    l'inquadratura anche quando la camera allarga il campo. E' un'espressione
    semplice (una divisione), che Blender valuta senza Python: funziona anche
    con l'esecuzione automatica degli script disattivata."""
    w = rig.frame_width(zoom, depth) * bleed
    h = w / rig.aspect
    mesh = bpy.data.meshes.new(kit.name("background"))
    # nel riferimento della camera: X a destra, Y in alto, si guarda lungo -Z
    mesh.from_pydata([(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0),
                      (w / 2, h / 2, 0), (-w / 2, h / 2, 0)], [], [(0, 1, 2, 3)])
    layer = mesh.uv_layers.new(name="UVMap")
    for li, uv in zip(mesh.polygons[0].loop_indices, ((0, 0), (1, 0), (1, 1), (0, 1))):
        layer.data[li].uv = uv
    mesh.materials.append(background_material(kit, corners_srgb))
    obj = kit.new_object("background", mesh, parent=cam)
    obj.location = (0.0, 0.0, -depth)
    hide_from_light(obj)

    # larghezza dell'inquadratura: proporzionale a ortho_scale, inversa della focale
    var = rig.zoom_path
    expr = f"{var} / {zoom!r}" if rig.kind == 'ORTHO' else f"{zoom!r} / {var}"
    for axis in (0, 1):
        fcurve = obj.driver_add("scale", axis)
        driver = fcurve.driver
        driver.type = 'SCRIPTED'
        v = driver.variables.new()
        v.name = var
        v.type = 'SINGLE_PROP'
        v.targets[0].id_type = 'CAMERA'
        v.targets[0].id = cam.data
        v.targets[0].data_path = var
        driver.expression = expr
    return obj


def mean_srgb(colors):
    """Il colore medio di una collezione di terne sRGB."""
    colors = list(colors)
    return tuple(sum(c[i] for c in colors) / len(colors) for i in range(3))


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
