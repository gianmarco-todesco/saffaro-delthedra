"""
v4/scene-1.py -- M esce dal quadro, l'icosaedro e le sue 20 facce attorno a M
(come v2/scene-1), e i 240 triangoli di M che migrano uno dopo l'altro nella
griglia.

--------------------------------------------------------------------------
LA SCALETTA (secondi, a 24 fps)
--------------------------------------------------------------------------
   0 - 1      il quadro, dalla camera davanti al suo centro, cosi' vicino che
              ne riempie esattamente l'altezza.
              M c'e' gia', coi colori del quadro, subito dietro il quadro
   1 - 8      la camera arretra lentamente, portandosi in asse con M
              (story.AxisLayout), finche' inquadra il quadro con un po' di
              margine
   8.5 - 9    il quadro gira: il suo centro va su un arco di cerchio
              orizzontale, prima allontanandosi dalla camera e poi piegando a
              destra, e il quadro resta perpendicolare alla tangente, fino a
              60 gradi (story.EXIT_TILT); M, dietro, gli va dietro
   8.75 - 12  M esce dal quadro lungo la normale (un quarto di secondo prima
              che il quadro si fermi: fino ad allora la normale gira col
              quadro), finche' ne e'
              tutto fuori: allora e' esattamente al centro dell'immagine. Il
              contorno della sezione -- dove M incontra il piano del quadro --
              brilla d'oro
  12          M comincia a girare lentamente su se stesso, e non smette piu';
              il quadro svanisce (12 - 13.5)
  21 - 22     compaiono gli spigoli dell'icosaedro che contiene M: gira con
              lui, solidale
  25 - 26     M e gli spigoli svaniscono, e crescono le 20 facce (scala da 0
              a FACE_SCALE): triangoli semitrasparenti coi lati a tubicini e
              i vertici a sferette, ben staccati l'uno dall'altro
  27 - 28     le facce svaniscono e M ricompare
  30 - 35     al posto di M i suoi 240 triangoli, che si staccano uno dopo
              l'altro -- pochi all'inizio, poi sempre di piu' -- e volano
              nella griglia dietro M: 20 gruppi da 12, rivolti alla camera
  36          fine

--------------------------------------------------------------------------
LE SCELTE
--------------------------------------------------------------------------
* Le posizioni (M, la camera, il quadro, la griglia) sono in story.ExitView,
  coi parametri EXIT_*: v4/scene-2 comincia dove finisce questa scena, e
  deve rifare gli stessi conti. M sta alla scala per cui, subito dietro il
  quadro, visto dalla camera (quella della fine dell'arretramento) e'
  identico al poliedro dipinto. Mentre il quadro gira M gli e' attaccato;
  poi ne esce perpendicolare alla sua superficie. Il raggio dell'arco del
  quadro e' quello per cui, finita l'uscita, M sta sull'asse della camera.
* M esiste solo davanti al quadro: nel materiale, la parte che sta dietro il
  piano del quadro (nelle coordinate del quadro, y > 0) e' trasparente.
  Visto da davanti non cambia niente, e M non spunta dai bordi del quadro:
  ne esce dalla superficie. La linea della sezione si
  calcola a ogni fotogramma nel riferimento del quadro
  (deltahedra.plane_section) ed e' un tubicino sottile (LINE_RADIUS) di luce
  dorata. L'emissione resta debole (LINE_STRENGTH), perche' un'emissione
  forte satura anche i pixel coperti in parte e la linea si vede a gradini;
  il bagliore lo fa il compositor da un passaggio AOV che scrive solo il
  materiale della linea (m_scene.setup_aov_glow): un alone stretto e forte
  (GLOW_SOFTEN) che sfuma il bordo della linea, piu' un bloom largo.
* M resta coi colori del quadro (Look 0) per tutta la scena.
* M, gli spigoli e le facce sono figli dello stesso perno (mover -> orient,
  come in v2/scene-1): girano insieme, fermi l'uno rispetto all'altro. Le
  facce scalano attorno al loro baricentro.
* I 240 triangoli: dal momento in cui sostituiscono M fino alla partenza
  seguono M fotogramma per fotogramma, poi volano: si staccano lungo la loro
  normale e, con una curva senza spigoli, vanno alla loro cella
  (POP_DISTANCE, ARRIVAL_PULL come in v2/scene-1). Partono prima i piu'
  vicini alla camera e i piu' frontali (la faccia perpendicolare alla linea
  di vista), con la posa di M all'inizio di MIGRATE: si veda
  departure_order. Il k-esimo parte a MIGRATE[0] + D sqrt(k/240): il numero
  di quelli partiti cresce come il quadrato del tempo, pochi all'inizio e
  sempre di piu'; D e' tale che l'ultimo arrivi alla fine di MIGRATE.
* La griglia: story.GRID (20 gruppi, uno per faccia estesa di M, da 4 x 3),
  su un piano perpendicolare all'asse della camera, story.EXIT_GRID_BEHIND
  piu' lontano del centro di M, larga GRID_FILL dell'inquadratura. Il
  materiale dei triangoli e' quello di M senza il taglio.
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

from mathutils import Vector, Matrix
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
PULLBACK      = (1.0, 8.0)       # la camera arretra
TURN          = (8.5, 9.0)       # il quadro gira sul suo arco
EXIT          = (8.75, 12.0)     # M esce dal quadro
SPIN_AT       = 12.0             # M comincia a girare...
SPIN_RAMP     = 1.5              # ... arrivando alla sua velocita' in tanto
SPIN_SECONDS_PER_TURN = 20.0
PAINT_FADE    = (12.0, 13.5)     # il quadro svanisce
SKELETON_IN   = (21.0, 22.0)     # gli spigoli dell'icosaedro compaiono
FACES_IN      = (25.0, 26.0)     # M e gli spigoli svaniscono, le facce crescono
FACES_OUT     = (27.0, 28.0)     # le facce svaniscono, M ricompare
MIGRATE       = (30.0, 35.0)     # i triangoli migrano nella griglia
FLY_SECONDS   = 1.2              # quanto dura il volo di un triangolo
END           = 36.0

# --- il contorno della sezione ---
GLOW_COLOR      = (1.0, 0.78, 0.35)
LINE_RADIUS     = 0.01           # il tubicino della linea (circa 4 pixel di diametro)
LINE_STRENGTH   = 0.3            # l'emissione: debole, la luce la fa il compositor
GLOW_AOV        = "glow"         # il passaggio da cui il compositor fa il bagliore
GLOW_GAIN       = 14.0           # quanto la linea scrive nel passaggio
GLARE_STRENGTH  = 0.4            # il bloom largo: piu' forte, fa un'anima bianca e netta
GLARE_SIZE      = 0.8
GLOW_SOFTEN     = 8.0            # pixel: l'alone stretto attorno alla linea...
GLOW_SOFTEN_WEIGHT = 0.2         # ... e quanto conta

# --- l'icosaedro (in unita' di M) ---
SKELETON_HUE      = 100.0        # gli spigoli: giallo pastello
SKELETON_RADIUS   = 0.04         # cilindretti e sferette degli spigoli
FACE_HUE          = 35.0         # le facce: corallo pastello
FACE_SCALE        = 0.85         # attorno al baricentro: fra le facce restano spazi ben visibili
FACE_OPACITY      = 0.35         # i triangoli delle facce
FACE_TUBE_RADIUS  = 0.025        # i lati e i vertici delle facce

# --- la migrazione ---
POP_DISTANCE    = 1.0            # quanto si allontana lungo la normale, prima di girare
ARRIVAL_PULL    = 0.4            # quanto l'arrivo tiene della direzione di partenza
FRONTAL_WEIGHT  = 0.5            # quanto conta, nell'ordine di partenza, essere frontali


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
    """{frame: angolo}: da SPIN_AT la velocita' sale da zero con un raccordo
    dolce in SPIN_RAMP secondi, poi resta costante; integrata fotogramma per
    fotogramma."""
    omega = 2.0 * math.pi / SPIN_SECONDS_PER_TURN
    out, a = {}, 0.0
    for f in frames:
        out[f] = a
        a += omega * smootherstep(time_of(f) + 0.5 / FPS, SPIN_AT, SPIN_AT + SPIN_RAMP) / FPS
    return out


def departure_order(centres, normals, eye):
    """L'ordine di partenza: prima i triangoli vicini alla camera e frontali.
    Il punteggio e' la distanza dalla camera, riportata fra 0 (il piu' vicino)
    e 1 (il piu' lontano), piu' FRONTAL_WEIGHT volte (1 - c), con c il coseno
    fra la normale e la direzione verso la camera: 1 se la faccia la guarda
    in pieno, -1 se le volta le spalle. A pari punteggio decide l'indice."""
    d = np.array([np.linalg.norm(c - eye) for c in centres])
    d = (d - d.min()) / (d.max() - d.min())
    facing = np.array([float(n @ ((eye - c) / np.linalg.norm(eye - c))) for c, n in zip(centres, normals)])
    score = d + FRONTAL_WEIGHT * (1.0 - facing)
    return sorted(range(len(centres)), key=lambda i: (round(float(score[i]), 9), i))


def departure_times(order):
    """Il k-esimo dell'ordine parte a MIGRATE[0] + D sqrt(k / (n - 1)), con D
    tale che l'ultimo arrivi alla fine di MIGRATE. Restituisce i tempi per
    indice."""
    n = len(order)
    D = (MIGRATE[1] - MIGRATE[0]) - FLY_SECONDS
    times = np.empty(n)
    for k, i in enumerate(order):
        times[i] = MIGRATE[0] + D * math.sqrt(k / (n - 1))
    return times


def bezier(p0, p1, p2, p3, u):
    v = 1.0 - u
    return p0 * v ** 3 + p1 * (3 * v * v * u) + p2 * (3 * v * u * u) + p3 * u ** 3


# =============================================================================
# IL CONTORNO DELLA SEZIONE
# =============================================================================

KIT = m_scene.Kit(PREFIX, COLLECTION_NAME, ASSETS_DIR)


def add_section_cut(mat, painting):
    """Rende trasparente, nel materiale, tutto quello che sta dietro il
    quadro: nelle coordinate dell'oggetto `painting` (il quadro sta nel suo
    piano y = 0, e la camera dalla parte delle y negative), y > 0. Segue il
    quadro mentre gira e arretra."""
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    out = next(n for n in nodes if n.type == 'OUTPUT_MATERIAL')
    surface = out.inputs["Surface"].links[0].from_socket
    coords = nodes.new("ShaderNodeTexCoord")
    coords.object = painting
    sep = nodes.new("ShaderNodeSeparateXYZ")
    links.new(coords.outputs["Object"], sep.inputs[0])
    behind = nodes.new("ShaderNodeMath")
    behind.operation = 'GREATER_THAN'
    links.new(sep.outputs["Y"], behind.inputs[0])
    behind.inputs[1].default_value = 0.0
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
    aov = nodes.new("ShaderNodeOutputAOV")
    aov.aov_name = GLOW_AOV
    aov.inputs["Color"].default_value = tuple(c * GLOW_GAIN for c in GLOW_COLOR) + (1.0,)
    mat.diffuse_color = tuple(GLOW_COLOR) + (1.0,)
    return mat


def build_section_lines(md, m_world, painting_world, frames):
    """Le linee della sezione: per ogni fotogramma in cui il piano del quadro
    taglia M, un oggetto curva coi tubicini delle curve chiuse, visibile solo
    in quel fotogramma. La sezione si calcola nel riferimento del quadro (il
    suo piano e' y = 0) e si riporta nel mondo. m_world(f) e painting_world(f)
    sono le matrici mondo di M e del quadro. Restituisce i fotogrammi che ne
    hanno una."""
    mat = line_material()
    V = np.asarray(md.vertices, dtype=float)
    Vh = np.c_[V, np.ones(len(V))]
    out = []
    for f in frames:
        Mp = painting_world(f)
        local = (np.asarray(Mp.inverted() @ m_world(f)) @ Vh.T).T[:, :3]
        loops = deltahedra.plane_section(local, md.faces, axis=1, value=0.0)
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
                w = Mp @ Vector(q)
                point.co = (w.x, w.y, w.z, 1.0)
            spline.use_cyclic_u = True
        curve.materials.append(mat)
        obj = KIT.new_object(name, curve)
        m_scene.hide_from_light(obj)
        bl_anim.key_visibility(obj, [(FRAME_START, False), (f, True), (f + 1, False)])
        out.append(f)
    return out


# =============================================================================
# L'ICOSAEDRO: GLI SPIGOLI E LE 20 FACCE
# =============================================================================

def fade(mat, keys):
    """Keyframe del nodo 'Fade' del materiale: (secondi, valore)."""
    bl_anim.key_value(mat.node_tree, m_scene.FADE_PATH, [(frame_of(t), v) for t, v in keys])


def visible_between(obj, t0, t1):
    bl_anim.key_visibility(obj, [(FRAME_START, False), (frame_of(t0), True), (frame_of(t1) + 1, False)])


def build_icosahedron(orient, md):
    """Gli spigoli e le 20 facce dell'icosaedro-gabbia di M, figli di orient:
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
    p0, q0, s0 = (world_of(f_dep) @ local).decompose()
    p1 = p0 + normal_of(f_dep) * POP_DISTANCE
    p3 = Vector(loc_t)
    p2 = p3 + (p1 - p3) * ARRIVAL_PULL
    keys = []
    for f in frames:
        if f <= f_dep:
            loc, quat, sc = (world_of(f) @ local).decompose()
            keys.append(Key(f, loc, quat, sc.x))
        else:
            u = smoother(ramp(time_of(f), depart, depart + FLY_SECONDS))
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
    m_scene.setup_aov_glow(KIT, scene, GLOW_AOV, GLARE_STRENGTH, GLARE_SIZE, GLOW_SOFTEN, GLOW_SOFTEN_WEIGHT)

    # --- la camera: arretra lungo il suo asse, dal poliedro dipinto al quadro intero ---
    bl_anim.key_value(cam, "location",
                      [(f, tuple(ev.eye0 + (ev.eye1 - ev.eye0) * smootherstep(time_of(f), *PULLBACK)))
                       for f in range(frame_of(PULLBACK[0]), frame_of(PULLBACK[1]) + 1)],
                      interpolation='LINEAR')

    # --- il quadro: gira, si sposta e svanisce ---
    painting, p_mat = story.build_painting(KIT, painting_img, layout)
    fade(p_mat, [(PAINT_FADE[0], 1.0), (PAINT_FADE[1], 0.0)])
    bl_anim.key_visibility(painting, [(FRAME_START, True), (frame_of(PAINT_FADE[1]) + 1, False)])

    def painting_world(f):
        return ev.painting_matrix(smootherstep(time_of(f), *TURN))

    poses = [(f, painting_world(f).decompose()) for f in frames]
    painting.rotation_mode = 'QUATERNION'
    bl_anim.key_value(painting, "location", [(f, tuple(loc)) for f, (loc, _, _) in poses],
                      interpolation='LINEAR')
    bl_anim.key_value(painting, "rotation_quaternion", [(f, tuple(q)) for f, (_, q, _) in poses],
                      interpolation='LINEAR')

    # --- M: mover (posizione, scala, giro) -> orient (la posa del quadro) -> M ---
    face_img = KIT.load_image(m_scene.FACE_TEXTURE_FILE)
    uvs = m_scene.face_uvs(face_img, m_scene.FACE_TEXTURE_UV_PX, m_scene.FACE_TEXTURE_UV_INSET)
    m_mat = story.face_material(KIT, face_img, uvs)          # Look 0: i colori del quadro
    fade(m_mat, [(FACES_IN[0], 1.0), (FACES_IN[1], 0.0), (FACES_OUT[0], 0.0), (FACES_OUT[1], 1.0)])
    add_section_cut(m_mat, painting)
    mover = KIT.new_object("mover")
    mover.empty_display_size = 0.5
    mover.scale = (ev.s0,) * 3
    orient = KIT.new_object("orient", parent=mover)
    orient.rotation_euler = [math.radians(a) for a in story.ORIENT_EULER_DEG]
    m_obj = KIT.new_object("M", m_scene.merged_mesh(KIT, md, m_mat, uvs), parent=orient)
    bl_utils.merge_by_distance(m_obj)
    m_obj.visible_shadow = False
    bl_anim.key_visibility(m_obj, [(FRAME_START, True), (frame_of(MIGRATE[0]), False)])
    spin = spin_angles(frames)

    def frame_of_m(f):
        """Il centro di M e la sua rotazione attorno alla verticale: quella
        che gli da' il quadro, piu' il suo giro."""
        t = time_of(f)
        loc, q, _ = ev.m_frame(smootherstep(t, *TURN), smootherstep(t, *EXIT)).decompose()
        return loc, q.to_euler().z + spin[f]

    m_poses = {f: frame_of_m(f) for f in frames}
    bl_anim.key_value(mover, "location", [(f, tuple(m_poses[f][0])) for f in frames],
                      interpolation='LINEAR')
    bl_anim.key_value(mover, "rotation_euler", [(f, (0.0, 0.0, m_poses[f][1])) for f in frames],
                      interpolation='LINEAR')
    O = story.orient_matrix()

    def world_of(f):
        loc, angle = m_poses[f]
        return Matrix.Translation(loc) @ Matrix.Rotation(angle, 4, 'Z') @ Matrix.Scale(ev.s0, 4) @ O

    lit = build_section_lines(md, world_of, painting_world, frames)

    # --- l'icosaedro ---
    build_icosahedron(orient, md)

    # --- i 240 triangoli: seguono M, poi migrano nella griglia ---
    tri_mat = story.face_material(KIT, face_img, uvs)        # come M, senza il taglio
    mesh = m_scene.triangle_mesh(KIT, tri_mat, uvs)
    tris = [m_scene.Tri(p) for p in pieces.m_pieces(md)]

    def normal_of_tri(tri):
        n = Vector(tri.piece.normal)
        return lambda f: (Matrix.Rotation(m_poses[f][1], 3, 'Z') @ O.to_3x3() @ n).normalized()

    f_mig = frame_of(MIGRATE[0])
    centres = [np.asarray(world_of(f_mig) @ tri.loc) for tri in tris]
    normals = [np.asarray(normal_of_tri(tri)(f_mig)) for tri in tris]
    order = departure_order(centres, normals, ev.eye1)
    departs = departure_times(order)
    targets = ev.grid_poses(tris)
    mig_frames = [f for f in frames if f >= f_mig]
    for tri, target, t_dep in zip(tris, targets, departs):
        obj = KIT.new_object(f"tri_{tri.piece.index:03d}", mesh)
        obj.visible_shadow = False
        bl_anim.apply_keys(obj, migration_keys(tri, world_of, normal_of_tri(tri), t_dep, target, mig_frames))
        bl_anim.set_interpolation(obj, 'LINEAR', bl_anim.POSE_PATHS)
        bl_anim.key_visibility(obj, [(FRAME_START, False), (f_mig, True)])

    scene.frame_set(FRAME_START)
    print(f"[scene-1 v4] frame {FRAME_START}-{FRAME_END} a {FPS} fps ({END:.0f} s)")
    print(f"[scene-1 v4] la camera arretra da {ev.eye0[1]:.2f} a {ev.eye1[1]:.2f}; M alla scala "
          f"{ev.s0:.3f}; il quadro gira di {story.EXIT_TILT} gradi su un arco di raggio "
          f"{ev.turn_radius:.2f}; M esce di {ev.exit_distance:.2f}, fino a {np.round(ev.m_end, 2)}; "
          f"la linea della sezione da {time_of(lit[0]):.2f} a {time_of(lit[-1]):.2f} s")
    print(f"[scene-1 v4] griglia a {ev.grid_distance():.2f} dalla camera, triangoli scalati a "
          f"{targets[0][2]:.3f}; partenze da {departs.min():.2f} a {departs.max():.2f} s, in volo "
          f"{FLY_SECONDS} s")


build()
