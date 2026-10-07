"""
cundy_deltahedra.py -- i deltaedri di Cundy e Olshevsky: tutti i 25 modelli di
3dmodels/cundy/D2-Deltaedri di Cundy, in una platea.

--------------------------------------------------------------------------
LA SCENA
--------------------------------------------------------------------------
* I modelli hanno tutti spigolo 1 e si tengono nelle loro grandezze vere
  (circonraggio da 1.0 a 2.5). Ordinati per grandezza, stanno in file
  (ROWS: 3, 4, 5, 6, 7 pezzi): i piu' piccoli davanti, vicini alla camera, i
  piu' grandi in fondo. Le file in fondo hanno piu' pezzi perche' la
  prospettiva le restringe; numeri diversi di pezzi in file vicine le
  sfalsano da soli, cosi' quelli dietro si vedono fra quelli davanti.
* Ogni poliedro ha un colore pastello: stessa luminosita' e stessa
  saturazione in OKLCH (PASTEL_L, PASTEL_C), tinte diverse. Le tinte seguono
  l'angolo aureo nell'ordine di comparsa, quindi due poliedri che compaiono
  uno dopo l'altro (e che stanno vicini) non hanno mai tinte simili.
* Compaiono uno dopo l'altro (scala da 0 a 1, ease in/out), dal piu' piccolo
  davanti al piu' grande in fondo, e girano sempre su se stessi attorno
  all'asse verticale, ognuno con la sua fase.
* La camera inquadra tutto con un margine (FRAME_FILL), vista dall'alto di
  CAMERA_ELEVATION gradi.
* I pezzi stanno sopra un pavimento, ognuno appena sollevato (CLEARANCE)
  perche' girando non lo tocchi, e proiettano ombre dai bordi morbidi: il
  sole del cielo ha un disco grande (SUN_SIZE_DEG). Il pavimento occupa tutto
  lo sfondo.

Una sola scena, tutto in keyframe (nessun handler), script idempotente, nomi
col prefisso CD_.
"""

import bpy
import mathutils

import os, sys, glob
import math
import importlib

import numpy as np

# rendi possibile importare i moduli da src/libs
# (nota bene: __file__ non funziona dallo script editor di Blender,
#  quindi si ricava il path del file dal datablock di testo attivo)
def _find_libs_dir():
    txt = getattr(getattr(bpy.context, "space_data", None), "text", None)
    if txt is None:  # lo script non gira dal Text Editor: cerco il datablock per nome
        txt = bpy.data.texts.get("cundy_deltahedra.py")
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

PREFIX          = "CD"
COLLECTION_NAME = "cundy_deltahedra"

# saffaro/..., accanto al repository: src/libs -> src -> saffaro-delthedra -> saffaro
_SAFFARO   = os.path.dirname(os.path.dirname(os.path.dirname(_LIBS)))
ASSETS_DIR = os.path.join(_SAFFARO, "assets")
MODELS_DIR = os.path.join(_SAFFARO, "3dmodels", "cundy", "D2-Deltaedri di Cundy")

FPS         = 24
RESOLUTION  = (1920, 1080)
FRAME_START = 1

# --- la disposizione ---
ROWS     = [3, 4, 5, 6, 7]       # pezzi per fila, dalla prima (davanti) all'ultima
GAP      = 0.8                   # fra due pezzi della stessa fila, oltre alle loro sfere
ROW_GAP  = 0.6                   # fra una fila e la successiva, idem
CLEARANCE = 0.3                  # fra il pavimento e la sfera che contiene il pezzo

# --- il pavimento e le ombre ---
# Con la camera a CAMERA_ELEVATION gradi e questo obiettivo l'orizzonte cade
# sopra il bordo alto dell'immagine: il pavimento e' tutto lo sfondo, e il
# fondo sfumato delle altre scene qui non c'e' (lo coprirebbe, stando piu'
# vicino del bordo del pavimento). Nel render esce blu ardesia, circa
# (62, 68, 85), nei toni del fondo delle altre scene.
FLOOR_SRGB      = (30, 38, 56)
FLOOR_ROUGHNESS = 0.85
# Quanto riflette il cielo. Il pavimento lo si guarda di sbieco, e a quegli
# angoli il riflesso (bianco) vince sul colore: con il valore di default (0.5)
# il pavimento esce grigio qualunque sia il suo colore.
FLOOR_SPECULAR  = 0.05
FLOOR_SIZE      = 400.0          # lato del quadrato: abbastanza da non vederne il bordo
# Le ombre sono quelle del sole del cielo: il bordo e' tanto piu' morbido
# quanto piu' grande e' il disco del sole (il sole vero e' 0.545 gradi).
SUN_SIZE_DEG    = 8.0

# --- i colori: pastello, stessa luminosita' e saturazione in OKLCH ---
# 0.82 e 0.085: il colore piu' saturo che sta nel gamut sRGB per tutte le
# tinte a quella luminosita' (a 0.09 i blu fra 261 e 274 gradi escono)
PASTEL_L   = 0.82
PASTEL_C   = 0.085
HUE_START  = 20.0                # gradi, la tinta del primo
HUE_STEP   = 137.508             # l'angolo aureo
ROUGHNESS  = 0.5

# --- la scaletta, in secondi ---
APPEAR_GAP   = 0.3               # fra un poliedro e il successivo
GROW_SECONDS = 0.8               # scala da 0 a 1 (ease in/out)
HOLD_SECONDS = 6.0               # dopo l'ultimo
SPIN_SECONDS_PER_TURN = 10.0     # ognuno su se stesso

# --- la camera ---
CAMERA_ELEVATION = 22.0          # gradi sopra l'orizzonte
CAMERA_LENS      = 40.0          # mm, sensore da 36
FRAME_FILL       = (0.90, 0.80)  # quanta larghezza e altezza dell'immagine occupa la platea

# --- la luce ---
LIGHT_IN_CAMERA   = (0.866, -0.5, 0.0)
# il sole piu' alto che nelle altre scene: a 15 gradi le ombre sarebbero
# lunghe quasi quattro volte l'altezza dei pezzi, e finirebbero sugli altri
SKY_SUN_ELEVATION = 30.0
SKY_STRENGTH      = 0.1

SENSOR_W = 36.0
ASPECT   = RESOLUTION[0] / RESOLUTION[1]
SENSOR_H = SENSOR_W / ASPECT


# =============================================================================
# I MODELLI E LA DISPOSIZIONE
# =============================================================================

class Model:
    """Un deltaedro: il file, la mesh (vertici saldati, centrata), il
    circonraggio, e dove sta."""

    def __init__(self, path):
        self.path = path
        self.name = os.path.splitext(os.path.basename(path))[0]
        md = geometry.read_obj(path)
        index, remap = {}, []
        for v in md.vertices:
            remap.append(index.setdefault(tuple(np.round(v, 5)), len(index)))
        V = np.asarray(list(index), dtype=float)
        self.vertices = V - V.mean(axis=0)
        self.faces = [[remap[i] for i in f] for f in md.faces]
        self.radius = float(np.linalg.norm(self.vertices, axis=1).max())
        self.location = Vector((0.0, 0.0, 0.0))


def load_models():
    paths = sorted(glob.glob(os.path.join(MODELS_DIR, "*.obj")))
    if len(paths) != sum(ROWS):
        raise ValueError(f"{len(paths)} modelli in {MODELS_DIR}, ma ROWS ne prevede {sum(ROWS)}")
    return [Model(p) for p in paths]


def arrange(models):
    """Le file: i modelli ordinati per grandezza (a pari grandezza, per nome),
    i primi davanti. Restituisce l'ordine di comparsa e le file.

    Dentro una fila il piu' grande sta al centro e gli altri si alternano a
    destra e a sinistra, a scalare; due vicini stanno alla distanza che serve
    a loro due (somma dei raggi piu' GAP), non a quella del pezzo piu' grande
    della fila, che allargherebbe tutto per un pezzo solo. La distanza fra due
    file e' la somma dei loro raggi massimi piu' ROW_GAP: non si toccano mai,
    nemmeno girando.

    L'ordine di comparsa va fila per fila, da sinistra a destra."""
    by_size = sorted(models, key=lambda m: (round(m.radius, 3), m.name))
    rows, k = [], 0
    for n in ROWS:
        rows.append(by_size[k:k + n])
        k += n
    y, prev = 0.0, None
    for k, row in enumerate(rows):
        r = max(m.radius for m in row)
        if prev is not None:
            y += prev + r + ROW_GAP
        prev = r
        # il piu' grande al centro, poi alternati: ..., 4, 2, 0, 1, 3, ...
        big_first = sorted(row, key=lambda m: (-m.radius, m.name))
        line = []
        for j, m in enumerate(big_first):
            if j % 2:
                line.append(m)
            else:
                line.insert(0, m)
        x, xs = 0.0, []
        for j, m in enumerate(line):
            if j:
                x += line[j - 1].radius + m.radius + GAP
            xs.append(x)
        mid = (xs[0] - line[0].radius + xs[-1] + line[-1].radius) / 2.0
        for m, x in zip(line, xs):
            m.location = Vector((x - mid, y, m.radius + CLEARANCE))
        rows[k] = line
    order = [m for row in rows for m in row]
    return order, rows


# =============================================================================
# LA CAMERA
# =============================================================================

def camera_back():
    e = math.radians(CAMERA_ELEVATION)
    return Vector((0.0, -math.cos(e), math.sin(e)))


def project(points, target, distance):
    """Coordinate nell'immagine (0..1, y verso l'alto) per la camera che
    guarda `target` da `distance` lungo camera_back(): la geometria della
    camera di Blender (prospettica, sensor_fit AUTO)."""
    back = np.asarray(camera_back())
    f = -back
    r = np.array([1.0, 0.0, 0.0])
    u = np.cross(r, f)
    q = np.asarray(points) - (np.asarray(target) + back * distance)
    z = q @ f
    return 0.5 + (q @ r) / z * CAMERA_LENS / SENSOR_W, 0.5 + (q @ u) / z * CAMERA_LENS / SENSOR_H


def _sphere_cloud(models):
    n = 300
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    theta = math.pi * (1 + 5 ** 0.5) * i
    S = np.c_[np.cos(theta) * np.sin(phi), np.sin(theta) * np.sin(phi), np.cos(phi)]
    return np.concatenate([S * m.radius + np.asarray(m.location) for m in models])


def frame_all(models):
    """(punto inquadrato, distanza): la platea -- le sfere che contengono i
    pezzi, quindi qualunque sia la loro rotazione -- occupa FRAME_FILL
    dell'immagine nella dimensione che arriva prima al limite, ed e'
    centrata. Bisezione sulla distanza e correzione del punto, alternate."""
    P = _sphere_cloud(models)
    target = Vector(np.mean([np.asarray(m.location) for m in models], axis=0))
    for _ in range(10):
        lo, hi = 1.0, 500.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            x, y = project(P, target, mid)
            if (x.max() - x.min()) > FRAME_FILL[0] or (y.max() - y.min()) > FRAME_FILL[1]:
                lo = mid
            else:
                hi = mid
        d = hi
        x, y = project(P, target, d)
        w = d * SENSOR_W / CAMERA_LENS
        dx = ((x.min() + x.max()) / 2 - 0.5) * w
        dy = ((y.min() + y.max()) / 2 - 0.5) * w / ASPECT
        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            break
        R = camera_back().to_track_quat('Z', 'Y').to_matrix()
        target = target + R.col[0] * dx + R.col[1] * dy
    return target, d


# =============================================================================
# COSTRUZIONE
# =============================================================================

KIT = m_scene.Kit(PREFIX, COLLECTION_NAME, ASSETS_DIR)
RIG = m_scene.CameraRig('PERSP', 10.0, SENSOR_W, RESOLUTION)


def frame_of(t):
    return FRAME_START + int(round(t * FPS))


def build():
    KIT.clear_previous_run()
    models = load_models()
    order, rows = arrange(models)

    t_last = (len(order) - 1) * APPEAR_GAP + GROW_SECONDS
    t_end = t_last + HOLD_SECONDS
    frame_end = frame_of(t_end)

    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.render.resolution_x, scene.render.resolution_y = RESOLUTION
    scene.frame_start, scene.frame_end = FRAME_START, frame_end
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    KIT.new_collection(scene)

    back = camera_back()
    rot = back.to_track_quat('Z', 'Y')
    light = rot.to_matrix() @ Vector(LIGHT_IN_CAMERA)
    m_scene.setup_sky_world(KIT, math.radians(SKY_SUN_ELEVATION),
                            m_scene.sky_rotation(-light), SKY_STRENGTH,
                            sun_size=math.radians(SUN_SIZE_DEG))
    floor_mesh = bpy.data.meshes.new(KIT.name("floor"))
    h = FLOOR_SIZE / 2.0
    floor_mesh.from_pydata([(-h, -h, 0.0), (h, -h, 0.0), (h, h, 0.0), (-h, h, 0.0)], [], [(0, 1, 2, 3)])
    floor_mat = m_scene.wire_material(KIT, "floor", m_scene.linear_rgba(FLOOR_SRGB),
                                      roughness=FLOOR_ROUGHNESS)
    bsdf = next(n for n in floor_mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs["Specular IOR Level"].default_value = FLOOR_SPECULAR
    floor_mesh.materials.append(floor_mat)
    floor = KIT.new_object("floor", floor_mesh)
    floor.location = (0.0, sum(m.location.y for m in models) / len(models), 0.0)
    target, distance = frame_all(models)
    cam = RIG.build(KIT, target + back * distance, clip_end=distance + FLOOR_SIZE)
    cam.data.lens = CAMERA_LENS
    cam.rotation_mode = 'QUATERNION'
    cam.rotation_quaternion = rot

    spin = 2.0 * math.pi / (SPIN_SECONDS_PER_TURN * FPS)       # radianti a fotogramma
    clipped = []
    for n, m in enumerate(order):
        hue = (HUE_START + n * HUE_STEP) % 360.0
        color, out_of_gamut = m_scene.oklch_to_linear(PASTEL_L, PASTEL_C, hue)
        if out_of_gamut:
            clipped.append(m.name)
        mesh = bpy.data.meshes.new(KIT.name(m.name))
        mesh.from_pydata([tuple(v) for v in m.vertices], [], m.faces)
        mesh.materials.append(m_scene.wire_material(KIT, f"mat_{m.name}", color, roughness=ROUGHNESS))
        mesh.update()
        obj = KIT.new_object(m.name, mesh)
        obj.location = m.location
        t0 = n * APPEAR_GAP
        bl_anim.key_value(obj, "scale", [(frame_of(t0), (0.0,) * 3),
                                         (frame_of(t0 + GROW_SECONDS), (1.0,) * 3)])
        # sempre in rotazione, ognuno con la sua fase: due chiavi e una retta
        phase = 2.0 * math.pi * ((n * 0.618034) % 1.0)
        obj.rotation_mode = 'XYZ'
        bl_anim.key_value(obj, "rotation_euler",
                          [(FRAME_START, (0.0, 0.0, phase)),
                           (frame_end, (0.0, 0.0, phase + spin * (frame_end - FRAME_START)))],
                          interpolation='LINEAR')
    scene.frame_set(FRAME_START)

    x, y = project(_sphere_cloud(models), target, distance)
    print(f"[cundy] {len(models)} deltaedri, frame {FRAME_START}-{frame_end} a {FPS} fps "
          f"({t_end:.1f} s); l'ultimo compare a {t_last:.1f} s")
    for k, row in enumerate(rows):
        print(f"[cundy] fila {k + 1}: {len(row)} pezzi, raggi {min(m.radius for m in row):.2f}-"
              f"{max(m.radius for m in row):.2f}, a y = {row[0].location.y:.2f}")
    print(f"[cundy] camera a {distance:.2f}; la platea occupa x {x.min():.3f}-{x.max():.3f}, "
          f"y {y.min():.3f}-{y.max():.3f} dell'immagine")
    print(f"[cundy] colori fuori gamut (tagliati): {clipped if clipped else 'nessuno'}")
    return order


ORDER = build()
