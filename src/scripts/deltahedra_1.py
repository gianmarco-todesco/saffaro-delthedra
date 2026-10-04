"""
deltahedra_1.py -- M e l'icosaedro, poi gli otto deltaedri convessi in due
girotondi concentrici.

--------------------------------------------------------------------------
LA SCALETTA (secondi dall'inizio, a 24 fps)
--------------------------------------------------------------------------
   0          M a sinistra e l'icosaedro a destra girano lentamente, ognuno
              attorno al proprio asse verticale
  17.6        con un movimento rapido (ease in) si allontanano dal centro, M a
              sinistra e l'icosaedro a destra, ed escono dall'inquadratura
  18          al centro compare un tetraedro (scala da 0 a 1, ease in/out)
  21          torna l'icosaedro da destra, arriva l'ottaedro da sinistra, il
              tetraedro si sposta: i tre stanno ai vertici di un triangolo
              equilatero, che comincia a girare lentamente -- il primo girotondo
  32          arrivano gli altri cinque e formano un secondo girotondo, appena
              piu' largo, attorno al primo; gira in senso contrario
  42          fine

I girotondi stanno su un piano perpendicolare alla linea di vista, parallelo
allo schermo. Ogni pezzo intanto gira su se stesso, attorno al proprio asse
verticale.

--------------------------------------------------------------------------
LE SCELTE
--------------------------------------------------------------------------
* Ogni pezzo sta in una sfera di raggio 1 (anche M): hanno tutti la stessa
  grandezza apparente, qualunque sia la lunghezza dei loro spigoli. I modelli
  vengono da saffaro/modelli-3d/convex-deltahedra, con il loro orientamento.
* M e' orientata come l'icosaedro che le sta accanto: la sua anima e' lo
  stesso icosaedro, nella stessa posa (align_m()).
* I due girotondi sono distanti quanto basta perche' le sfere dei pezzi non si
  tocchino mai, nemmeno quando i due cerchi girano in senso contrario: la
  corona fra INNER_RADIUS e OUTER_RADIUS e' piu' larga di un diametro.
* L'ingombro verticale e' BAND_FRACTION (un terzo) dell'altezza dell'immagine
  per la coppia e il tetraedro, RING_BAND per i girotondi: un disco alto un
  terzo dell'immagine renderebbe i pezzi cinque volte piu' piccoli che nella
  coppia. La distanza della camera si calcola per ogni fase proiettando le
  sfere dei pezzi in tutte le posizioni dei giri (frame_layout()), e la camera
  passa dall'una all'altra durante gli arrivi. Lo script stampa l'ingombro che
  ottiene.
* I colori vanno in ordine d'arcobaleno col numero di facce; M ha la sua
  texture. Fondo, cielo e niente ombre portate come M_story.

Una sola scena, tutto in keyframe (nessun handler), script idempotente, nomi
col prefisso DH_.
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
        txt = bpy.data.texts.get("deltahedra_1.py")
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
import geometry, bl_utils, extended_face, bl_anim, m_scene
for _mod in (geometry, bl_utils, extended_face, bl_anim, m_scene):
    importlib.reload(_mod)

from mathutils import Vector


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

PREFIX          = "DH"
COLLECTION_NAME = "deltahedra_1"

# saffaro/..., accanto al repository: src/libs -> src -> saffaro-delthedra -> saffaro
_SAFFARO   = os.path.dirname(os.path.dirname(os.path.dirname(_LIBS)))
ASSETS_DIR = os.path.join(_SAFFARO, "assets")
MODELS_DIR = os.path.join(_SAFFARO, "modelli-3d", "convex-deltahedra")

# Gli otto deltaedri convessi, in ordine di numero di facce: i cinque del
# secondo girotondo stanno in quest'ordine. I colori (sRGB) vanno in ordine
# d'arcobaleno.
DELTAHEDRA = [
    ("tetra",  "01_Regular_Tetrahedron.obj",             (214,  66,  58)),   # 4 facce
    ("tribi",  "02_Triangular_Bipyramid.obj",            (232, 132,  46)),   # 6
    ("octa",   "03_Regular_Octahedron.obj",              (236, 196,  60)),   # 8
    ("pentbi", "04_Pentagonal_Bipyramid.obj",            (118, 182,  74)),   # 10
    ("snub",   "05_Snub_Disphenoid.obj",                 ( 52, 160, 140)),   # 12
    ("triaug", "06_Triaugmented_Triangular_Prism.obj",   ( 66, 108, 204)),   # 14
    ("gyro",   "07_Gyroelongated_Square_Bipyramid.obj",  (138,  86, 196)),   # 16
    ("ico",    "08_Regular_Icosahedron.obj",             (206,  80, 150)),   # 20
]
ROUGHNESS = 0.55

FPS        = 24
RESOLUTION = (1920, 1080)
FRAME_START = 1

# --- la scaletta, in secondi dall'inizio ---
TETRA_AT  = 18.0             # il tetraedro comincia a comparire
TRIO_AT   = 21.0             # icosaedro e ottaedro partono verso il tetraedro
OUTER_AT  = 32.0             # partono gli altri cinque
END_AT    = 42.0             # fine

EXIT_SECONDS       = 1.0     # quanto ci mettono M e l'icosaedro a uscire (ease in)
TETRA_DELAY        = 0.4     # di quanto l'uscita precede il tetraedro
TETRA_GROW_SECONDS = 1.0     # scala da 0 a 1 (ease in/out)
TRIO_IN_SECONDS    = 1.8     # quanto ci mettono icosaedro e ottaedro ad arrivare
OUTER_IN_SECONDS   = 2.5     # quanto ci mettono gli altri cinque

# --- i movimenti ---
SPIN_SECONDS_PER_TURN  = 12.0    # ogni pezzo su se stesso
INNER_SECONDS_PER_TURN = 20.0    # il girotondo dei tre, in senso antiorario
OUTER_SECONDS_PER_TURN = 30.0    # il girotondo dei cinque, in senso orario
RING_RAMP_SECONDS      = 1.5     # i girotondi partono con un raccordo
PIECE_RADIUS = 1.0               # ogni pezzo sta in una sfera di questo raggio
PAIR_X       = 1.6               # M e l'icosaedro stanno a x = -PAIR_X e +PAIR_X
INNER_RADIUS = 1.45              # il girotondo dei tre (lato del triangolo 2.51)
OUTER_RADIUS = 3.75              # quello dei cinque: la corona e' larga 2.3 > 2

# Gli angoli sui cerchi, nel piano dello schermo (gradi; 0 = a destra, 90 = in
# alto). Il primo girotondo: il tetraedro in alto, l'icosaedro in basso a
# destra (arriva da destra), l'ottaedro in basso a sinistra.
INNER_ANGLES = {"tetra": 90.0, "ico": -30.0, "octa": 210.0}
# Il secondo: i cinque in ordine di numero di facce, dall'alto, a 72 gradi.
OUTER_FIRST, OUTER_STEP = 90.0, -72.0

# --- la camera ---
# Gradi sopra l'orizzonte: quanto si vedono i pezzi un po' dall'alto. I
# girotondi stanno comunque nel piano perpendicolare alla linea di vista.
CAMERA_ELEVATION = 8.0
CAMERA_LENS      = 50.0          # mm, sensore da 36
BAND_FRACTION    = 1.0 / 3.0     # l'ingombro verticale della coppia, sull'altezza dell'immagine
RING_BAND        = 0.6           # ... e dei girotondi (1/3 per lasciare spazio alle scritte)
OUT_MARGIN       = 1.5           # di quanto si esce dall'inquadratura (oltre la sfera)

# --- fondo e luce: come M_story ---
BACKGROUND_CORNERS_SRGB = {
    "top_left":     (34, 46, 70),
    "top_right":    (16, 22, 38),
    "bottom_left":  (20, 28, 46),
    "bottom_right": (6, 8, 16),
}
BACKGROUND_BLEED  = 1.02
USE_STANDARD_VIEW = True
LIGHT_IN_CAMERA   = (0.866, -0.5, 0.0)   # verso cui va la luce, nel riferimento della camera
SKY_SUN_ELEVATION = 15.0
SKY_STRENGTH      = 0.1


# =============================================================================
# LA REGIA
# =============================================================================

T_TETRA0 = TETRA_AT
T_EXIT0  = T_TETRA0 - TETRA_DELAY
T_EXIT1  = T_EXIT0 + EXIT_SECONDS
T_TETRA1 = T_TETRA0 + TETRA_GROW_SECONDS
T_TRIO0  = TRIO_AT
T_TRIO1  = T_TRIO0 + TRIO_IN_SECONDS
T_OCT0   = OUTER_AT
T_OCT1   = T_OCT0 + OUTER_IN_SECONDS
T_END    = END_AT

_marks = [0.0, T_EXIT0, T_EXIT1, T_TETRA1, T_TRIO0, T_TRIO1, T_OCT0, T_OCT1, T_END]
if _marks != sorted(_marks) or T_TETRA0 < T_EXIT0:
    raise ValueError(f"scaletta fuori ordine: {_marks}")

FRAME_END = FRAME_START + int(round(T_END * FPS))
TRIO = ("tetra", "ico", "octa")
OUTER = tuple(key for key, _, _ in DELTAHEDRA if key not in TRIO)
OUTER_ORDER = {key: k for k, key in enumerate(OUTER)}


def time_of(frame):
    return (frame - FRAME_START) / FPS


def ramp(t, t0, t1):
    return min(1.0, max(0.0, (t - t0) / (t1 - t0)))


def ease_in(u):
    return u ** 3


def ease_out(u):
    return 1.0 - (1.0 - u) ** 3


def ease_inout(u):
    return u * u * (3.0 - 2.0 * u)


def _ring_angles(t_start, seconds_per_turn):
    """L'angolo di un girotondo (radianti) a ogni fotogramma: fermo fino a
    t_start, poi a velocita' costante dopo un raccordo di RING_RAMP_SECONDS;
    seconds_per_turn negativo = senso orario. Integrato numericamente,
    fotogramma per fotogramma."""
    omega = 2.0 * math.pi / seconds_per_turn            # radianti al secondo
    angles, a, steps = {}, 0.0, 16
    for f in range(FRAME_START, FRAME_END + 1):
        angles[f] = a
        t = time_of(f)
        a += sum(omega * ease_inout(ramp(t + (i + 0.5) / (steps * FPS), t_start,
                                         t_start + RING_RAMP_SECONDS))
                 for i in range(steps)) / (steps * FPS)
    return angles


INNER_RING = _ring_angles(T_TRIO1, INNER_SECONDS_PER_TURN)
OUTER_RING = _ring_angles(T_OCT0, -OUTER_SECONDS_PER_TURN)


def frame_at(t):
    return min(FRAME_END, FRAME_START + int(round(t * FPS)))


RIGHT = Vector((1.0, 0.0, 0.0))


def screen_up():
    """L'alto dello schermo nel mondo: e' l'asse Y della camera."""
    e = math.radians(CAMERA_ELEVATION)
    return Vector((0.0, math.sin(e), math.cos(e)))


def ring_point(radius, angle):
    """Il punto del cerchio di raggio `radius` all'angolo `angle`, nel piano
    dello schermo che passa per l'origine."""
    return RIGHT * (radius * math.cos(angle)) + screen_up() * (radius * math.sin(angle))


def inner_slot(key, alpha):
    return ring_point(INNER_RADIUS, math.radians(INNER_ANGLES[key]) + alpha)


def outer_slot(key, alpha):
    return ring_point(OUTER_RADIUS, math.radians(OUTER_FIRST + OUTER_STEP * OUTER_ORDER[key]) + alpha)


def piece_position(key, frame, x_out):
    """Dove sta il pezzo `key` ('M' o una chiave di DELTAHEDRA) al fotogramma.
    `x_out` e' la x a cui un pezzo e' fuori dall'inquadratura."""
    t = time_of(frame)
    out = ease_in(ramp(t, T_EXIT0, T_EXIT1))
    if key == "M":
        return RIGHT * (-PAIR_X - out * (x_out - PAIR_X))

    if key in TRIO:
        if key == "ico" and t < T_TRIO0:
            return RIGHT * (PAIR_X + out * (x_out - PAIR_X))
        start = {"ico": RIGHT * x_out, "octa": RIGHT * -x_out,
                 "tetra": Vector((0.0, 0.0, 0.0))}[key]
        u = ramp(t, T_TRIO0, T_TRIO1)
        u = ease_inout(u) if key == "tetra" else ease_out(u)
        return start.lerp(inner_slot(key, INNER_RING[frame]), u)

    # i cinque: dal lato in cui sta il loro posto, alla sua altezza, cosi'
    # non attraversano il primo girotondo
    end = outer_slot(key, OUTER_RING[frame_at(T_OCT1)])
    start = RIGHT * math.copysign(x_out, end.x if abs(end.x) > 1e-6 else 1.0) \
        + screen_up() * end.dot(screen_up())
    return start.lerp(outer_slot(key, OUTER_RING[frame]), ease_out(ramp(t, T_OCT0, T_OCT1)))


def tetra_scale(frame):
    t = time_of(frame)
    return ease_inout(ramp(t, T_TETRA0, T_TETRA1))


# =============================================================================
# LA CAMERA: PROIEZIONE E INQUADRATURA
# =============================================================================

def camera_back():
    """Il versore dal punto inquadrato verso la camera: davanti (-Y), alzato
    di CAMERA_ELEVATION."""
    e = math.radians(CAMERA_ELEVATION)
    return Vector((0.0, -math.cos(e), math.sin(e)))


ASPECT = RESOLUTION[0] / RESOLUTION[1]
SENSOR_W = 36.0                       # sensor_fit AUTO: il lato lungo e' 36 mm
SENSOR_H = SENSOR_W / ASPECT


def project(points, target, distance):
    """Le coordinate nell'immagine (0..1, y verso l'alto) dei punti, per la
    camera che guarda `target` da `distance` lungo camera_back(): la stessa
    geometria della camera di Blender (prospettica, sensor_fit AUTO)."""
    back = np.asarray(camera_back())
    f = -back
    r = np.array([1.0, 0.0, 0.0])
    u = np.cross(r, f)
    eye = np.asarray(target) + back * distance
    q = np.asarray(points) - eye
    z = q @ f
    x = 0.5 + (q @ r) / z * CAMERA_LENS / SENSOR_W
    y = 0.5 + (q @ u) / z * CAMERA_LENS / SENSOR_H
    return x, y


_SPHERE = None


def _sphere_points():
    """Punti sulla sfera unitaria: per proiettare una sfera basta il suo
    contorno, e una nuvola fitta lo contiene."""
    global _SPHERE
    if _SPHERE is None:
        n = 600
        i = np.arange(n) + 0.5
        phi = np.arccos(1 - 2 * i / n)
        theta = math.pi * (1 + 5 ** 0.5) * i
        _SPHERE = np.c_[np.cos(theta) * np.sin(phi), np.sin(theta) * np.sin(phi), np.cos(phi)]
    return _SPHERE


def extent(layouts, target, distance):
    """(y basso, y alto, x sinistra, x destra) nell'immagine dell'unione delle
    sfere dei pezzi, sul caso peggiore fra tutte le disposizioni date."""
    lo_y, hi_y, lo_x, hi_x = 1.0, 0.0, 1.0, 0.0
    S = _sphere_points() * PIECE_RADIUS
    for centers in layouts:
        P = np.concatenate([S + np.asarray(c) for c in centers])
        x, y = project(P, target, distance)
        lo_y, hi_y = min(lo_y, y.min()), max(hi_y, y.max())
        lo_x, hi_x = min(lo_x, x.min()), max(hi_x, x.max())
    return lo_y, hi_y, lo_x, hi_x


def frame_layout(layouts, band):
    """(distanza, altezza del punto inquadrato) per cui l'ingombro verticale
    dei pezzi -- il caso peggiore fra le disposizioni -- e' `band`
    dell'altezza dell'immagine, e centrato. Bisezione sulla distanza e
    correzione dell'altezza, alternate fino a convergenza."""
    z = 0.0
    for _ in range(8):
        lo, hi = 2.0, 200.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            y0, y1, _, _ = extent(layouts, (0.0, 0.0, z), mid)
            if y1 - y0 > band:
                lo = mid
            else:
                hi = mid
        d = hi
        y0, y1, _, _ = extent(layouts, (0.0, 0.0, z), d)
        # sposta il punto inquadrato perche' la fascia sia centrata: uno
        # scostamento dy nell'immagine vale circa dy * altezza dell'inquadratura
        frame_h = d * SENSOR_H / CAMERA_LENS
        dz = ((y0 + y1) / 2 - 0.5) * frame_h / math.cos(math.radians(CAMERA_ELEVATION))
        if abs(dz) < 1e-6:
            break
        z += dz
    return d, z


def camera_plan(samples=12):
    """Le tre inquadrature: coppia (e tetraedro), primo girotondo, due
    girotondi. Per i girotondi si provano le posizioni lungo un terzo di giro
    del primo e un quinto del secondo, in tutte le combinazioni, perche'
    girano in senso contrario."""
    pair = [[RIGHT * -PAIR_X, RIGHT * PAIR_X]]
    a3 = [2 * math.pi / 3 * i / samples for i in range(samples)]
    a5 = [2 * math.pi / 5 * i / samples for i in range(samples)]
    trio = [[inner_slot(k, a) for k in TRIO] for a in a3]
    both = [[inner_slot(k, a) for k in TRIO] + [outer_slot(k, b) for k in OUTER]
            for a in a3 for b in a5]
    return {"pair": (frame_layout(pair, BAND_FRACTION), pair),
            "trio": (frame_layout(trio, RING_BAND), trio),
            "octet": (frame_layout(both, RING_BAND), both)}


# =============================================================================
# COSTRUZIONE
# =============================================================================

KIT = m_scene.Kit(PREFIX, COLLECTION_NAME, ASSETS_DIR)
RIG = m_scene.CameraRig('PERSP', 10.0, SENSOR_W, RESOLUTION)


def normalized(md):
    """Il MeshData centrato nel baricentro dei vertici e scalato perche' stia
    nella sfera di raggio PIECE_RADIUS."""
    V = np.asarray(md.vertices, dtype=float)
    V = V - V.mean(axis=0)
    V = V * (PIECE_RADIUS / np.linalg.norm(V, axis=1).max())
    out = geometry.MeshData()
    out.vertices = [tuple(v) for v in V]
    out.faces = [list(f) for f in md.faces]
    return out


def align_m(ico_md):
    """La rotazione (numpy 3x3) che porta Polyhedron.ico -- l'icosaedro su cui
    e' costruita M -- sui vertici dell'icosaedro del file: M cosi' ha la stessa
    posa dell'icosaedro che le sta accanto. Si prova a mandare il vertice 0 sul
    vertice piu' alto e un suo vicino su un vicino di quello, e si tiene la
    rotazione che porta tutti i vertici su vertici."""
    P = np.asarray([v.tup() for v in geometry.Polyhedron.ico.vertices])
    Q = np.asarray(ico_md.vertices, dtype=float)
    Q = Q / np.linalg.norm(Q, axis=1)[:, None]
    top = int(np.argmax(Q[:, 2]))
    q_next = int(np.argsort(np.linalg.norm(Q - Q[top], axis=1))[1])
    for j in np.argsort(np.linalg.norm(P - P[0], axis=1))[1:6]:
        src = tuple(geometry.Vector(p) for p in ((0, 0, 0), P[0], P[j]))
        dst = tuple(geometry.Vector(q) for q in ((0, 0, 0), Q[top], Q[q_next]))
        R = geometry.matrix_from_triples(src, dst)[:3, :3]
        if np.linalg.det(R) < 0:
            continue
        mapped = P @ R.T
        # le coordinate del file hanno 6 decimali: gli spigoli dell'icosaedro
        # vi variano gia' di 1e-4, quindi la tolleranza e' 1e-3 (i vertici
        # distano fra loro piu' di 1)
        if max(np.linalg.norm(Q - m, axis=1).min() for m in mapped) < 1e-3:
            return R
    raise RuntimeError("l'icosaedro del file non e' un icosaedro regolare")


def build_pieces(face_img, uvs):
    """Gli oggetti: M e gli otto deltaedri. Restituisce {chiave: oggetto}."""
    pieces = {}
    models = {key: normalized(geometry.read_obj(os.path.join(MODELS_DIR, f)))
              for key, f, _ in DELTAHEDRA}
    for key, _, srgb in DELTAHEDRA:
        mesh = bpy.data.meshes.new(KIT.name(key))
        mesh.from_pydata(models[key].vertices, [], models[key].faces)
        mesh.materials.append(m_scene.wire_material(KIT, f"mat_{key}", m_scene.linear_rgba(srgb),
                                                    roughness=ROUGHNESS))
        mesh.update()
        pieces[key] = KIT.new_object(key, mesh)

    # M: nella posa dell'icosaedro del file, nella sfera di raggio 1
    R = align_m(models["ico"])
    md = extended_face.make_M()
    md.vertices = [tuple(R @ np.asarray(v)) for v in md.vertices]
    md = normalized(md)
    m_mat = m_scene.physical_face_material(KIT, face_img, 0.75)
    obj = KIT.new_object("M", m_scene.merged_mesh(KIT, md, m_mat, uvs))
    bl_utils.merge_by_distance(obj)
    pieces["M"] = obj
    for obj in pieces.values():
        obj.visible_shadow = False         # niente ombre portate, come in M_story
    return pieces


def animate(pieces, x_out, frames):
    spin = 2.0 * math.pi / (SPIN_SECONDS_PER_TURN * FPS)       # radianti a fotogramma
    for key, obj in pieces.items():
        bl_anim.key_value(obj, "location",
                          [(f, tuple(piece_position(key, f, x_out))) for f in frames],
                          interpolation='LINEAR')
        obj.rotation_mode = 'XYZ'
        # su se stesso, sempre: due chiavi e una retta
        bl_anim.key_value(obj, "rotation_euler",
                          [(FRAME_START, (0.0, 0.0, 0.0)),
                           (FRAME_END, (0.0, 0.0, spin * (FRAME_END - FRAME_START)))],
                          interpolation='LINEAR')
    bl_anim.key_value(pieces["tetra"], "scale",
                      [(f, (tetra_scale(f),) * 3) for f in frames
                       if T_TETRA0 - 1 / FPS <= time_of(f) <= T_TETRA1 + 1 / FPS],
                      interpolation='LINEAR')

    # visibili solo quando possono essere in scena: fuori dall'inquadratura
    # non si vedono comunque, ma la camera piu' tardi si allarga
    first = {key: FRAME_START for key in pieces}
    for key in ("octa",):
        first[key] = FRAME_START + int(T_TRIO0 * FPS) - 1
    for key, _, _ in DELTAHEDRA:
        if key not in TRIO:
            first[key] = FRAME_START + int(T_OCT0 * FPS) - 1
    for key, obj in pieces.items():
        changes = [(FRAME_START, first[key] == FRAME_START)]
        if first[key] != FRAME_START:
            changes.append((first[key], True))
        if key == "M":
            changes.append((FRAME_START + int(math.ceil(T_EXIT1 * FPS)) + 1, False))
        bl_anim.key_visibility(obj, changes)


def build_camera(plan, frames):
    """La camera: guarda sempre da camera_back(), e passa da un'inquadratura
    all'altra durante gli arrivi (ease in/out)."""
    (d1, z1), _ = plan["pair"]
    (d3, z3), _ = plan["trio"]
    (d8, z8), _ = plan["octet"]
    cam = RIG.build(KIT, Vector((0, 0, 0)), clip_end=d8 + 3 * OUTER_RADIUS + 40.0)
    cam.data.lens = CAMERA_LENS
    cam.rotation_mode = 'QUATERNION'
    cam.rotation_quaternion = camera_back().to_track_quat('Z', 'Y')
    keys = []
    for f in frames:
        t = time_of(f)
        u3 = ease_inout(ramp(t, T_TRIO0, T_TRIO1))
        u8 = ease_inout(ramp(t, T_OCT0, T_OCT1))
        d = d1 + u3 * (d3 - d1) + u8 * (d8 - d3)
        z = z1 + u3 * (z3 - z1) + u8 * (z8 - z3)
        keys.append((f, tuple(Vector((0, 0, z)) + camera_back() * d)))
    bl_anim.key_value(cam, "location", keys, interpolation='LINEAR')
    m_scene.build_background(KIT, RIG, cam, CAMERA_LENS, d8 + OUTER_RADIUS + 20.0,
                             BACKGROUND_CORNERS_SRGB, BACKGROUND_BLEED)
    return cam


def x_out_for(plan):
    """La x a cui un pezzo e' fuori dall'inquadratura anche quando la camera e'
    piu' larga (i due girotondi): mezza larghezza a quella distanza piu' la
    sfera."""
    (d8, _), _ = plan["octet"]
    return d8 * SENSOR_W / CAMERA_LENS / 2.0 + PIECE_RADIUS + OUT_MARGIN


def build():
    KIT.clear_previous_run()
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.render.resolution_x, scene.render.resolution_y = RESOLUTION
    scene.frame_start, scene.frame_end = FRAME_START, FRAME_END
    if USE_STANDARD_VIEW:
        scene.view_settings.view_transform = 'Standard'
        scene.view_settings.look = 'None'
    KIT.new_collection(scene)

    back = camera_back()
    light = back.to_track_quat('Z', 'Y').to_matrix() @ Vector(LIGHT_IN_CAMERA)
    m_scene.setup_sky_world(KIT, math.radians(SKY_SUN_ELEVATION),
                            m_scene.sky_rotation(-light), SKY_STRENGTH)

    face_img = KIT.load_image(m_scene.FACE_TEXTURE_FILE)
    uvs = m_scene.face_uvs(face_img, m_scene.FACE_TEXTURE_UV_PX, m_scene.FACE_TEXTURE_UV_INSET)
    pieces = build_pieces(face_img, uvs)

    frames = list(range(FRAME_START, FRAME_END + 1))
    plan = camera_plan()
    x_out = x_out_for(plan)
    animate(pieces, x_out, frames)
    build_camera(plan, frames)
    scene.frame_set(FRAME_START)

    print(f"[deltahedra_1] frame {FRAME_START}-{FRAME_END} a {FPS} fps ({T_END:.1f} s); "
          f"uscita {T_EXIT0:.1f} s, tetraedro {T_TETRA0:.1f}-{T_TETRA1:.1f} s, primo "
          f"girotondo {T_TRIO0:.1f}-{T_TRIO1:.1f} s, secondo {T_OCT0:.1f}-{T_OCT1:.1f} s")
    for name, ((d, z), lay) in plan.items():
        y0, y1, x0, x1 = extent(lay, (0.0, 0.0, z), d)
        print(f"[deltahedra_1] {name:5s}: camera a {d:.2f} dal punto (0, 0, {z:+.3f}); "
              f"ingombro verticale {y0:.3f}-{y1:.3f} ({y1 - y0:.1%} dell'altezza), "
              f"orizzontale {x0:.3f}-{x1:.3f}")
    print(f"[deltahedra_1] fuori campo a x = {x_out:.2f}")
    return pieces


PIECES = build()
