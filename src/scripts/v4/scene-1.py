"""
v4/scene-1.py -- M esce dal quadro (come v3/scene1b), l'icosaedro e le sue
20 facce attorno a M (come v2/scene-1), e i 240 triangoli di M che migrano
uno dopo l'altro nella griglia.

--------------------------------------------------------------------------
LA SCALETTA (secondi, a 24 fps)
--------------------------------------------------------------------------
   0 - 7      il quadro, fermo, dalla camera in asse con M (story.AxisLayout).
              M c'e' gia', coi colori del quadro, subito dietro il quadro
   7          la camera comincia a girare di lato (story.EXIT_SIDE_ANGLE) e un po' in
              alto, e si ferma quando il centro di M passa per il quadro
   7.5 - 12.5 M esce piano dal quadro con un solo movimento (ease in/out),
              venendo avanti e un po' a sinistra; il contorno della sezione
              -- dove M incontra il piano del quadro -- brilla d'oro
  11.5 - 14   la camera, ferma dov'e', si gira verso M e lo porta al centro;
              il quadro svanisce (12 - 13.5); da 12.5 M comincia a girare su
              se stesso, e non smette piu'
  19 - 20     compare lo scheletro dell'icosaedro che contiene M: gira con
              lui, solidale
  20.5 - 22   M e lo scheletro svaniscono, e le 20 facce dell'icosaedro
              crescono (scala da 0 a FACE_SCALE): triangoli semitrasparenti
              coi lati a tubicini e i vertici a sferette
  22.5 - 24   le facce svaniscono e M ricompare
  28 - 32     al posto di M i suoi 240 triangoli, che si staccano uno dopo
              l'altro -- pochi all'inizio, poi sempre di piu' -- e volano
              nella griglia dietro M: 20 gruppi da 12, rivolti alla camera.
              A 32 s sono tutti al loro posto, ed e' la fine

--------------------------------------------------------------------------
LE SCELTE
--------------------------------------------------------------------------
* L'uscita dal quadro e' quella di v3/scene1b (si veda li'): la camera di
  story.AxisLayout, M alla scala del dipinto, la parte di M dietro il quadro
  trasparente, la linea dorata della sezione calcolata a ogni fotogramma.
  M resta coi colori del quadro (Look 0) per tutta la scena.
* M, lo scheletro e le facce sono figli dello stesso perno (mover -> orient,
  come in v2/scene-1): girano insieme, fermi l'uno rispetto all'altro. Le
  facce scalano attorno al loro baricentro, quindi non si toccano.
* I 240 triangoli: dal momento in cui sostituiscono M fino alla partenza
  seguono M fotogramma per fotogramma (la sua posa e il suo giro), poi volano:
  si staccano lungo la loro normale e, con una curva senza spigoli, vanno
  alla loro cella (POP_DISTANCE, ARRIVAL_PULL come in v2/scene-1). L'ordine
  e' casuale ma fisso (SEED). Il k-esimo parte a MIGRATE[0] + D sqrt(k/240):
  il numero di quelli partiti cresce come il quadrato del tempo, pochi
  all'inizio e sempre di piu'; D e' tale che l'ultimo arrivi alla fine.
* La griglia: story.GRID (20 gruppi, uno per faccia estesa di M, da 4 x 3),
  su un piano perpendicolare all'asse della camera finale, story.EXIT_GRID_BEHIND piu'
  lontano del centro di M, larga GRID_FILL dell'inquadratura. Il materiale
  dei triangoli e' quello di M senza il taglio dietro il quadro (qualcuno,
  volando, passa dietro il suo piano).
* Il motore e' Cycles, a 256 campioni (m_scene.use_cycles).

Una sola scena, tutto in keyframe (nessun handler), script idempotente, nomi
col prefisso S1V4_.
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
    # script in src/scripts/v4, librerie in src/libs
    libs = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(path))), "libs")
    if not os.path.isdir(libs):
        raise RuntimeError(f"cartella libs non trovata: {libs}  (filepath: {txt.filepath})")
    return libs


_LIBS = _find_libs_dir()
if _LIBS not in sys.path:
    sys.path.insert(0, _LIBS)

# questo serve nel caso che tu faccia modifiche ai moduli senza interrompere la sessione di Blender
import geometry, bl_utils, extended_face, pieces, bl_anim, m_scene, story, deltahedra
for _mod in (geometry, bl_utils, extended_face, pieces, bl_anim, m_scene, story, deltahedra):
    importlib.reload(_mod)

from mathutils import Vector, Matrix, Quaternion
from bl_anim import Key


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

PREFIX          = "S1V4"
COLLECTION_NAME = "scene-1_v4"

# saffaro/assets, accanto al repository: src/libs -> src -> saffaro-delthedra -> saffaro
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(_LIBS))), "assets")

FPS         = story.FPS
RESOLUTION  = story.RESOLUTION
FRAME_START = 1

# --- la scaletta, in secondi ---
MOVE          = (7.5, 12.5)      # M esce dal quadro, con un solo ease in/out
CAMERA_LEAD   = 0.5              # la camera va di lato da tanto prima di MOVE fino a quando
                                 # il centro di M passa per il piano del quadro
FOCUS         = (11.5, 14.0)     # la camera si gira verso M e lo porta al centro
PAINT_FADE    = (12.0, 13.5)     # il quadro svanisce
SPIN_RAMP     = 1.5              # quando M si ferma comincia a girare, arrivando alla
                                 # sua velocita' in tanto
SPIN_SECONDS_PER_TURN = 20.0
SKELETON_IN   = (19.0, 20.0)     # lo scheletro dell'icosaedro compare
FACES_IN      = (20.5, 22.0)     # M e lo scheletro svaniscono, le facce crescono
FACES_OUT     = (22.5, 24.0)     # le facce svaniscono, M ricompare
MIGRATE       = (28.0, 32.0)     # i triangoli migrano nella griglia
FLY_SECONDS   = 1.2              # quanto dura il volo di un triangolo
END           = MIGRATE[1]

# Le posizioni dell'uscita (dove si ferma M, la camera di lato e quella finale,
# la griglia) sono in story.ExitView, coi parametri EXIT_*: v4/scene-2 comincia
# dove finisce questa scena, e deve rifare gli stessi conti.

# --- il contorno della sezione ---
GLOW_COLOR      = (1.0, 0.78, 0.35)
LINE_RADIUS     = 0.007          # il tubicino della linea (circa 3 pixel di diametro)
LINE_STRENGTH   = 30.0           # quanto brilla
GLARE_THRESHOLD = 1.0
GLARE_STRENGTH  = 1.2
GLARE_SIZE      = 0.7

# --- l'icosaedro (in unita' di M) ---
SKELETON_HUE      = 100.0        # lo scheletro: giallo pastello
SKELETON_RADIUS   = 0.04         # cilindretti e sferette dello scheletro
FACE_HUE          = 35.0         # le facce: corallo pastello
FACE_SCALE        = 0.95         # attorno al baricentro: le facce non si toccano
FACE_OPACITY      = 0.35         # i triangoli delle facce
FACE_TUBE_RADIUS  = 0.025        # i lati e i vertici delle facce

# --- la migrazione ---
SEED          = 7
POP_DISTANCE  = 1.0              # quanto si allontana lungo la normale, prima di girare
ARRIVAL_PULL  = 0.4              # quanto l'arrivo tiene della direzione di partenza


# =============================================================================
# LA REGIA
# =============================================================================

FRAME_END = FRAME_START + int(round(END * FPS))


def frame_of(t):
    return FRAME_START + int(round(t * FPS))


def time_of(frame):
    return (frame - FRAME_START) / FPS


def ramp(t, t0, t1):
    return min(1.0, max(0.0, (t - t0) / (t1 - t0)))


def smoother(u):
    return u * u * u * (u * (6.0 * u - 15.0) + 10.0)


def smootherstep(x, x0, x1):
    return smoother(ramp(x, x0, x1))


def spin_angles(frames):
    """{frame: angolo}: dalla fine di MOVE la velocita' sale da zero con un
    raccordo dolce in SPIN_RAMP secondi, poi resta costante; integrata
    fotogramma per fotogramma."""
    omega = 2.0 * math.pi / SPIN_SECONDS_PER_TURN
    out, a = {}, 0.0
    for f in frames:
        out[f] = a
        a += omega * smootherstep(time_of(f) + 0.5 / FPS, MOVE[1], MOVE[1] + SPIN_RAMP) / FPS
    return out


def departure_times(n, rng):
    """Quando parte ogni triangolo (per indice): in un ordine casuale, il
    k-esimo a MIGRATE[0] + D sqrt(k / (n - 1)), con D tale che l'ultimo arrivi
    alla fine di MIGRATE."""
    D = (MIGRATE[1] - MIGRATE[0]) - FLY_SECONDS
    order = rng.permutation(n)
    times = np.empty(n)
    for k, i in enumerate(order):
        times[i] = MIGRATE[0] + D * math.sqrt(k / (n - 1))
    return times


def bezier(p0, p1, p2, p3, u):
    v = 1.0 - u
    return p0 * v ** 3 + p1 * (3 * v * v * u) + p2 * (3 * v * u * u) + p3 * u ** 3


# =============================================================================
# LA CAMERA
# =============================================================================

look_quat = story.look_quat
camera_back = story.camera_back


# =============================================================================
# IL CONTORNO DELLA SEZIONE (come v3/scene1b)
# =============================================================================

KIT = m_scene.Kit(PREFIX, COLLECTION_NAME, ASSETS_DIR)


def add_section_cut(mat, plane_y):
    """Rende trasparente, nel materiale, tutto quello che sta dietro il piano
    y = plane_y."""
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    out = next(n for n in nodes if n.type == 'OUTPUT_MATERIAL')
    surface = out.inputs["Surface"].links[0].from_socket
    geo = nodes.new("ShaderNodeNewGeometry")
    sep = nodes.new("ShaderNodeSeparateXYZ")
    links.new(geo.outputs["Position"], sep.inputs[0])
    behind = nodes.new("ShaderNodeMath")
    behind.operation = 'GREATER_THAN'
    links.new(sep.outputs["Y"], behind.inputs[0])
    behind.inputs[1].default_value = plane_y
    clear = nodes.new("ShaderNodeBsdfTransparent")
    cut = nodes.new("ShaderNodeMixShader")
    links.new(behind.outputs[0], cut.inputs["Fac"])
    links.new(surface, cut.inputs[1])
    links.new(clear.outputs["BSDF"], cut.inputs[2])
    links.new(cut.outputs["Shader"], out.inputs["Surface"])


def line_material():
    mat, nodes, links = KIT.new_material("section")
    out = nodes.new("ShaderNodeOutputMaterial")
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = tuple(GLOW_COLOR) + (1.0,)
    emit.inputs["Strength"].default_value = LINE_STRENGTH
    links.new(emit.outputs["Emission"], out.inputs["Surface"])
    mat.diffuse_color = tuple(GLOW_COLOR) + (1.0,)
    return mat


def build_section_lines(md, P, frames, m_loc, m_spin, scale, plane_y):
    """Le linee della sezione: per ogni fotogramma in cui il piano del quadro
    taglia M, un oggetto curva coi tubicini delle curve chiuse, visibile solo
    in quel fotogramma. Restituisce i fotogrammi che ne hanno una."""
    mat = line_material()
    out = []
    for f, loc, a in zip(frames, m_loc, m_spin):
        c, sn = math.cos(a), math.sin(a)
        Rz = np.array([[c, -sn, 0.0], [sn, c, 0.0], [0.0, 0.0, 1.0]])
        W = np.asarray(loc) + scale * (P @ Rz.T)
        loops = deltahedra.plane_section(W, md.faces, axis=1, value=plane_y)
        if not loops:
            continue
        name = f"section_{f:04d}"
        curve = bpy.data.curves.new(KIT.name(name), 'CURVE')
        curve.dimensions = '3D'
        curve.bevel_depth = LINE_RADIUS
        curve.bevel_resolution = 2
        curve.fill_mode = 'FULL'
        for loop in loops:
            spline = curve.splines.new('POLY')
            spline.points.add(len(loop) - 1)
            for point, q in zip(spline.points, loop):
                point.co = (q[0], q[1], q[2], 1.0)
            spline.use_cyclic_u = True
        curve.materials.append(mat)
        obj = KIT.new_object(name, curve)
        m_scene.hide_from_light(obj)
        bl_anim.key_visibility(obj, [(FRAME_START, False), (f, True), (f + 1, False)])
        out.append(f)
    return out


# =============================================================================
# L'ICOSAEDRO: LO SCHELETRO E LE 20 FACCE
# =============================================================================

def fade(mat, keys):
    """Keyframe del nodo 'Fade' del materiale: (secondi, valore)."""
    bl_anim.key_value(mat.node_tree, m_scene.FADE_PATH, [(frame_of(t), v) for t, v in keys])


def visible_between(obj, t0, t1):
    bl_anim.key_visibility(obj, [(FRAME_START, False), (frame_of(t0), True), (frame_of(t1) + 1, False)])


def build_icosahedron(orient, md):
    """Lo scheletro e le 20 facce dell'icosaedro-gabbia di M, figli di orient:
    girano con M. Ogni faccia e' un triangolo semitrasparente (l'oggetto, che
    scala attorno al suo baricentro) con un figlio: i tubicini dei lati e le
    sferette dei vertici."""
    ico = geometry.Polyhedron.ico
    scale = geometry.enclosing_scale(md.vertices, ico) * story.ICO_MARGIN
    V = [np.asarray(v.tup()) * scale for v in ico.vertices]
    edges = sorted({tuple(sorted((f[k], f[(k + 1) % 3]))) for f in ico.faces for k in range(3)})

    yellow = m_scene.fading_material(KIT, "skeleton", story.pastel(SKELETON_HUE), roughness=0.4)
    skeleton = KIT.new_object("skeleton", m_scene.skeleton_mesh(KIT, "skeleton", V, edges,
                                                                SKELETON_RADIUS, yellow), parent=orient)
    skeleton.visible_shadow = False
    fade(yellow, [(SKELETON_IN[0], 0.0), (SKELETON_IN[1], 1.0), (FACES_IN[0], 1.0), (FACES_IN[1], 0.0)])
    visible_between(skeleton, SKELETON_IN[0], FACES_IN[1])

    coral = story.pastel(FACE_HUE)
    glass = m_scene.fading_material(KIT, "ico_faces", coral, roughness=0.4)
    fade(glass, [(FACES_IN[0], FACE_OPACITY), (FACES_OUT[0], FACE_OPACITY), (FACES_OUT[1], 0.0)])
    rims = m_scene.fading_material(KIT, "ico_rims", coral, roughness=0.35)
    fade(rims, [(FACES_IN[0], 1.0), (FACES_OUT[0], 1.0), (FACES_OUT[1], 0.0)])
    for n, f in enumerate(ico.faces):
        c = sum(V[i] for i in f) / 3.0
        local = [tuple(V[i] - c) for i in f]
        mesh = bpy.data.meshes.new(KIT.name(f"ico_face_{n:02d}"))
        mesh.from_pydata(local, [], [(0, 1, 2)])
        mesh.materials.append(glass)
        obj = KIT.new_object(f"ico_face_{n:02d}", mesh, parent=orient)
        obj.location = tuple(c)
        obj.visible_shadow = False
        rim = KIT.new_object(f"ico_face_{n:02d}_rim",
                             m_scene.skeleton_mesh(KIT, f"ico_face_{n:02d}_rim", local,
                                                   [(0, 1), (1, 2), (0, 2)], FACE_TUBE_RADIUS, rims),
                             parent=obj)
        rim.visible_shadow = False
        bl_anim.key_value(obj, "scale", [(frame_of(FACES_IN[0]), (0.0,) * 3),
                                         (frame_of(FACES_IN[1]), (FACE_SCALE,) * 3)])
        visible_between(obj, FACES_IN[0], FACES_OUT[1])
    return scale


# =============================================================================
# LA MIGRAZIONE
# =============================================================================

def migration_keys(tri, world_of, normal_of, depart, target, frames):
    """Le chiavi del triangolo, una per fotogramma da MIGRATE[0]: prima segue
    M (world_of(f) e' la sua matrice mondo), poi vola alla cella. Il volo e'
    una Bezier cubica: parte lungo la normale, arriva sulla cella tenendo un
    po' della direzione di partenza; rotazione e scala seguono lo stesso
    parametro, con un raccordo dolce."""
    loc_t, quat_t, scale_t = target
    f_dep = frame_of(depart)
    local = Matrix.Translation(tri.loc) @ tri.quat.to_matrix().to_4x4()
    m0 = world_of(f_dep) @ local
    p0, q0, s0 = m0.decompose()
    p1 = p0 + normal_of(f_dep) * POP_DISTANCE
    p3 = Vector(loc_t)
    p2 = p3 + (p1 - p3) * ARRIVAL_PULL
    keys = []
    for f in frames:
        t = time_of(f)
        if f <= f_dep:
            loc, quat, sc = (world_of(f) @ local).decompose()
            keys.append(Key(f, loc, quat, sc.x))
        else:
            u = smoother(ramp(t, depart, depart + FLY_SECONDS))
            keys.append(Key(f, bezier(p0, p1, p2, p3, u), q0.slerp(quat_t, u), s0.x + (scale_t - s0.x) * u))
    return keys


# =============================================================================
# COSTRUZIONE
# =============================================================================

def build():
    KIT.clear_previous_run()
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.render.resolution_x, scene.render.resolution_y = RESOLUTION
    scene.frame_start, scene.frame_end = FRAME_START, FRAME_END
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    m_scene.use_cycles(scene)
    scene.cycles.transparent_max_bounces = 32       # dissolvenze e facce semitrasparenti
    KIT.new_collection(scene)
    frames = list(range(FRAME_START, FRAME_END + 1))

    md = extended_face.make_M()
    painting_img = KIT.load_image(story.PAINTING_FILE)
    ev = story.ExitView(md, painting_img.size)
    layout = ev.layout
    cam = story.build_camera_and_world(KIT, layout, clip_end=story.CAMERA_DISTANCE + story.GRID_DEPTH + 40.0)
    painting, p_mat = story.build_painting(KIT, painting_img, layout)
    fade(p_mat, [(PAINT_FADE[0], 1.0), (PAINT_FADE[1], 0.0)])
    bl_anim.key_visibility(painting, [(FRAME_START, True), (frame_of(PAINT_FADE[1]) + 1, False)])
    m_scene.setup_glare(KIT, scene, GLARE_THRESHOLD, GLARE_STRENGTH, GLARE_SIZE)
    plane = layout.painting_depth

    # --- M: mover (posizione, scala, giro) -> orient (la posa del quadro) -> M ---
    face_img = KIT.load_image(m_scene.FACE_TEXTURE_FILE)
    uvs = m_scene.face_uvs(face_img, m_scene.FACE_TEXTURE_UV_PX, m_scene.FACE_TEXTURE_UV_INSET)
    m_mat = story.face_material(KIT, face_img, uvs)          # Look 0: i colori del quadro
    fade(m_mat, [(FACES_IN[0], 1.0), (FACES_IN[1], 0.0), (FACES_OUT[0], 0.0), (FACES_OUT[1], 1.0)])
    add_section_cut(m_mat, plane)
    mover = KIT.new_object("mover")
    mover.empty_display_size = 0.5
    orient = KIT.new_object("orient", parent=mover)
    orient.rotation_euler = [math.radians(a) for a in story.ORIENT_EULER_DEG]
    m_obj = KIT.new_object("M", m_scene.merged_mesh(KIT, md, m_mat, uvs), parent=orient)
    bl_utils.merge_by_distance(m_obj)
    m_obj.visible_shadow = False
    bl_anim.key_visibility(m_obj, [(FRAME_START, True), (frame_of(MIGRATE[0]), False)])

    # --- l'uscita dal quadro ---
    P, eye0 = ev.P, np.asarray(layout.eye)
    s0, y0, y1, side = ev.s0, ev.y0, ev.y1, ev.side
    target1, eye1, lens1 = ev.target1, ev.eye1, ev.lens1
    w_move = [smootherstep(time_of(f), *MOVE) for f in frames]
    m_loc = [(-side * w, y0 + (y1 - y0) * w, 0.0) for w in w_move]
    spin = spin_angles(frames)
    bl_anim.key_value(mover, "location", [(f, loc) for f, loc in zip(frames, m_loc)],
                      interpolation='LINEAR')
    mover.scale = (s0,) * 3
    bl_anim.key_value(mover, "rotation_euler", [(f, (0.0, 0.0, spin[f])) for f in frames],
                      interpolation='LINEAR')
    lit = build_section_lines(md, P, frames, m_loc, [spin[f] for f in frames], s0, plane)

    # --- la camera: di lato, ferma, poi si gira verso M ---
    t_center = next(time_of(f) for f, loc in zip(frames, m_loc) if loc[1] <= plane)
    camera_move = (MOVE[0] - CAMERA_LEAD, t_center)
    m_end, lens_m = ev.m_end, ev.lens_m
    target0 = eye0 + np.array([0.0, story.EXIT_DISTANCE, 0.0])
    cam.rotation_mode = 'QUATERNION'
    keys_loc, keys_rot, keys_lens = [], [], []
    for f in frames:
        t = time_of(f)
        w = smootherstep(t, *camera_move)
        target = target0 + (target1 - target0) * w
        eye = target + camera_back(story.EXIT_SIDE_ANGLE * w, story.EXIT_ELEVATION * w) * story.EXIT_DISTANCE
        lens = layout.lens + (lens1 - layout.lens) * w
        z = smootherstep(t, *FOCUS)
        target = target + (m_end - target1) * z
        lens = lens + (lens_m - lens1) * z
        keys_loc.append((f, tuple(eye)))
        keys_rot.append((f, tuple(look_quat(target - eye))))
        keys_lens.append((f, lens))
    bl_anim.key_value(cam, "location", keys_loc, interpolation='LINEAR')
    bl_anim.key_value(cam, "rotation_quaternion", keys_rot, interpolation='LINEAR')
    bl_anim.key_value(cam.data, "lens", keys_lens, interpolation='LINEAR')

    # --- l'icosaedro ---
    build_icosahedron(orient, md)

    # --- i 240 triangoli: seguono M, poi migrano nella griglia ---
    tri_mat = story.face_material(KIT, face_img, uvs)        # come M, senza il taglio
    mesh = m_scene.triangle_mesh(KIT, tri_mat, uvs)
    tris = [m_scene.Tri(p) for p in pieces.m_pieces(md)]
    O = story.orient_matrix()

    def world_of(f):
        return (Matrix.Translation(m_loc[f - FRAME_START]) @ Matrix.Rotation(spin[f], 4, 'Z')
                @ Matrix.Scale(s0, 4) @ O)

    def normal_of_tri(tri):
        n = Vector(tri.piece.normal)
        return lambda f: (Matrix.Rotation(spin[f], 3, 'Z') @ O.to_3x3() @ n).normalized()

    grid_distance = ev.grid_distance()
    targets = ev.grid_poses(tris)
    departs = departure_times(len(tris), np.random.default_rng(SEED))
    mig_frames = [f for f in frames if f >= frame_of(MIGRATE[0])]
    for tri, target, t_dep in zip(tris, targets, departs):
        obj = KIT.new_object(f"tri_{tri.piece.index:03d}", mesh)
        obj.visible_shadow = False
        bl_anim.apply_keys(obj, migration_keys(tri, world_of, normal_of_tri(tri), t_dep, target, mig_frames))
        bl_anim.set_interpolation(obj, 'LINEAR', bl_anim.POSE_PATHS)
        bl_anim.key_visibility(obj, [(FRAME_START, False), (frame_of(MIGRATE[0]), True)])

    scene.frame_set(FRAME_START)
    print(f"[scene-1 v4] frame {FRAME_START}-{FRAME_END} a {FPS} fps ({END:.0f} s)")
    print(f"[scene-1 v4] M alla scala {s0:.3f}, esce dal quadro fra {MOVE[0]} e {MOVE[1]} s; la linea "
          f"della sezione da {time_of(lit[0]):.2f} a {time_of(lit[-1]):.2f} s")
    print(f"[scene-1 v4] camera di lato fra {camera_move[0]:.2f} e {camera_move[1]:.2f} s, poi su M "
          f"fra {FOCUS[0]} e {FOCUS[1]} s (focale {lens_m:.1f} mm)")
    print(f"[scene-1 v4] griglia a {grid_distance:.2f} dalla camera, triangoli scalati a {targets[0][2]:.3f}; "
          f"partenze da {departs.min():.2f} a {departs.max():.2f} s, in volo {FLY_SECONDS} s")


build()
