"""
scene_1.py -- dal quadro di Saffaro a M, all'icosaedro e ai solidi platonici,
e di nuovo a M che esplode nei suoi 240 triangoli.

--------------------------------------------------------------------------
LA SCALETTA (secondi, a 24 fps)
--------------------------------------------------------------------------
   0          il quadro, alto quanto l'inquadratura e centrato
  10 - 11     il quadro si dissolve: resta M, nella stessa posa e con i colori
              del quadro, sul fondo scuro sfumato
  11 - 13     il materiale di M passa con continuita' dai colori del quadro a
              un fisico pastello (stessa texture)
  12          M comincia a girare lentamente su se stessa (ease in)
  19 - 20     compare lo scheletro dell'icosaedro (giallo pastello), solidale
              con M
  24          M si dissolve e compaiono le facce dell'icosaedro (scala da 0 a
              0.9: non toccano lo scheletro); la transizione dura un secondo
  27          compaiono uno dopo l'altro i 5 solidi platonici, in colonna a
              sinistra: solo le facce, azzurro pastello opaco all'80%
  37 - 38     solidi e icosaedro si dissolvono mentre M ricompare: per un
              istante si vedono, semitrasparenti, tutti e due
  37 - 40     la rotazione di M rallenta fino a fermarsi (ease out)
  45 - 48     l'esplosione: ogni triangolo si allontana dal centro lungo la sua
              normale e poi, con una curva senza spigoli, va alla sua cella;
              20 gruppi da 12 (5 x 4 gruppi, 4 x 3 triangoli), su un piano
              parallelo allo schermo
  48 - 53     tutto fermo

--------------------------------------------------------------------------
LE SCELTE
--------------------------------------------------------------------------
* La camera e' prospettica e ferma per tutta la scena. Guarda il centro del
  quadro, e il quadro e' scalato e spostato perche' il poliedro dipinto
  combaci con M visto dalla camera (come in M_video): M quindi sta un po' piu'
  in alto del centro dell'immagine, dove sta nel quadro.
* Il materiale di M e' uno solo (m_scene.look_face_material), con due nodi
  animati: 'Look' (dal quadro al pastello) e 'Fade' (la dissolvenza). Lo usano
  anche i 240 triangoli dell'esplosione.
* I colori pastello hanno tutti la stessa luminosita' e saturazione in OKLCH.
* Niente di quello che compare dopo il quadro fa ombra. M e i triangoli
  nemmeno: sono concavi, e un'ombra netta li taglierebbe in due colori (si veda
  M_story).
* Le dissolvenze di oggetti opachi in Cycles lasciano intravedere le facce
  posteriori: e' la semitrasparenza vera.

Una sola scena, tutto in keyframe (nessun handler), script idempotente, nomi
col prefisso S1_.
"""

import bpy
import bmesh
import mathutils

import os, sys
import math
import importlib

import numpy as np

# rendi possibile importare i moduli da src/libs
# (nota bene: __file__ non funziona dallo script editor di Blender,
#  quindi si ricava il path del file dal datablock di testo attivo)
def _find_libs_dir():
    txt = getattr(getattr(bpy.context, "space_data", None), "text", None)
    if txt is None:  # lo script non gira dal Text Editor: cerco il datablock per nome
        txt = bpy.data.texts.get("scene_1.py")
    if txt is None or not txt.filepath:
        raise RuntimeError(
            "non riesco a ricavare il path dello script: il testo non e' salvato "
            "su disco (Text > Save As) oppure e' un blocco 'interno'"
        )
    # attenzione: se il file e' stato aperto con l'opzione 'Relative Path' spuntata,
    # filepath e' del tipo '//../...' (relativo al .blend) e os.path lo interpreta
    # come percorso UNC. bpy.path.abspath lo risolve; sugli assoluti non fa nulla.
    path = os.path.abspath(bpy.path.abspath(txt.filepath))
    # script in src/scripts, librerie in src/libs
    libs = os.path.join(os.path.dirname(os.path.dirname(path)), "libs")
    if not os.path.isdir(libs):
        raise RuntimeError(f"cartella libs non trovata: {libs}  (filepath: {txt.filepath})")
    return libs


_LIBS = _find_libs_dir()
if _LIBS not in sys.path:
    sys.path.insert(0, _LIBS)

# questo serve nel caso che tu faccia modifiche ai moduli senza interrompere la sessione di Blender
import geometry, bl_utils, extended_face, pieces, bl_anim, m_scene, story
for _mod in (geometry, bl_utils, extended_face, pieces, bl_anim, m_scene, story):
    importlib.reload(_mod)

from mathutils import Vector
from bl_anim import Key


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

PREFIX          = "S1"
COLLECTION_NAME = "scene_1"

# saffaro/assets, accanto al repository: src/libs -> src -> saffaro-delthedra -> saffaro
ASSETS_DIR    = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(_LIBS))), "assets")

# Quello che scene_2 deve ritrovare uguale per raccordarsi -- la posa di M nel
# quadro, la camera, la griglia, i colori, il fondo, la luce -- sta in
# libs/story.py: qui ci sono solo le scelte di questa scena.
FPS         = story.FPS
RESOLUTION  = story.RESOLUTION
FRAME_START = 1

# --- la scaletta, in secondi ---
PAINT_FADE      = (10.0, 11.0)   # il quadro si dissolve
LOOK_CHANGE     = (11.0, 13.0)   # M: dai colori del quadro al pastello fisico
SPIN_START      = 12.0           # M comincia a girare (ease in)
SPIN_RAMP       = 2.0            # ... raggiungendo la velocita' in tanti secondi
SPIN_STOP       = (37.0, 40.0)   # ... e rallenta fino a fermarsi
SPIN_SECONDS_PER_TURN = 20.0
SKELETON_IN     = (19.0, 20.0)   # lo scheletro dell'icosaedro compare
M_OUT           = (24.0, 24.6)   # M si dissolve...
ICO_FACES_IN    = (24.4, 25.0)   # ... e intanto crescono le facce dell'icosaedro
SOLIDS_IN       = 27.0           # il primo solido platonico comincia a comparire
SOLIDS_GAP      = 0.4            # fra un solido e il successivo
SOLIDS_FADE     = 0.8            # quanto ci mette uno a comparire
CROSSFADE       = (37.0, 38.0)   # solidi e icosaedro via, M di nuovo
EXPLODE         = (45.0, 48.0)   # l'esplosione
HOLD_SECONDS    = 5.0            # immagine ferma, alla fine

# --- i colori: pastello, stessa luminosita' e saturazione in OKLCH (story.pastel) ---
SKELETON_HUE = 100.0             # lo scheletro dell'icosaedro: giallo
ICO_FACE_HUE = 35.0              # le facce dell'icosaedro: corallo
SOLIDS_HUE   = 235.0             # i solidi platonici: azzurro (a 215 e' un ciano, che al sole vira al verde acqua)
SOLIDS_OPACITY = 0.8

# --- l'icosaedro ---
ICO_MARGIN       = story.ICO_MARGIN   # la gabbia di M: tangente ai suoi 30 spigoli (M_ico)
ICO_TUBE_RADIUS  = 0.04          # cilindretti e sferette
ICO_FACE_SCALE   = 0.9           # le facce non toccano lo scheletro

# --- i solidi platonici ---
# In colonna a sinistra: x e altezze nell'immagine (frazioni), e diametro di
# ognuno come frazione dell'altezza dell'immagine.
SOLIDS_X        = 0.12
SOLIDS_Y        = (0.86, 0.68, 0.50, 0.32, 0.14)
SOLIDS_DIAMETER = 0.14
SOLIDS_EULER_DEG = (20.0, 0.0, 25.0)

# --- l'esplosione (la griglia e' story.GRID) ---
STAGGER_SECONDS = 0.8            # fra il primo triangolo che parte e l'ultimo
POP_DISTANCE    = 1.5            # quanto si allontana lungo la normale, prima di girare
ARRIVAL_PULL    = 0.4            # quanto l'arrivo tiene della direzione di partenza


# =============================================================================
# LA REGIA
# =============================================================================

T_END     = EXPLODE[1] + HOLD_SECONDS
FRAME_END = FRAME_START + int(round(T_END * FPS))


def frame_of(t):
    return FRAME_START + int(round(t * FPS))


def time_of(frame):
    return (frame - FRAME_START) / FPS


def ramp(t, t0, t1):
    return min(1.0, max(0.0, (t - t0) / (t1 - t0)))


def ease_inout(u):
    return u * u * (3.0 - 2.0 * u)


def _check_schedule():
    marks = [0.0, PAINT_FADE[0], PAINT_FADE[1], SPIN_START, SKELETON_IN[0], M_OUT[0],
             SOLIDS_IN, CROSSFADE[0], SPIN_STOP[1], EXPLODE[0], EXPLODE[1], T_END]
    if marks != sorted(marks):
        raise ValueError(f"scaletta fuori ordine: {marks}")
    if SPIN_START + SPIN_RAMP > SPIN_STOP[0]:
        raise ValueError("SPIN_RAMP: la rotazione non fa in tempo a partire")


def spin_angles():
    """{frame: angolo} del perno: velocita' che sale da zero con un raccordo a
    coseno (SPIN_RAMP), costante, e scende a zero allo stesso modo fra
    SPIN_STOP[0] e SPIN_STOP[1]. Integrata fotogramma per fotogramma."""
    omega = 2.0 * math.pi / SPIN_SECONDS_PER_TURN            # radianti al secondo

    def speed(t):
        if t <= SPIN_START or t >= SPIN_STOP[1]:
            return 0.0
        if t < SPIN_START + SPIN_RAMP:
            k = (t - SPIN_START) / SPIN_RAMP
        elif t > SPIN_STOP[0]:
            k = (SPIN_STOP[1] - t) / (SPIN_STOP[1] - SPIN_STOP[0])
        else:
            k = 1.0
        return omega * (1.0 - math.cos(math.pi * k)) / 2.0

    angles, a, steps = {}, 0.0, 16
    for f in range(FRAME_START, FRAME_END + 1):
        angles[f] = a
        t = time_of(f)
        a += sum(speed(t + (i + 0.5) / (steps * FPS)) for i in range(steps)) / (steps * FPS)
    return angles


orient_matrix = story.orient_matrix
pastel = story.pastel


# =============================================================================
# L'ESPLOSIONE
# =============================================================================

def bezier(p0, p1, p2, p3, u):
    v = 1.0 - u
    return p0 * v ** 3 + p1 * (3 * v * v * u) + p2 * (3 * v * u * u) + p3 * u ** 3


def explosion_keys(tri, target, rank):
    """Keyframe del triangolo, uno per fotogramma durante il suo volo.

    La traiettoria e' una curva di Bezier cubica: parte lungo la normale della
    faccia (si allontana dal centro del solido) e arriva sulla cella, e una
    Bezier non ha spigoli. Il secondo punto di controllo e' a POP_DISTANCE
    lungo la normale; il terzo sta fra il secondo e la cella (ARRIVAL_PULL),
    cosi' l'arrivo eredita un po' della direzione di partenza invece di
    piegare di colpo. Rotazione (slerp) e scala seguono lo stesso parametro."""
    loc_t, quat_t, scale_t = target
    p0 = tri.loc
    p1 = tri.loc + Vector(tri.piece.normal) * POP_DISTANCE
    p3 = loc_t
    p2 = p3 + (p1 - p3) * ARRIVAL_PULL
    fly = (EXPLODE[1] - EXPLODE[0]) - STAGGER_SECONDS
    t1 = EXPLODE[0] + STAGGER_SECONDS * rank / 19.0
    f1, f2 = frame_of(t1), frame_of(t1 + fly)
    keys = [Key(FRAME_START, tri.loc, tri.quat, 1.0)]
    for f in range(f1, f2 + 1):
        u = ease_inout(ramp(time_of(f), t1, t1 + fly))
        keys.append(Key(f, bezier(p0, p1, p2, p3, u), tri.quat.slerp(quat_t, u),
                        1.0 + (scale_t - 1.0) * u))
    return keys


# =============================================================================
# COSTRUZIONE
# =============================================================================

KIT = m_scene.Kit(PREFIX, COLLECTION_NAME, ASSETS_DIR)
CAMERA = story.camera_rig()


def fade(mat, keys):
    """Keyframe del nodo 'Fade' del materiale: (secondi, valore)."""
    bl_anim.key_value(mat.node_tree, m_scene.FADE_PATH, [(frame_of(t), v) for t, v in keys])


def visible_between(obj, t0, t1=None):
    """Visibile da t0 a t1 (secondi): fuori non serve renderizzarlo."""
    changes = [(FRAME_START, t0 <= 0.0)]
    if t0 > 0.0:
        changes.append((frame_of(t0) - 1, True))
    if t1 is not None:
        changes.append((frame_of(t1) + 1, False))
    bl_anim.key_visibility(obj, changes)


def build_painting(image, center, height, width, depth):
    mesh = bpy.data.meshes.new(KIT.name("painting"))
    mesh.from_pydata([(-width / 2, 0, -height / 2), (width / 2, 0, -height / 2),
                      (width / 2, 0, height / 2), (-width / 2, 0, height / 2)], [], [(0, 1, 2, 3)])
    layer = mesh.uv_layers.new(name="UVMap")
    for li, uv in zip(mesh.polygons[0].loop_indices, ((0, 0), (1, 0), (1, 1), (0, 1))):
        layer.data[li].uv = uv
    mat, nodes, links = KIT.new_material("painting")
    out = nodes.new("ShaderNodeOutputMaterial")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    emit = nodes.new("ShaderNodeEmission")
    clear = nodes.new("ShaderNodeBsdfTransparent")
    mix = nodes.new("ShaderNodeMixShader")
    mix.name = "Fade"
    mix.inputs["Fac"].default_value = 1.0
    links.new(tex.outputs["Color"], emit.inputs["Color"])
    links.new(clear.outputs["BSDF"], mix.inputs[1])
    links.new(emit.outputs["Emission"], mix.inputs[2])
    links.new(mix.outputs["Shader"], out.inputs["Surface"])
    bl_utils.set_blended(mat)
    mesh.materials.append(mat)
    obj = KIT.new_object("painting", mesh)
    obj.location = (center[0], depth, center[1])
    m_scene.hide_from_light(obj)
    fade(mat, [(PAINT_FADE[0], 1.0), (PAINT_FADE[1], 0.0)])
    visible_between(obj, 0.0, PAINT_FADE[1])
    return obj


def build_icosahedron(orient, md):
    """Lo scheletro e le 20 facce dell'icosaedro-gabbia di M, figli di
    MV_orient: girano con M."""
    ico = geometry.Polyhedron.ico
    scale = geometry.enclosing_scale(md.vertices, ico) * ICO_MARGIN
    V = [np.asarray(v.tup()) * scale for v in ico.vertices]
    edges = sorted({tuple(sorted((f[k], f[(k + 1) % 3]))) for f in ico.faces for k in range(3)})

    yellow = m_scene.fading_material(KIT, "skeleton", pastel(SKELETON_HUE), roughness=0.4)
    skeleton = KIT.new_object("skeleton", m_scene.skeleton_mesh(KIT, "skeleton", V, edges,
                                                                ICO_TUBE_RADIUS, yellow), parent=orient)
    skeleton.visible_shadow = False
    fade(yellow, [(SKELETON_IN[0], 0.0), (SKELETON_IN[1], 1.0),
                  (CROSSFADE[0], 1.0), (CROSSFADE[1], 0.0)])
    visible_between(skeleton, SKELETON_IN[0], CROSSFADE[1])

    coral = m_scene.fading_material(KIT, "ico_faces", pastel(ICO_FACE_HUE), roughness=0.5)
    fade(coral, [(0.0, 1.0), (CROSSFADE[0], 1.0), (CROSSFADE[1], 0.0)])
    faces = []
    for n, f in enumerate(ico.faces):
        c = sum(V[i] for i in f) / 3.0
        mesh = bpy.data.meshes.new(KIT.name(f"ico_face_{n:02d}"))
        mesh.from_pydata([tuple(V[i] - c) for i in f], [], [(0, 1, 2)])
        mesh.materials.append(coral)
        obj = KIT.new_object(f"ico_face_{n:02d}", mesh, parent=orient)
        obj.location = tuple(c)
        obj.visible_shadow = False
        # scala attorno al baricentro: a 0.9 resta un bordo libero verso lo scheletro
        bl_anim.key_value(obj, "scale", [(frame_of(ICO_FACES_IN[0]), (0.0,) * 3),
                                         (frame_of(ICO_FACES_IN[1]), (ICO_FACE_SCALE,) * 3)])
        visible_between(obj, ICO_FACES_IN[0], CROSSFADE[1])
        faces.append(obj)
    return skeleton, faces, scale


def platonic_solids():
    """I cinque solidi platonici, inscritti nella sfera unitaria: [(nome,
    vertici)]. Le facce le trova l'inviluppo convesso."""
    phi = (1.0 + 5.0 ** 0.5) / 2.0
    tetra = [(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)]
    cube = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    octa = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    dodeca = cube + [(0, s / phi, t * phi) for s in (-1, 1) for t in (-1, 1)] \
        + [(s / phi, t * phi, 0) for s in (-1, 1) for t in (-1, 1)] \
        + [(s * phi, 0, t / phi) for s in (-1, 1) for t in (-1, 1)]
    icosa = [v.tup() for v in geometry.Polyhedron.ico.vertices]
    out = []
    for name, verts in (("tetrahedron", tetra), ("cube", cube), ("octahedron", octa),
                        ("dodecahedron", dodeca), ("icosahedron", icosa)):
        V = np.asarray(verts, dtype=float)
        out.append((name, V / np.linalg.norm(V, axis=1).max()))
    return out


def convex_mesh(name, vertices, material):
    """La mesh dell'inviluppo convesso, con le facce complanari fuse (i
    quadrati del cubo, i pentagoni del dodecaedro)."""
    bm = bmesh.new()
    for v in vertices:
        bm.verts.new(v)
    bmesh.ops.convex_hull(bm, input=bm.verts)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=bm.verts, edges=bm.edges)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(KIT.name(name))
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(material)
    return mesh


def build_solids(eye, lens):
    """I cinque solidi in colonna a sinistra, sul piano y = 0: posizioni e
    grandezza in frazioni dell'immagine, tradotte nel mondo con la camera."""
    depth = -eye.y
    fw = CAMERA.frame_width(lens, depth)
    fh = fw / CAMERA.aspect
    radius = SOLIDS_DIAMETER * fh / 2.0
    out = []
    for n, ((name, V), fy) in enumerate(zip(platonic_solids(), SOLIDS_Y)):
        mat = m_scene.fading_material(KIT, f"solid_{name}", pastel(SOLIDS_HUE), roughness=0.4)
        t0 = SOLIDS_IN + n * SOLIDS_GAP
        fade(mat, [(t0, 0.0), (t0 + SOLIDS_FADE, SOLIDS_OPACITY),
                   (CROSSFADE[0], SOLIDS_OPACITY), (CROSSFADE[1], 0.0)])
        obj = KIT.new_object(name, convex_mesh(name, V * radius, mat))
        obj.location = (eye.x + (SOLIDS_X - 0.5) * fw, 0.0, eye.z + (fy - 0.5) * fh)
        obj.rotation_euler = [math.radians(a) for a in SOLIDS_EULER_DEG]
        obj.visible_shadow = False
        visible_between(obj, t0, CROSSFADE[1])
        out.append(obj)
    return out


def build():
    _check_schedule()
    KIT.clear_previous_run()
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.render.resolution_x, scene.render.resolution_y = RESOLUTION
    scene.frame_start, scene.frame_end = FRAME_START, FRAME_END
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    if hasattr(scene, "cycles"):
        # le dissolvenze sovrappongono parecchie superfici semitrasparenti
        scene.cycles.transparent_max_bounces = 32
    KIT.new_collection(scene)

    md = extended_face.make_M()
    ico_scale = geometry.enclosing_scale(md.vertices, geometry.Polyhedron.ico) * ICO_MARGIN

    # --- il quadro e la camera: story.Layout, la stessa inquadratura di scene_2 ---
    painting_img = KIT.load_image(story.PAINTING_FILE)
    layout = story.Layout(md, painting_img.size)
    p_center, p_height, p_width = layout.painting_center, layout.painting_height, layout.painting_width
    p_depth, eye, lens = layout.painting_depth, layout.eye, layout.lens
    story.build_camera_and_world(KIT, layout, clip_end=story.CAMERA_DISTANCE + story.GRID_DEPTH + 30.0)
    build_painting(painting_img, p_center, p_height, p_width, p_depth)

    # --- M ---
    face_img = KIT.load_image(m_scene.FACE_TEXTURE_FILE)
    uvs = m_scene.face_uvs(face_img, m_scene.FACE_TEXTURE_UV_PX, m_scene.FACE_TEXTURE_UV_INSET)
    m_mat = story.face_material(KIT, face_img, uvs)
    bl_anim.key_value(m_mat.node_tree, m_scene.LOOK_PATH,
                      [(frame_of(LOOK_CHANGE[0]), 0.0), (frame_of(LOOK_CHANGE[1]), 1.0)])
    fade(m_mat, [(M_OUT[0], 1.0), (M_OUT[1], 0.0), (CROSSFADE[0], 0.0), (CROSSFADE[1], 1.0)])

    spin = spin_angles()
    pivot = KIT.new_object("pivot")
    pivot.empty_display_size = 0.5
    bl_anim.apply_euler_keys(pivot, [(f, (0.0, 0.0, a)) for f, a in spin.items()
                                     if SPIN_START * FPS - 2 <= f - FRAME_START <= SPIN_STOP[1] * FPS + 2
                                     or f in (FRAME_START, FRAME_END)])
    bl_anim.set_interpolation(pivot, 'LINEAR', ("rotation_euler",))
    orient = KIT.new_object("orient", parent=pivot)
    orient.empty_display_type = 'ARROWS'
    orient.rotation_euler = [math.radians(a) for a in story.ORIENT_EULER_DEG]
    orient_world = mathutils.Matrix.Rotation(spin[FRAME_END], 4, 'Z') @ orient_matrix()

    m_obj = KIT.new_object("M", m_scene.merged_mesh(KIT, md, m_mat, uvs), parent=orient)
    bl_utils.merge_by_distance(m_obj)
    m_obj.visible_shadow = False
    bl_anim.key_visibility(m_obj, [(FRAME_START, True), (frame_of(M_OUT[1]) + 1, False),
                                   (frame_of(CROSSFADE[0]) - 1, True), (frame_of(EXPLODE[0]), False)])

    # --- icosaedro e solidi ---
    build_icosahedron(orient, md)
    build_solids(eye, lens)

    # --- i 240 triangoli ---
    mesh = m_scene.triangle_mesh(KIT, m_mat, uvs)
    tris = [m_scene.Tri(p) for p in pieces.m_pieces(md)]
    targets, world_targets, grid_scale = layout.grid(tris, orient_world)
    ranks = m_scene.fan_ranks(tris, orient_world)
    for tri, target in zip(tris, targets):
        obj = KIT.new_object(f"tri_{tri.piece.index:03d}", mesh, parent=orient)
        obj.visible_shadow = False
        tri.obj = obj
        bl_anim.apply_keys(obj, explosion_keys(tri, target, ranks[tri.piece.fan]))
        bl_anim.set_interpolation(obj, 'LINEAR', bl_anim.POSE_PATHS)
        bl_anim.key_visibility(obj, [(FRAME_START, False), (frame_of(EXPLODE[0]), True)])

    miss, tilt = m_scene.check_targets(tris, world_targets, scene, FRAME_END)
    scene.frame_set(FRAME_START)

    print(f"[scene_1] frame {FRAME_START}-{FRAME_END} a {FPS} fps ({T_END:.1f} s)")
    print(f"[scene_1] quadro alto {p_height:.3f} sul piano y = {p_depth:.2f}, camera in "
          f"({eye.x:.3f}, {eye.y:.1f}, {eye.z:.3f}) con focale {lens:.2f} mm")
    print(f"[scene_1] M gira {spin[FRAME_END] / (2 * math.pi):.3f} giri fra {SPIN_START} e "
          f"{SPIN_STOP[1]} s; gabbia a scala {ico_scale:.4f}; triangoli scalati a {grid_scale:.3f}")
    print(f"[scene_1] a fine esplosione: scarto di posizione {miss:.2e}, di rotazione {tilt:.2e} gradi")
    return tris


TRIS = build()
