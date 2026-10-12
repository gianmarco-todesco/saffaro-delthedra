"""
v2/scene-1.py -- dal quadro di Saffaro a M, all'icosaedro, e di nuovo a M che
esplode nei suoi 240 triangoli. E' scene_1.py coi tempi della seconda versione
del video, e senza i solidi platonici.

--------------------------------------------------------------------------
LA SCALETTA (secondi, a 24 fps)
--------------------------------------------------------------------------
   0          il quadro, alto quanto l'inquadratura e centrato
   8 - 9      il quadro si dissolve: resta M, nella stessa posa e con i colori
              del quadro, sul fondo scuro sfumato
   9 - 11     il materiale di M passa con continuita' dai colori del quadro a
              un fisico pastello (stessa texture)
  10          M comincia a girare lentamente su se stessa (ease in)
  15 - 16     compare lo scheletro dell'icosaedro (giallo pastello), solidale
              con M
  20 - 21     M si dissolve
  20.5 - 21.5 crescono le facce dell'icosaedro (scala da 0 a ICO_FACE_SCALE:
              non si toccano, e non toccano lo scheletro)
  21 - 22     lo scheletro si dissolve
  22 - 23     le facce dell'icosaedro si rimpiccioliscono a zero, e intanto M
              ricompare
  22 - 25     la rotazione di M rallenta fino a fermarsi (ease out)
  25 - 26     l'esplosione, decelerata (ease out), tutti i triangoli insieme:
              ognuno si allontana dal centro lungo la sua normale e poi, con
              una curva senza spigoli, va alla sua cella; 20 gruppi da 12 (5 x
              4 gruppi, 4 x 3 triangoli), su un piano parallelo allo schermo
  26 - 28     tutto fermo

--------------------------------------------------------------------------
LE SCELTE
--------------------------------------------------------------------------
* Come scene_1: la camera e' prospettica e ferma, il quadro e' scalato e
  spostato perche' il poliedro dipinto combaci con M visto dalla camera, e il
  materiale di M e' uno solo (m_scene.look_face_material), con i nodi animati
  'Look' (dal quadro al pastello) e 'Fade' (la dissolvenza), che usano anche i
  240 triangoli dell'esplosione.
* Le semplificazioni rispetto a scene_1: niente solidi platonici; le facce
  dell'icosaedro sono opache e compaiono e spariscono solo scalando;
  l'esplosione parte per tutti i triangoli insieme (in un secondo lo
  sfalsamento di scene_1 non ci starebbe).
* Niente di quello che compare dopo il quadro fa ombra.
* Il motore e' Cycles, a 256 campioni (m_scene.use_cycles).

Una sola scena, tutto in keyframe (nessun handler), script idempotente, nomi
col prefisso S1V2_.
"""

import bpy
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
        txt = bpy.data.texts.get("scene-1.py")
    if txt is None or not txt.filepath:
        raise RuntimeError(
            "non riesco a ricavare il path dello script: il testo non e' salvato "
            "su disco (Text > Save As) oppure e' un blocco 'interno'"
        )
    # attenzione: se il file e' stato aperto con l'opzione 'Relative Path' spuntata,
    # filepath e' del tipo '//../...' (relativo al .blend) e os.path lo interpreta
    # come percorso UNC. bpy.path.abspath lo risolve; sugli assoluti non fa nulla.
    path = os.path.abspath(bpy.path.abspath(txt.filepath))
    # script in src/scripts/v2, librerie in src/libs
    libs = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(path))), "libs")
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

PREFIX          = "S1V2"
COLLECTION_NAME = "scene-1_v2"

# saffaro/assets, accanto al repository: src/libs -> src -> saffaro-delthedra -> saffaro
ASSETS_DIR    = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(_LIBS))), "assets")

# Quello che scene_2 deve ritrovare uguale per raccordarsi -- la posa di M nel
# quadro, la camera, la griglia, i colori, il fondo, la luce -- sta in
# libs/story.py: qui ci sono solo le scelte di questa scena.
FPS         = story.FPS
RESOLUTION  = story.RESOLUTION
FRAME_START = 1

# --- la scaletta, in secondi ---
PAINT_FADE      = (8.0, 9.0)     # il quadro si dissolve
LOOK_CHANGE     = (9.0, 11.0)    # M: dai colori del quadro al pastello fisico
SPIN_START      = 10.0           # M comincia a girare (ease in)
SPIN_RAMP       = 2.0            # ... raggiungendo la velocita' in tanti secondi
SPIN_STOP       = (22.0, 25.0)   # ... e rallenta fino a fermarsi
SPIN_SECONDS_PER_TURN = 20.0
SKELETON_IN     = (15.0, 16.0)   # lo scheletro dell'icosaedro compare
M_OUT           = (20.0, 21.0)   # M si dissolve...
ICO_FACES_IN    = (20.5, 21.5)   # ... le facce dell'icosaedro crescono...
SKELETON_OUT    = (21.0, 22.0)   # ... e lo scheletro si dissolve
SWAP_BACK       = (22.0, 23.0)   # le facce si rimpiccioliscono e M ricompare
EXPLODE         = (25.0, 26.0)   # l'esplosione
HOLD_SECONDS    = 2.0            # immagine ferma, alla fine

# --- i colori: pastello, stessa luminosita' e saturazione in OKLCH (story.pastel) ---
SKELETON_HUE = 100.0             # lo scheletro dell'icosaedro: giallo
ICO_FACE_HUE = 35.0              # le facce dell'icosaedro: corallo

# --- l'icosaedro ---
ICO_MARGIN       = story.ICO_MARGIN   # la gabbia di M: tangente ai suoi 30 spigoli (M_ico)
ICO_TUBE_RADIUS  = 0.04          # cilindretti e sferette
ICO_FACE_SCALE   = 0.85          # le facce non si toccano (scene_1: 0.9)

# --- l'esplosione (la griglia e' story.GRID) ---
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


def ease_out(u):
    return 1.0 - (1.0 - u) ** 3


def _check_schedule():
    marks = [0.0, PAINT_FADE[0], PAINT_FADE[1], SPIN_START, SKELETON_IN[1], M_OUT[0],
             ICO_FACES_IN[0], SKELETON_OUT[0], SWAP_BACK[0], SPIN_STOP[1], EXPLODE[0],
             EXPLODE[1], T_END]
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


def explosion_keys(tri, target):
    """Keyframe del triangolo, uno per fotogramma durante il volo, che e'
    lo stesso per tutti e decelera (ease out).

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
    t1, t2 = EXPLODE
    keys = [Key(FRAME_START, tri.loc, tri.quat, 1.0)]
    for f in range(frame_of(t1), frame_of(t2) + 1):
        u = ease_out(ramp(time_of(f), t1, t2))
        keys.append(Key(f, bezier(p0, p1, p2, p3, u), tri.quat.slerp(quat_t, u),
                        1.0 + (scale_t - 1.0) * u))
    return keys


# =============================================================================
# COSTRUZIONE
# =============================================================================

KIT = m_scene.Kit(PREFIX, COLLECTION_NAME, ASSETS_DIR)


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
                  (SKELETON_OUT[0], 1.0), (SKELETON_OUT[1], 0.0)])
    visible_between(skeleton, SKELETON_IN[0], SKELETON_OUT[1])

    coral = m_scene.wire_material(KIT, "ico_faces", pastel(ICO_FACE_HUE), roughness=0.5)
    faces = []
    for n, f in enumerate(ico.faces):
        c = sum(V[i] for i in f) / 3.0
        mesh = bpy.data.meshes.new(KIT.name(f"ico_face_{n:02d}"))
        mesh.from_pydata([tuple(V[i] - c) for i in f], [], [(0, 1, 2)])
        mesh.materials.append(coral)
        obj = KIT.new_object(f"ico_face_{n:02d}", mesh, parent=orient)
        obj.location = tuple(c)
        obj.visible_shadow = False
        # scala attorno al baricentro: sotto 1 resta un bordo libero fra le facce
        bl_anim.key_value(obj, "scale", [(frame_of(ICO_FACES_IN[0]), (0.0,) * 3),
                                         (frame_of(ICO_FACES_IN[1]), (ICO_FACE_SCALE,) * 3),
                                         (frame_of(SWAP_BACK[0]), (ICO_FACE_SCALE,) * 3),
                                         (frame_of(SWAP_BACK[1]), (0.0,) * 3)])
        visible_between(obj, ICO_FACES_IN[0], SWAP_BACK[1])
        faces.append(obj)
    return skeleton, faces, scale


def build():
    _check_schedule()
    KIT.clear_previous_run()
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.render.resolution_x, scene.render.resolution_y = RESOLUTION
    scene.frame_start, scene.frame_end = FRAME_START, FRAME_END
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    m_scene.use_cycles(scene)
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
    fade(m_mat, [(M_OUT[0], 1.0), (M_OUT[1], 0.0), (SWAP_BACK[0], 0.0), (SWAP_BACK[1], 1.0)])

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
                                   (frame_of(SWAP_BACK[0]) - 1, True), (frame_of(EXPLODE[0]), False)])

    # --- l'icosaedro ---
    build_icosahedron(orient, md)

    # --- i 240 triangoli ---
    mesh = m_scene.triangle_mesh(KIT, m_mat, uvs)
    tris = [m_scene.Tri(p) for p in pieces.m_pieces(md)]
    targets, world_targets, grid_scale = layout.grid(tris, orient_world)
    for tri, target in zip(tris, targets):
        obj = KIT.new_object(f"tri_{tri.piece.index:03d}", mesh, parent=orient)
        obj.visible_shadow = False
        tri.obj = obj
        bl_anim.apply_keys(obj, explosion_keys(tri, target))
        bl_anim.set_interpolation(obj, 'LINEAR', bl_anim.POSE_PATHS)
        bl_anim.key_visibility(obj, [(FRAME_START, False), (frame_of(EXPLODE[0]), True)])

    miss, tilt = m_scene.check_targets(tris, world_targets, scene, FRAME_END)
    scene.frame_set(FRAME_START)

    print(f"[scene-1 v2] frame {FRAME_START}-{FRAME_END} a {FPS} fps ({T_END:.1f} s)")
    print(f"[scene-1 v2] quadro alto {p_height:.3f} sul piano y = {p_depth:.2f}, camera in "
          f"({eye.x:.3f}, {eye.y:.1f}, {eye.z:.3f}) con focale {lens:.2f} mm")
    print(f"[scene-1 v2] M gira {spin[FRAME_END] / (2 * math.pi):.3f} giri fra {SPIN_START} e "
          f"{SPIN_STOP[1]} s; gabbia a scala {ico_scale:.4f}; triangoli scalati a {grid_scale:.3f}")
    print(f"[scene-1 v2] a fine esplosione: scarto di posizione {miss:.2e}, di rotazione {tilt:.2e} gradi")
    return tris


TRIS = build()
