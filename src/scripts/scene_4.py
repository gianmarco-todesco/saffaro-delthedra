"""
scene_4.py -- monoformi, biformi, triformi (biform_deltahedra), poi la stella
octangula va al suo posto nella platea dei deltaedri di Cundy e Olshevsky
(cundy_deltahedra).

--------------------------------------------------------------------------
LA SCALETTA (secondi)
--------------------------------------------------------------------------
 0 - 1    compaiono, a mezzo secondo l'uno dall'altro, l'icosaedro, la
          stella octangula e il composto di tre tetraedri; girano su se
          stessi rallentando, e si fermano nella posa (entro 8.5).
 9        compaiono le sferette sui vertici, colorate per tipo.
 9.6      le scritte, un poliedro dopo l'altro: in alto "Un solo tipo", "Due
          tipi", "Tre tipi"; sulla stella e sul composto una scritta per tipo
          ("tipo A", ...) con una breve freccia verso un vertice di quel tipo.
16        l'icosaedro e il composto escono di lato, veloci; le scritte
          sfumano e le sferette della stella spariscono.
17        la stella salta al suo posto nella platea (cundy_deltahedra) e
          prende il suo colore; la camera indietreggia fino all'inquadratura
          della platea, e intanto compaiono tutti gli altri.
30        fine.

--------------------------------------------------------------------------
LE SCELTE
--------------------------------------------------------------------------
* Il mondo e' quello di cundy_deltahedra fin dall'inizio: pavimento, ombre
  morbide, la camera alta CAMERA_ELEVATION gradi e la stessa rotazione dal
  primo all'ultimo fotogramma. All'inizio e' vicina ai tre poliedri, che
  stanno sul pavimento davanti alla platea (TRIO_Y); a 17 s si sposta
  (indietro e in alto) fino all'inquadratura della platea.
* Tutti i poliedri hanno lo spigolo 1, la loro grandezza vera: la stella
  arriva nella platea senza cambiare grandezza. Fa un arco (ARC_HEIGHT)
  per passare sopra la prima fila, che intanto compare.
* I tre poliedri sono grigi come in biform_deltahedra, perche' risaltino le
  sferette; la stella sfuma nel suo pastello mentre va al suo posto. La
  platea ha i colori, le rotazioni e la disposizione di cundy_deltahedra.
* Le scritte stanno su un piano subito davanti all'obiettivo, figlie della
  camera (come in biform_deltahedra). Per ogni tipo si sceglie un vertice
  visibile (ray cast a poliedri fermi); la freccia va dal centro del
  poliedro verso il vertice, la scritta sta oltre la coda. Fra tutte le
  combinazioni si sceglie quella in cui le scritte stanno dentro
  l'immagine, non toccano i titoli, i poliedri e le altre scritte, e sono
  il piu' lontano possibile fra loro.
"""

import bpy
import bmesh
import mathutils

import os, sys
import math
import itertools
import importlib

import numpy as np

# rendi possibile importare i moduli da src/libs
# (nota bene: __file__ non funziona dallo script editor di Blender,
#  quindi si ricava il path del file dal datablock di testo attivo)
def _find_libs_dir():
    txt = getattr(getattr(bpy.context, "space_data", None), "text", None)
    if txt is None:  # lo script non gira dal Text Editor: cerco il datablock per nome
        txt = bpy.data.texts.get("scene_4.py")
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
import bl_utils, bl_anim, m_scene, deltahedra
for _mod in (bl_utils, bl_anim, m_scene, deltahedra):
    importlib.reload(_mod)

from mathutils import Vector, Quaternion, Euler


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

PREFIX          = "S4"
COLLECTION_NAME = "scene_4"

# saffaro/..., accanto al repository: src/libs -> src -> saffaro-delthedra -> saffaro
_SAFFARO   = os.path.dirname(os.path.dirname(os.path.dirname(_LIBS)))
ASSETS_DIR = os.path.join(_SAFFARO, "assets")
CONVEX_DIR = os.path.join(_SAFFARO, "modelli-3d", "convex-deltahedra")
CUNDY_DIR  = os.path.join(_SAFFARO, "3dmodels", "cundy", "D2-Deltaedri di Cundy")
STELLA     = "06_Octaugmented_Octahedron"

FPS         = 24
RESOLUTION  = (1920, 1080)
FRAME_START = 1
SENSOR_W    = 36.0
ASPECT      = RESOLUTION[0] / RESOLUTION[1]

# --- i tre poliedri: (chiave, file o 'CHAIN', posa da fermi (Eulero XYZ in
# gradi), x del centro). Icosaedro e stella hanno le pose di biform_deltahedra.
# Il composto no: con questa camera, piu' alta, quella posa lo mostra quasi di
# punta. Questa e' la migliore fra 20000 rotazioni casuali con tutti e sei i
# vertici visibili: i vertici, nell'immagine, il piu' lontano possibile fra
# loro e dal centro del composto (da cui partono le frecce).
TRIO = [
    ("ico",    os.path.join(CONVEX_DIR, "08_Regular_Icosahedron.obj"), (0.0, 0.0, 12.0),       -3.4),
    ("stella", os.path.join(CUNDY_DIR, STELLA + ".obj"),               (-90.0, 0.0, 20.0),      0.0),
    ("chain",  "CHAIN",                                                (146.84, 7.9, -123.28),  3.4),
]
TRIO_Y      = -4.5               # davanti alla prima fila della platea (che sta a y = 0)
HEADINGS    = {"ico": "Un solo tipo", "stella": "Due tipi", "chain": "Tre tipi"}

# --- la scaletta, in secondi ---
APPEAR_GAP    = 0.5              # fra un poliedro e il successivo
GROW_SECONDS  = 1.0              # scala da 0 a 1
SPIN_SECONDS  = 7.5              # dall'inizio della comparsa all'arresto
SPIN_TURNS    = 1.5              # quanti giri fa mentre compare e rallenta
VERTICES_AT   = 9.0              # le sferette
VERTEX_GROW   = 0.5
LABELS_AT     = 9.6              # le scritte del primo poliedro...
LABELS_GAP    = 0.4              # ... e degli altri, dopo
LABEL_FADE    = 0.5
EXIT_AT       = 16.0             # icosaedro e composto escono, le scritte sfumano
EXIT_SECONDS  = 0.6
MOVE_AT       = 17.0             # la stella va al suo posto, la camera indietreggia
MOVE_SECONDS  = 3.0
ARC_HEIGHT    = 2.5              # quanto si alza la stella a meta' strada
OTHERS_AT     = 17.0             # la platea compare
END           = 30.0

# --- i colori ---
FACE_SRGB      = (150, 156, 170)  # i tre poliedri: neutri, perche' risaltino le sferette
FACE_ROUGHNESS = 0.6
VERTEX_TYPES = {                  # (poliedro, triangoli nel vertice) -> (lettera, colore sRGB)
    ("ico", 5):    ("",  (245, 245, 240)),
    ("stella", 3): ("A", (240, 150, 40)),
    ("stella", 8): ("B", (40, 175, 235)),
    ("chain", 3):  ("A", (240, 150, 40)),
    ("chain", 4):  ("B", (40, 175, 235)),
    ("chain", 5):  ("C", (150, 205, 70)),
}
VERTEX_RADIUS = 0.07

# --- la camera all'inizio: i tre poliedri occupano START_FILL dell'immagine,
# con il loro centro all'altezza TRIO_SCREEN_Y (sopra c'e' la riga dei titoli)
START_FILL    = (0.78, 0.50)
TRIO_SCREEN_Y = 0.45

# --- le scritte (frazioni dell'altezza dell'immagine) ---
HEADING_Y      = 0.86            # centro dei titoli
HEADING_HEIGHT = 0.042           # altezza delle maiuscole dei titoli
LABEL_HEIGHT   = 0.030           # e delle scritte dei tipi
ARROW_GAP      = 0.010           # fra la punta della freccia e la sferetta
ARROW_LENGTH   = 0.060
ARROW_WIDTH    = 0.0025          # lo spessore dell'asta
ARROW_HEAD     = (0.016, 0.011)  # lunghezza e mezza larghezza della punta
LABEL_PAD      = 0.010           # fra la coda della freccia e la scritta
FRAME_MARGIN   = 0.03            # le scritte stanno almeno cosi' dentro l'immagine
LABEL_DEPTH    = 1.0             # distanza del piano delle scritte dalla camera

# --- la platea: come cundy_deltahedra ---
ROWS      = [3, 4, 5, 6, 7]
GAP       = 0.8
ROW_GAP   = 0.6
CLEARANCE = 0.3
FLOOR_SRGB      = (30, 38, 56)
FLOOR_ROUGHNESS = 0.85
FLOOR_SPECULAR  = 0.05
FLOOR_SIZE      = 400.0
SUN_SIZE_DEG    = 8.0
PASTEL_L   = 0.82
PASTEL_C   = 0.085
HUE_START  = 20.0
HUE_STEP   = 137.508
ROUGHNESS  = 0.5
OTHERS_GAP   = 0.3
OTHERS_GROW  = 0.8
SPIN_SECONDS_PER_TURN = 10.0
CAMERA_ELEVATION = 22.0
CAMERA_LENS      = 40.0
FRAME_FILL       = (0.90, 0.80)
LIGHT_IN_CAMERA   = (0.866, -0.5, 0.0)
SKY_SUN_ELEVATION = 30.0
SKY_STRENGTH      = 0.1


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


def smooth(u):
    return u * u * (3.0 - 2.0 * u)


def spin_angle(n, t):
    """L'n-esimo dei tre gira attorno alla verticale e rallenta fino a
    fermarsi nella posa (angolo 0) dopo SPIN_SECONDS."""
    u = ramp(t, n * APPEAR_GAP, n * APPEAR_GAP + SPIN_SECONDS)
    return -2.0 * math.pi * SPIN_TURNS * (1.0 - u) ** 2


def platea_angle(n, frame):
    """La rotazione dell'n-esimo pezzo della platea, come in cundy_deltahedra:
    sempre in rotazione, ognuno con la sua fase."""
    phase = 2.0 * math.pi * ((n * 0.618034) % 1.0)
    return phase + 2.0 * math.pi / (SPIN_SECONDS_PER_TURN * FPS) * (frame - FRAME_START)


def platea_color(n):
    hue = (HUE_START + n * HUE_STEP) % 360.0
    return m_scene.oklch_to_linear(PASTEL_L, PASTEL_C, hue)[0]


def label_fade_keys(n):
    t0 = LABELS_AT + n * LABELS_GAP
    return [(frame_of(t0), 0.0), (frame_of(t0 + LABEL_FADE), 1.0),
            (frame_of(EXIT_AT), 1.0), (frame_of(EXIT_AT + LABEL_FADE), 0.0)]


# =============================================================================
# COSTRUZIONE
# =============================================================================

KIT  = m_scene.Kit(PREFIX, COLLECTION_NAME, ASSETS_DIR)
RIG  = m_scene.CameraRig('PERSP', 10.0, SENSOR_W, RESOLUTION)
VIEW = deltahedra.View(CAMERA_ELEVATION, CAMERA_LENS, SENSOR_W, ASPECT)


def load_trio_piece(source):
    """(vertici, facce) con spigolo 1 (la grandezza vera), centrati."""
    if source == "CHAIN":
        V, faces = deltahedra.tetrahedron_chain()
        return V - V.mean(axis=0), faces
    return deltahedra.load_welded(source)


def build_floor_and_sky(models, rot):
    light = rot.to_matrix() @ Vector(LIGHT_IN_CAMERA)
    m_scene.setup_sky_world(KIT, math.radians(SKY_SUN_ELEVATION),
                            m_scene.sky_rotation(-light), SKY_STRENGTH,
                            sun_size=math.radians(SUN_SIZE_DEG))
    m_scene.build_floor(KIT, FLOOR_SRGB, FLOOR_ROUGHNESS, FLOOR_SPECULAR, FLOOR_SIZE,
                        y=sum(m.location[1] for m in models) / len(models))


def build_trio(order):
    """I tre poliedri: compaiono, girano e si fermano; icosaedro e composto
    escono di lato, la stella va al suo posto nella platea. Restituisce
    [(chiave, oggetto, vertici, gradi)] e la posizione della stella."""
    frames = range(FRAME_START, FRAME_END + 1)
    n_stella = next(n for n, m in enumerate(order) if m.name == STELLA)
    stella_model = order[n_stella]
    out = []
    for n, (key, source, euler, x) in enumerate(TRIO):
        V, faces = load_trio_piece(source)
        radius = float(np.linalg.norm(V, axis=1).max())
        mat = m_scene.wire_material(KIT, f"mat_{key}", m_scene.linear_rgba(FACE_SRGB),
                                    roughness=FACE_ROUGHNESS if key != "stella" else ROUGHNESS)
        mesh = bpy.data.meshes.new(KIT.name(key))
        mesh.from_pydata([tuple(v) for v in V], [], faces)
        mesh.materials.append(mat)
        mesh.update()
        obj = KIT.new_object(key, mesh)
        start = Vector((x, TRIO_Y, radius + CLEARANCE))
        obj.location = start
        t0 = n * APPEAR_GAP
        bl_anim.key_value(obj, "scale", [(frame_of(t0), (0.0,) * 3),
                                         (frame_of(t0 + GROW_SECONDS), (1.0,) * 3)])
        pose = Euler([math.radians(a) for a in euler], 'XYZ').to_quaternion()
        up = Vector((0.0, 0.0, 1.0))
        rot_keys, loc_keys = [], []
        for f in frames:
            t = time_of(f)
            q = Quaternion(up, spin_angle(n, t)) @ pose
            if key == "stella":
                w = smooth(ramp(t, MOVE_AT, MOVE_AT + MOVE_SECONDS))
                if w > 0.0:
                    q = q.slerp(Quaternion(up, platea_angle(n_stella, f)), w)
                    end = Vector(tuple(stella_model.location))
                    p = start.lerp(end, w) + up * (ARC_HEIGHT * math.sin(math.pi * w))
                    loc_keys.append((f, tuple(p)))
            rot_keys.append((f, tuple(q)))
        obj.rotation_mode = 'QUATERNION'
        bl_anim.key_value(obj, "rotation_quaternion", rot_keys, interpolation='LINEAR')
        if key == "stella":
            bl_anim.key_value(obj, "location", [(frame_of(MOVE_AT) - 1, tuple(start))] + loc_keys,
                              interpolation='LINEAR')
            # il colore: dal grigio al pastello della platea, durante il salto
            bl_anim.key_value(mat.node_tree, 'nodes["Principled BSDF"].inputs[0].default_value',
                              [(frame_of(MOVE_AT), m_scene.linear_rgba(FACE_SRGB)),
                               (frame_of(MOVE_AT + MOVE_SECONDS), platea_color(n_stella))])
        else:
            # di lato, fuori dall'immagine, accelerando (u^2)
            side = -1.0 if x < 0 else 1.0
            f0, f1 = frame_of(EXIT_AT), frame_of(EXIT_AT + EXIT_SECONDS)
            travel = VIEW.frame_width(START_DISTANCE) * 0.75
            bl_anim.key_value(obj, "location",
                              [(f, tuple(start + Vector((side * travel * ((f - f0) / (f1 - f0)) ** 2, 0, 0))))
                               for f in range(f0, f1 + 1)], interpolation='LINEAR')
            bl_anim.key_visibility(obj, [(FRAME_START, True), (f1 + 1, False)])
        out.append((key, obj, V, deltahedra.vertex_degrees(len(V), faces)))
    return out, n_stella


def build_platea(order, n_stella):
    """Tutti gli altri pezzi di cundy_deltahedra, con la loro fase e il loro
    colore; compaiono dopo OTHERS_AT, nell'ordine della platea."""
    k = 0
    for n, m in enumerate(order):
        if n == n_stella:
            continue
        mesh = bpy.data.meshes.new(KIT.name(m.name))
        mesh.from_pydata([tuple(v) for v in m.vertices], [], m.faces)
        mesh.materials.append(m_scene.wire_material(KIT, f"mat_{m.name}", platea_color(n),
                                                    roughness=ROUGHNESS))
        mesh.update()
        obj = KIT.new_object(m.name, mesh)
        obj.location = tuple(m.location)
        t0 = OTHERS_AT + k * OTHERS_GAP
        k += 1
        bl_anim.key_value(obj, "scale", [(frame_of(t0), (0.0,) * 3),
                                         (frame_of(t0 + OTHERS_GROW), (1.0,) * 3)])
        bl_anim.key_visibility(obj, [(FRAME_START, False), (frame_of(t0) + 1, True)])
        obj.rotation_mode = 'XYZ'
        bl_anim.key_value(obj, "rotation_euler",
                          [(FRAME_START, (0.0, 0.0, platea_angle(n, FRAME_START))),
                           (FRAME_END, (0.0, 0.0, platea_angle(n, FRAME_END)))],
                          interpolation='LINEAR')
    return k


def build_camera(models, trio_centres, trio_radii):
    """La camera: la stessa rotazione sempre; all'inizio inquadra i tre
    poliedri, dopo MOVE_AT si sposta all'inquadratura della platea."""
    global START_DISTANCE
    t_start, START_DISTANCE = deltahedra.frame_all(VIEW, trio_centres, trio_radii, START_FILL)
    # i tre poliedri un po' piu' in basso del centro: sopra ci sono i titoli
    h = VIEW.frame_width(START_DISTANCE) / ASPECT
    t_start = t_start + VIEW.up * ((0.5 - TRIO_SCREEN_Y) * h)
    t_end, d_end = deltahedra.frame_all(VIEW, [m.location for m in models],
                                        [m.radius for m in models], FRAME_FILL)
    rot = Vector(VIEW.back).to_track_quat('Z', 'Y')
    p0 = Vector(t_start + VIEW.back * START_DISTANCE)
    p1 = Vector(t_end + VIEW.back * d_end)
    cam = RIG.build(KIT, p0, clip_end=d_end + FLOOR_SIZE)
    cam.data.lens = CAMERA_LENS
    cam.rotation_mode = 'QUATERNION'
    cam.rotation_quaternion = rot
    bl_anim.key_value(cam, "location", [(frame_of(MOVE_AT), tuple(p0)),
                                        (frame_of(MOVE_AT + MOVE_SECONDS), tuple(p1))])
    return cam, rot, d_end


def visible_vertices(scene, cam, trio):
    """{(chiave, indice): visibile}, a poliedri fermi: il raggio dalla camera
    si ferma poco prima del vertice; se incontra una faccia, e' coperto."""
    from bpy_extras.object_utils import world_to_camera_view as w2c
    dg = bpy.context.evaluated_depsgraph_get()
    eye = cam.matrix_world.translation
    seen = {}
    for key, obj, V, _ in trio:
        for i, v in enumerate(V):
            p = obj.matrix_world @ Vector(v)
            q = w2c(scene, cam, p)
            if not (0.0 <= q.x <= 1.0 and 0.0 <= q.y <= 1.0):
                seen[(key, i)] = False
                continue
            d = p - eye
            hit, *_ = scene.ray_cast(dg, eye, d.normalized(), distance=d.length - 1e-3)
            seen[(key, i)] = not hit
    return seen


def build_spheres(trio):
    """Le sferette sui vertici, figlie del poliedro: compaiono a VERTICES_AT;
    quelle della stella spariscono quando le scritte sfumano."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=VERTEX_RADIUS)
    for face in bm.faces:
        face.smooth = True
    shells = {}
    for (key, degree), (_, srgb) in VERTEX_TYPES.items():
        mesh = bpy.data.meshes.new(KIT.name(f"sphere_{key}_{degree}"))
        bm.to_mesh(mesh)
        mesh.materials.append(m_scene.wire_material(KIT, f"vertex_{key}_{degree}",
                                                    m_scene.linear_rgba(srgb), roughness=0.35))
        shells[(key, degree)] = mesh
    bm.free()
    for key, obj, V, deg in trio:
        keys = [(frame_of(VERTICES_AT), (0.0,) * 3), (frame_of(VERTICES_AT + VERTEX_GROW), (1.0,) * 3)]
        if key == "stella":
            keys += [(frame_of(EXIT_AT), (1.0,) * 3), (frame_of(EXIT_AT + LABEL_FADE), (0.0,) * 3)]
        for i, v in enumerate(V):
            s = KIT.new_object(f"{key}_v{i:02d}", shells[(key, deg[i])], parent=obj)
            s.location = tuple(v)
            s.visible_shadow = False
            bl_anim.key_value(s, "scale", keys)


# --- le scritte, sul piano davanti all'obiettivo ---

def plane_size():
    """(larghezza, altezza) dell'inquadratura sul piano delle scritte."""
    w = LABEL_DEPTH * SENSOR_W / CAMERA_LENS
    return w, w / ASPECT


def to_plane(cam, world_point):
    """Il punto del piano delle scritte (coordinate della camera) che copre
    `world_point` nell'immagine, e la profondita' del punto."""
    c = cam.matrix_world.inverted() @ Vector(world_point)
    return Vector((c.x, c.y)) * (LABEL_DEPTH / -c.z), -c.z


def overlay_material(suffix):
    """Bianco emissivo che sfuma nel trasparente col nodo 'Fade'."""
    mat, nodes, links = KIT.new_material(suffix)
    out = nodes.new("ShaderNodeOutputMaterial")
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    clear = nodes.new("ShaderNodeBsdfTransparent")
    mix = nodes.new("ShaderNodeMixShader")
    mix.name = "Fade"
    mix.inputs["Fac"].default_value = 0.0
    links.new(clear.outputs["BSDF"], mix.inputs[1])
    links.new(emit.outputs["Emission"], mix.inputs[2])
    links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return mat


def new_text(cam, name, text, cap_height, mat):
    """Una scritta centrata, figlia della camera, sul piano delle scritte
    (nell'origine: la si sposta dopo). Restituisce (oggetto, larghezza,
    altezza) nel piano."""
    _, h = plane_size()
    curve = bpy.data.curves.new(KIT.name(name), 'FONT')
    curve.body = text
    curve.align_x, curve.align_y = 'CENTER', 'CENTER'
    curve.size = cap_height * h / 0.72       # size e' l'altezza del corpo; le maiuscole ne sono circa 0.72
    curve.materials.append(mat)
    obj = KIT.new_object(name, curve, parent=cam)
    obj.location = (0.0, 0.0, -LABEL_DEPTH)
    obj.visible_shadow = False
    bpy.context.view_layer.update()
    return obj, obj.dimensions.x, obj.dimensions.y


def arrow_mesh(name, tail, head, mat):
    """La freccia da `tail` a `head` (punti del piano): un'asta e una punta,
    un solo oggetto figlio della camera."""
    _, h = plane_size()
    d = head - tail
    u = d.normalized()
    n = Vector((-u.y, u.x))
    head_len, head_half = ARROW_HEAD[0] * h, ARROW_HEAD[1] * h
    half = ARROW_WIDTH * h / 2.0
    base = head - u * head_len
    verts = [tail + n * half, tail - n * half, base - n * half, base + n * half,
             base + n * head_half, base - n * head_half, head]
    mesh = bpy.data.meshes.new(KIT.name(name))
    mesh.from_pydata([(*v, 0.0) for v in verts], [], [(0, 1, 2, 3), (4, 5, 6)])
    mesh.materials.append(mat)
    return mesh


def rect_overlap(a, b):
    """Due rettangoli (cx, cy, mezza larghezza, mezza altezza) si toccano?"""
    return abs(a[0] - b[0]) < a[2] + b[2] and abs(a[1] - b[1]) < a[3] + b[3]


def rect_hits_disk(r, c, radius):
    dx = max(abs(r[0] - c.x) - r[2], 0.0)
    dy = max(abs(r[1] - c.y) - r[3], 0.0)
    return dx * dx + dy * dy < radius * radius


def build_labels(scene, cam, trio, seen):
    """Titoli, scritte dei tipi e frecce, con la loro dissolvenza.
    Restituisce le righe del resoconto."""
    w, h = plane_size()
    discs = {}
    for key, obj, V, _ in trio:
        c, depth = to_plane(cam, obj.matrix_world.translation)
        radius = float(np.linalg.norm(V, axis=1).max()) * LABEL_DEPTH / depth
        discs[key] = (c, radius)
    mats = {key: overlay_material(f"overlay_{key}") for key, *_ in trio}
    for n, (key, *_) in enumerate(trio):
        bl_anim.key_value(mats[key].node_tree, 'nodes["Fade"].inputs[0].default_value',
                          label_fade_keys(n))

    # i titoli
    taken = []                                   # rettangoli gia' occupati
    for key, *_ in trio:
        obj, tw, th = new_text(cam, f"heading_{key}", HEADINGS[key], HEADING_HEIGHT, mats[key])
        x, y = discs[key][0].x, (HEADING_Y - 0.5) * h
        obj.location = (x, y, -LABEL_DEPTH)
        taken.append((x, y, tw / 2.0, th / 2.0))

    # le scritte dei tipi: per ogni poliedro la combinazione migliore
    report = []
    for key, obj, V, deg in trio:
        types = sorted(set(deg))
        if len(types) < 2:
            continue
        texts = {}
        for t in types:
            letter = VERTEX_TYPES[(key, t)][0]
            texts[t] = new_text(cam, f"label_{key}_{t}", f"tipo {letter}", LABEL_HEIGHT, mats[key])
        candidates = {}
        for t in types:
            _, tw, th = texts[t]
            cands = []
            for i in range(len(V)):
                if deg[i] != t or not seen[(key, i)]:
                    continue
                p, depth = to_plane(cam, obj.matrix_world @ Vector(V[i]))
                d = p - discs[key][0]
                if d.length < 1e-9:
                    continue
                u = d.normalized()
                head = p + u * (VERTEX_RADIUS * LABEL_DEPTH / depth + ARROW_GAP * h)
                tail = head + u * (ARROW_LENGTH * h)
                off = abs(u.x) * tw / 2.0 + abs(u.y) * th / 2.0 + LABEL_PAD * h
                c = tail + u * off
                cands.append((i, head, tail, (c.x, c.y, tw / 2.0, th / 2.0)))
            if not cands:
                raise ValueError(f"{key}: nessun vertice visibile con {t} triangoli")
            candidates[t] = cands
        best, best_score = None, None
        for combo in itertools.product(*(candidates[t] for t in types)):
            rects = [c[3] for c in combo]
            bad = 0
            for r in rects:
                if abs(r[0]) + r[2] > w / 2.0 - FRAME_MARGIN * h or abs(r[1]) + r[3] > h / 2.0 - FRAME_MARGIN * h:
                    bad += 1
                bad += sum(rect_overlap(r, q) for q in taken)
                bad += sum(rect_hits_disk(r, c, rad) for c, rad in discs.values())
            for a, b in itertools.combinations(rects, 2):
                bad += rect_overlap(a, b)
            spread = min(math.hypot(a[0] - b[0], a[1] - b[1]) for a, b in itertools.combinations(rects, 2))
            score = spread - 10.0 * bad
            if best_score is None or score > best_score:
                best, best_score, best_bad = combo, score, bad
        for t, (i, head, tail, r) in zip(types, best):
            texts[t][0].location = (r[0], r[1], -LABEL_DEPTH)
            arrow = KIT.new_object(f"arrow_{key}_{t}", arrow_mesh(f"arrow_{key}_{t}", tail, head, mats[key]),
                                   parent=cam)
            arrow.location = (0.0, 0.0, -LABEL_DEPTH)
            arrow.visible_shadow = False
            taken.append(r)
            report.append(f"{key}, tipo {VERTEX_TYPES[(key, t)][0]} ({t} triangoli): vertice {i}, "
                          f"{len(candidates[t])} candidati visibili")
        if best_bad:
            report.append(f"{key}: ATTENZIONE, {best_bad} sovrapposizioni nella scelta migliore")
    return report


def build():
    KIT.clear_previous_run()
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.render.resolution_x, scene.render.resolution_y = RESOLUTION
    scene.frame_start, scene.frame_end = FRAME_START, FRAME_END
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    KIT.new_collection(scene)

    models = deltahedra.load_models(CUNDY_DIR, sum(ROWS))
    order, rows = deltahedra.arrange(models, ROWS, GAP, ROW_GAP, CLEARANCE)

    trio_V = [load_trio_piece(src)[0] for _, src, _, _ in TRIO]
    trio_radii = [float(np.linalg.norm(V, axis=1).max()) for V in trio_V]
    trio_centres = [np.array([x, TRIO_Y, r + CLEARANCE]) for (_, _, _, x), r in zip(TRIO, trio_radii)]
    cam, rot, d_end = build_camera(models, trio_centres, trio_radii)
    build_floor_and_sky(models, rot)

    trio, n_stella = build_trio(order)
    # visibilita' e scritte a poliedri fermi, prima che ci siano sferette e platea
    scene.frame_set(frame_of(LABELS_AT))
    seen = visible_vertices(scene, cam, trio)
    build_spheres(trio)
    report = build_labels(scene, cam, trio, seen)
    n_others = build_platea(order, n_stella)
    scene.frame_set(FRAME_START)

    row = next(k for k, r in enumerate(rows) if any(m.name == STELLA for m in r))
    print(f"[scene_4] frame {FRAME_START}-{FRAME_END} a {FPS} fps ({END:.0f} s); camera da "
          f"{START_DISTANCE:.2f} a {d_end:.2f}")
    print(f"[scene_4] la stella va nella fila {row + 1}; gli altri {n_others} compaiono fra "
          f"{OTHERS_AT:.1f} e {OTHERS_AT + (n_others - 1) * OTHERS_GAP + OTHERS_GROW:.1f} s")
    for line in report:
        print(f"[scene_4] {line}")


START_DISTANCE = None
build()
