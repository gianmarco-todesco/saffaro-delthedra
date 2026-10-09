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

import os, sys
import math
import importlib


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
import bl_utils, bl_anim, m_scene, deltahedra
for _mod in (bl_utils, bl_anim, m_scene, deltahedra):
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
# LA PLATEA E LA CAMERA (libs/deltahedra.py)
# =============================================================================

VIEW = deltahedra.View(CAMERA_ELEVATION, CAMERA_LENS, SENSOR_W, ASPECT)


def load_models():
    return deltahedra.load_models(MODELS_DIR, sum(ROWS))


def arrange(models):
    return deltahedra.arrange(models, ROWS, GAP, ROW_GAP, CLEARANCE)


def camera_back():
    return Vector(VIEW.back)


def sphere_cloud(models):
    return deltahedra.sphere_cloud([m.location for m in models], [m.radius for m in models])


def frame_all(models):
    target, distance = deltahedra.frame_all(VIEW, [m.location for m in models],
                                            [m.radius for m in models], FRAME_FILL)
    return Vector(target), distance


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
    m_scene.build_floor(KIT, FLOOR_SRGB, FLOOR_ROUGHNESS, FLOOR_SPECULAR, FLOOR_SIZE,
                        y=sum(m.location[1] for m in models) / len(models))
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
        obj.location = tuple(m.location)
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

    x, y = VIEW.project(sphere_cloud(models), target, distance)
    print(f"[cundy] {len(models)} deltaedri, frame {FRAME_START}-{frame_end} a {FPS} fps "
          f"({t_end:.1f} s); l'ultimo compare a {t_last:.1f} s")
    for k, row in enumerate(rows):
        print(f"[cundy] fila {k + 1}: {len(row)} pezzi, raggi {min(m.radius for m in row):.2f}-"
              f"{max(m.radius for m in row):.2f}, a y = {row[0].location[1]:.2f}")
    print(f"[cundy] camera a {distance:.2f}; la platea occupa x {x.min():.3f}-{x.max():.3f}, "
          f"y {y.min():.3f}-{y.max():.3f} dell'immagine")
    print(f"[cundy] colori fuori gamut (tagliati): {clipped if clipped else 'nessuno'}")
    return order


ORDER = build()
