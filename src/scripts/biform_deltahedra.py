"""
biform_deltahedra.py -- deltaedri monoformi, biformi e triformi: con uno, due
o tre tipi di vertici.

--------------------------------------------------------------------------
LA SCALETTA
--------------------------------------------------------------------------
Tre poliedri affiancati compaiono uno dopo l'altro, a APPEAR_GAP secondi di
distanza: la scala va da 0 a 1 (ease in/out) mentre girano su se stessi, poi
rallentano fino a fermarsi. Fermi tutti, compaiono le scritte con le loro
linee, un poliedro dopo l'altro; restano HOLD_SECONDS e poi spariscono.

  icosaedro           monoforme: 12 vertici, 5 triangoli in ognuno
  stella octangula    biforme: 8 punte con 3 triangoli (tipo A), 6 vertici
                      rientranti con 8 (tipo B). E' l'ottaedro otta-aumentato
                      di Cundy, 3dmodels/cundy
  tre tetraedri       triforme: tre tetraedri regolari in catena, incollati
                      faccia a faccia. 6 vertici e 8 facce: le due estremita'
                      con 3 triangoli (A), i due vertici dopo con 4 (B), i due
                      centrali con 5 (C). Una rotazione di 180 gradi scambia i
                      vertici dello stesso tipo. I deltaedri convessi sono al
                      piu' biformi, e con 5 vertici c'e' solo la bipiramide
                      triangolare (biforme): questo e' il piu' semplice
                      triforme che conosciamo

Il tipo di un vertice e' il numero di triangoli che vi concorrono: per questi
poliedri coincide con la classe di simmetria, ed e' quello che chi guarda puo'
contare.

--------------------------------------------------------------------------
SCRITTE E LINEE
--------------------------------------------------------------------------
Stanno su un piano subito davanti all'obiettivo (LABEL_DEPTH), figlie della
camera: coprono i poliedri, e un punto di quel piano copre nell'immagine
esattamente quello che c'e' dietro. Ogni scritta ha una linea verso il vertice
del suo tipo piu' vicino, fra quelli visibili (LINES = 'ALL': verso tutti), e
la linea si ferma sul bordo della sferetta.

Un vertice e' visibile se il raggio dalla camera al vertice non incontra facce
prima di arrivarci (ray cast sulla scena, a poliedri fermi, prima di creare
sferette e scritte) e se cade nell'inquadratura.
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
        txt = bpy.data.texts.get("biform_deltahedra.py")
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
import geometry, bl_utils, bl_anim, m_scene
for _mod in (geometry, bl_utils, bl_anim, m_scene):
    importlib.reload(_mod)

from mathutils import Vector


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

PREFIX          = "BD"
COLLECTION_NAME = "biform_deltahedra"

# saffaro/..., accanto al repository: src/libs -> src -> saffaro-delthedra -> saffaro
_SAFFARO   = os.path.dirname(os.path.dirname(os.path.dirname(_LIBS)))
ASSETS_DIR = os.path.join(_SAFFARO, "assets")
CONVEX_DIR = os.path.join(_SAFFARO, "modelli-3d", "convex-deltahedra")
CUNDY_DIR  = os.path.join(_SAFFARO, "3dmodels", "cundy", "D2-Deltaedri di Cundy")

FPS         = 24
RESOLUTION  = (1920, 1080)
FRAME_START = 1

# I poliedri: (chiave, file o 'CHAIN', posa da fermi come angoli di Eulero XYZ
# in gradi, x del centro). La stella octangula nel file ha un asse ternario
# lungo Y: lo si porta in verticale, cosi' in cima c'e' una punta. La catena
# ha l'asse lungo inclinato di 50 gradi nell'immagine, ruotata attorno a
# quell'asse in modo da mostrare piu' superficie e tenere i sei vertici, tutti
# visibili, il piu' lontano possibile fra loro sullo schermo (cercata fra
# inclinazioni di 20, 35, 50 gradi e rotazioni a passi di 15).
POLYHEDRA = [
    ("ico",    os.path.join(CONVEX_DIR, "08_Regular_Icosahedron.obj"),     (0.0, 0.0, 12.0),   -3.4),
    ("stella", os.path.join(CUNDY_DIR, "06_Octaugmented_Octahedron.obj"), (-90.0, 0.0, 20.0),  0.0),
    ("chain",  "CHAIN",                                                   (99.36, -35.46, 117.23), 3.4),
]
PIECE_RADIUS = 1.0               # ogni poliedro sta in una sfera di questo raggio

# --- la scaletta, in secondi ---
APPEAR_GAP    = 0.5              # fra un poliedro e il successivo
GROW_SECONDS  = 1.0              # scala da 0 a 1 (ease in/out)
SPIN_SECONDS  = 2.5              # dall'inizio della comparsa all'arresto
SPIN_TURNS    = 1.0              # quanti giri fa mentre compare e rallenta
LABELS_PAUSE  = 0.4              # fra l'arresto dell'ultimo e la prima scritta
LABELS_GAP    = 0.5              # fra le scritte di un poliedro e quelle del successivo
LABEL_FADE    = 0.5              # quanto ci mette una scritta a comparire o sparire
HOLD_SECONDS  = 4.5              # tutto fermo, con le scritte
TAIL_SECONDS  = 0.5              # dopo che le scritte sono sparite

# --- i colori (sRGB) ---
FACE_SRGB = (150, 156, 170)      # neutre, perche' risaltino le sferette
FACE_ROUGHNESS = 0.6
# Il tipo di vertice -- (poliedro, triangoli nel vertice) -- con la lettera e
# il colore della sferetta. Le lettere seguono il numero di triangoli.
VERTEX_TYPES = {
    ("ico", 5):    ("",  (245, 245, 240)),     # un solo tipo: bianco
    ("stella", 3): ("A", (240, 150, 40)),      # arancio
    ("stella", 8): ("B", (40, 175, 235)),      # azzurro
    ("chain", 3):  ("A", (240, 150, 40)),
    ("chain", 4):  ("B", (40, 175, 235)),
    ("chain", 5):  ("C", (150, 205, 70)),      # verde
}
VERTEX_RADIUS = 0.07

# --- le scritte ---
# Dove sta la scritta di ogni tipo: (spostamento in x dal centro del
# poliedro nell'immagine, 'top' o 'bottom'). Le linee partono dal lato della
# scritta rivolto verso il poliedro.
LABEL_LAYOUT = {
    ("ico", 5):    (0.0,   "top"),
    ("stella", 3): (0.0,   "top"),
    ("stella", 8): (0.0,   "bottom"),
    ("chain", 3):  (0.06,  "top"),      # in questa posa il vertice A e' a destra:
    ("chain", 5):  (-0.06, "top"),      # cosi' le due linee non si incrociano
    ("chain", 4):  (0.0,   "bottom"),
}
LABEL_ROW_Y  = {"top": 0.80, "bottom": 0.20}   # centro della scritta, frazione dell'altezza
LABEL_HEIGHT = 0.030             # altezza delle lettere, in frazione dell'altezza dell'immagine
LINE_WIDTH   = 0.0022            # spessore delle linee, idem
LABEL_GAP    = 0.012             # fra la scritta e l'inizio della linea, idem
LABEL_DEPTH  = 1.0               # distanza del piano di scritte e linee dalla camera
# 'NEAREST' -> una linea sola, verso il vertice visibile piu' vicino alla scritta
# 'ALL'     -> una linea verso ogni vertice visibile del tipo
LINES = 'NEAREST'

# --- camera, fondo, luce: come deltahedra_1 ---
CAMERA_ELEVATION = 15.0
CAMERA_LENS      = 50.0
CAMERA_DISTANCE  = 19.0
BACKGROUND_CORNERS_SRGB = {
    "top_left":     (34, 46, 70),
    "top_right":    (16, 22, 38),
    "bottom_left":  (20, 28, 46),
    "bottom_right": (6, 8, 16),
}
BACKGROUND_BLEED  = 1.02
LIGHT_IN_CAMERA   = (0.866, -0.5, 0.0)
SKY_SUN_ELEVATION = 15.0
SKY_STRENGTH      = 0.1

SENSOR_W = 36.0
ASPECT   = RESOLUTION[0] / RESOLUTION[1]


# =============================================================================
# LA REGIA
# =============================================================================

def appear_at(n):
    """Quando comincia a comparire l'n-esimo poliedro (secondi)."""
    return n * APPEAR_GAP


T_STILL   = appear_at(len(POLYHEDRA) - 1) + max(GROW_SECONDS, SPIN_SECONDS)
T_LABELS  = T_STILL + LABELS_PAUSE
T_ALL_IN  = T_LABELS + (len(POLYHEDRA) - 1) * LABELS_GAP + LABEL_FADE
T_OUT     = T_ALL_IN + HOLD_SECONDS
T_END     = T_OUT + LABEL_FADE + TAIL_SECONDS
FRAME_END = FRAME_START + int(round(T_END * FPS))


def frame_of(t):
    return FRAME_START + int(round(t * FPS))


def time_of(frame):
    return (frame - FRAME_START) / FPS


def ramp(t, t0, t1):
    return min(1.0, max(0.0, (t - t0) / (t1 - t0)))


def spin_angle(n, t):
    """L'angolo di rotazione dell'n-esimo poliedro attorno al proprio asse
    verticale: parte girando e rallenta fino a fermarsi, a velocita' che cala
    linearmente, esattamente nella posa (angolo 0) dopo SPIN_SECONDS."""
    u = ramp(t, appear_at(n), appear_at(n) + SPIN_SECONDS)
    return -2.0 * math.pi * SPIN_TURNS * (1.0 - u) ** 2


def label_fade_keys(n):
    """Le scritte dell'n-esimo poliedro: compaiono in ordine, spariscono
    insieme."""
    t0 = T_LABELS + n * LABELS_GAP
    return [(frame_of(t0), 0.0), (frame_of(t0 + LABEL_FADE), 1.0),
            (frame_of(T_OUT), 1.0), (frame_of(T_OUT + LABEL_FADE), 0.0)]


# =============================================================================
# GEOMETRIA
# =============================================================================

def tetrahedron_chain():
    """Tre tetraedri regolari di spigolo 1 in catena: il secondo incollato a
    una faccia del primo, il terzo a una faccia del secondo, senza tornare
    indietro. Ogni nuovo vertice e' il riflesso, attraverso la faccia in
    comune, del vertice opposto. Restituisce (vertici numpy, facce); le facce
    interne (bcd, cde) non ci sono."""
    def reflect(p, a, b, c):
        n = np.cross(b - a, c - a)
        n = n / np.linalg.norm(n)
        return p - 2.0 * np.dot(p - a, n) * n
    a = np.array([0.0, 0.0, 0.0])
    b = np.array([1.0, 0.0, 0.0])
    c = np.array([0.5, math.sqrt(3) / 2, 0.0])
    d = np.array([0.5, math.sqrt(3) / 6, math.sqrt(2.0 / 3.0)])
    e = reflect(a, b, c, d)
    f = reflect(b, c, d, e)
    V = np.array([a, b, c, d, e, f])
    faces = [(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 4), (1, 3, 4), (2, 3, 5), (2, 4, 5), (3, 4, 5)]
    return V, orient_outward(V, faces)


def orient_outward(V, faces):
    """Le facce con l'orientamento coerente e le normali verso l'esterno.

    Si propaga l'orientamento da faccia a faccia attraverso gli spigoli (due
    facce adiacenti percorrono lo spigolo in sensi opposti), poi si sceglie il
    verso col segno del volume: su un poliedro non convesso il confronto col
    baricentro non basta."""
    faces = [list(f) for f in faces]
    done, todo = {0}, [0]
    while todo:
        i = todo.pop()
        edges_i = {(faces[i][k], faces[i][(k + 1) % 3]) for k in range(3)}
        for j, g in enumerate(faces):
            if j in done:
                continue
            edges_j = {(g[k], g[(k + 1) % 3]) for k in range(3)}
            if not any(e in edges_j or (e[1], e[0]) in edges_j for e in edges_i):
                continue
            if any(e in edges_j for e in edges_i):       # stesso verso: va girata
                faces[j] = [g[0], g[2], g[1]]
            done.add(j)
            todo.append(j)
    volume = sum(np.dot(V[f[0]], np.cross(V[f[1]], V[f[2]])) for f in faces)
    if volume < 0:
        faces = [[f[0], f[2], f[1]] for f in faces]
    return faces


def load_polyhedron(source, euler_deg):
    """Il poliedro: dal file (vertici duplicati saldati) o costruito, centrato,
    nella sfera di raggio PIECE_RADIUS e ruotato nella posa. Restituisce
    (vertici numpy, facce)."""
    if source == "CHAIN":
        V, faces = tetrahedron_chain()
    else:
        md = geometry.read_obj(source)
        index, remap = {}, []
        for v in md.vertices:
            remap.append(index.setdefault(tuple(np.round(v, 5)), len(index)))
        V = np.asarray(list(index), dtype=float)
        faces = [[remap[i] for i in f] for f in md.faces]
    V = V - V.mean(axis=0)
    V = V * (PIECE_RADIUS / np.linalg.norm(V, axis=1).max())
    R = np.asarray(mathutils.Euler([math.radians(a) for a in euler_deg], 'XYZ').to_matrix())
    return V @ R.T, faces


def vertex_degrees(n, faces):
    """Quanti triangoli concorrono in ogni vertice."""
    deg = [0] * n
    for f in faces:
        for i in f:
            deg[i] += 1
    return deg


def label_text(key, degree, count, n_types):
    if n_types == 1:
        return "un solo tipo\ndi vertice"
    letter = VERTEX_TYPES[(key, degree)][0]
    return f"{count} vertici\ndi tipo {letter}"


# =============================================================================
# COSTRUZIONE
# =============================================================================

KIT = m_scene.Kit(PREFIX, COLLECTION_NAME, ASSETS_DIR)
RIG = m_scene.CameraRig('PERSP', CAMERA_DISTANCE, SENSOR_W, RESOLUTION)


def camera_back():
    e = math.radians(CAMERA_ELEVATION)
    return Vector((0.0, -math.cos(e), math.sin(e)))


def overlay_material(suffix):
    """Bianco emissivo che sfuma nel trasparente col nodo 'Fade' (0 =
    invisibile, 1 = pieno)."""
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


def build_polyhedra():
    """Gli oggetti dei poliedri, animati (comparsa e rotazione), senza
    sferette. Restituisce [(chiave, oggetto, vertici, gradi)], vertici nel
    riferimento dell'oggetto."""
    face_mat = m_scene.wire_material(KIT, "faces", m_scene.linear_rgba(FACE_SRGB),
                                     roughness=FACE_ROUGHNESS)
    frames = list(range(FRAME_START, FRAME_END + 1))
    out = []
    for n, (key, source, euler, x) in enumerate(POLYHEDRA):
        V, faces = load_polyhedron(source, euler)
        mesh = bpy.data.meshes.new(KIT.name(key))
        mesh.from_pydata([tuple(v) for v in V], [], faces)
        mesh.materials.append(face_mat)
        mesh.update()
        obj = KIT.new_object(key, mesh)
        obj.location = (x, 0.0, 0.0)
        obj.visible_shadow = False
        t0 = appear_at(n)
        bl_anim.key_value(obj, "scale", [(frame_of(t0), (0.0,) * 3),
                                         (frame_of(t0 + GROW_SECONDS), (1.0,) * 3)])
        obj.rotation_mode = 'XYZ'
        bl_anim.key_value(obj, "rotation_euler",
                          [(f, (0.0, 0.0, spin_angle(n, time_of(f)))) for f in frames
                           if time_of(f) <= t0 + SPIN_SECONDS + 1.0 / FPS],
                          interpolation='LINEAR')
        out.append((key, obj, V, vertex_degrees(len(V), faces)))
    return out


def visible_vertices(scene, cam, polyhedra):
    """{(chiave, indice): visibile}, a poliedri fermi. Il raggio dalla camera
    si ferma poco prima del vertice: se incontra una faccia, il vertice e'
    coperto."""
    from bpy_extras.object_utils import world_to_camera_view as w2c
    dg = bpy.context.evaluated_depsgraph_get()
    eye = cam.matrix_world.translation
    seen = {}
    for key, obj, V, _ in polyhedra:
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


def build_spheres(polyhedra):
    """Le sferette sui vertici, figlie del poliedro: compaiono e girano con
    lui. Una mesh per tipo, lo stesso guscio col materiale del tipo."""
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
    for key, obj, V, deg in polyhedra:
        for i, v in enumerate(V):
            s = KIT.new_object(f"{key}_v{i:02d}", shells[(key, deg[i])], parent=obj)
            s.location = tuple(v)
            s.visible_shadow = False


def plane_size():
    """(larghezza, altezza) dell'inquadratura sul piano delle scritte."""
    w = LABEL_DEPTH * SENSOR_W / CAMERA_LENS
    return w, w / ASPECT


def to_plane(cam, world_point):
    """Il punto del piano delle scritte (coordinate della camera) che copre
    `world_point` nell'immagine, e la profondita' del punto."""
    c = cam.matrix_world.inverted() @ Vector(world_point)
    return Vector((c.x, c.y)) * (LABEL_DEPTH / -c.z), -c.z


def build_label(cam, name, text, frac, row, mat):
    """La scritta, centrata in `frac` (frazioni dell'immagine). Restituisce il
    punto del piano da cui parte la linea: sotto la scritta se sta in alto,
    sopra se sta in basso."""
    w, h = plane_size()
    curve = bpy.data.curves.new(KIT.name(name), 'FONT')
    curve.body = text
    curve.align_x, curve.align_y = 'CENTER', 'CENTER'
    curve.size = LABEL_HEIGHT * h / 0.72         # size e' l'altezza del corpo; le maiuscole ne sono circa 0.72
    curve.materials.append(mat)
    obj = KIT.new_object(name, curve, parent=cam)
    x, y = (frac[0] - 0.5) * w, (frac[1] - 0.5) * h
    obj.location = (x, y, -LABEL_DEPTH)
    obj.visible_shadow = False
    bpy.context.view_layer.update()
    half = obj.dimensions.y / 2                  # mezza altezza del blocco di testo
    side = -1.0 if row == "top" else 1.0
    return Vector((x, y + side * (half + LABEL_GAP * h)))


def build_lines(cam, name, start, ends, mat):
    """Le linee da `start` a ognuno degli `ends` (punti del piano), come
    rettangoli sottili in un solo oggetto figlio della camera."""
    _, h = plane_size()
    half = LINE_WIDTH * h / 2
    verts, faces = [], []
    for end in ends:
        d = end - start
        if d.length < 1e-9:
            continue
        nrm = Vector((-d.y, d.x)).normalized() * half
        k = len(verts)
        verts += [(*(start + nrm), 0.0), (*(start - nrm), 0.0),
                  (*(end - nrm), 0.0), (*(end + nrm), 0.0)]
        faces.append((k, k + 1, k + 2, k + 3))
    mesh = bpy.data.meshes.new(KIT.name(name))
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(mat)
    obj = KIT.new_object(name, mesh, parent=cam)
    obj.location = (0.0, 0.0, -LABEL_DEPTH)
    obj.visible_shadow = False
    return obj


def build_labels(scene, cam, polyhedra, seen):
    """Le scritte e le linee, per poliedro, con la loro dissolvenza.
    Restituisce le righe del resoconto."""
    from bpy_extras.object_utils import world_to_camera_view as w2c
    report = []
    for n, (key, obj, V, deg) in enumerate(polyhedra):
        mat = overlay_material(f"overlay_{key}")
        bl_anim.key_value(mat.node_tree, 'nodes["Fade"].inputs[0].default_value',
                          label_fade_keys(n))
        center_x = w2c(scene, cam, obj.matrix_world.translation).x
        degrees = sorted(set(deg))
        for degree in degrees:
            idx = [i for i in range(len(V)) if deg[i] == degree]
            dx, row = LABEL_LAYOUT[(key, degree)]
            text = label_text(key, degree, len(idx), len(degrees))
            start = build_label(cam, f"label_{key}_{degree}", text,
                                (center_x + dx, LABEL_ROW_Y[row]), row, mat)
            ends = []
            for i in idx:
                if not seen[(key, i)]:
                    continue
                p, depth = to_plane(cam, obj.matrix_world @ Vector(V[i]))
                r = VERTEX_RADIUS * LABEL_DEPTH / depth   # la linea si ferma sul bordo della sferetta
                d = p - start
                ends.append(start + d * max(0.0, (d.length - r) / d.length))
            if LINES == 'NEAREST' and ends:
                ends = [min(ends, key=lambda e: (e - start).length)]
            elif LINES not in ('ALL', 'NEAREST'):
                raise ValueError(f"LINES dev'essere 'ALL' o 'NEAREST', non {LINES!r}")
            build_lines(cam, f"lines_{key}_{degree}", start, ends, mat)
            visible = sum(1 for i in idx if seen[(key, i)])
            report.append(f"{key}, {degree} triangoli ({text.replace(chr(10), ' ')}): "
                          f"{visible} visibili su {len(idx)}, linee {len(ends)}")
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

    back = camera_back()
    rot = back.to_track_quat('Z', 'Y')
    light = rot.to_matrix() @ Vector(LIGHT_IN_CAMERA)
    m_scene.setup_sky_world(KIT, math.radians(SKY_SUN_ELEVATION),
                            m_scene.sky_rotation(-light), SKY_STRENGTH)
    cam = RIG.build(KIT, back * CAMERA_DISTANCE, clip_end=CAMERA_DISTANCE + 40.0)
    cam.data.lens = CAMERA_LENS
    cam.rotation_mode = 'QUATERNION'
    cam.rotation_quaternion = rot
    m_scene.build_background(KIT, RIG, cam, CAMERA_LENS, CAMERA_DISTANCE + 20.0,
                             BACKGROUND_CORNERS_SRGB, BACKGROUND_BLEED)

    polyhedra = build_polyhedra()
    # visibilita' e linee a poliedri fermi, prima che ci siano sferette e scritte
    scene.frame_set(frame_of(T_LABELS))
    seen = visible_vertices(scene, cam, polyhedra)
    build_spheres(polyhedra)
    report = build_labels(scene, cam, polyhedra, seen)
    scene.frame_set(FRAME_START)

    print(f"[biform] frame {FRAME_START}-{FRAME_END} a {FPS} fps ({T_END:.1f} s): fermi a "
          f"{T_STILL:.1f} s, scritte da {T_LABELS:.1f} s, via a {T_OUT:.1f} s")
    for line in report:
        print(f"[biform] {line}")
    return polyhedra


POLYHEDRA_OBJECTS = build()
