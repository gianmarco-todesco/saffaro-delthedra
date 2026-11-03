"""
v3/W.py -- estemporaneo: il deltaedro W di Saffaro appoggiato sul pavimento
ardesia, che gira lentamente su se stesso.

--------------------------------------------------------------------------
LA SCENA
--------------------------------------------------------------------------
* Il modello e' modelli-3d/saffaro-deltahedra/W.stl (360 facce), portato a
  spigolo medio 1 come gli altri modelli delle scene. Sta appoggiato: il suo
  punto piu' basso tocca il pavimento, e siccome gira attorno alla verticale
  continua a toccarlo.
* Il look e' quello di v2/scene-7: pavimento ardesia, cielo col sole a
  SKY_SUN_ELEVATION gradi e il disco largo (ombre morbide), la luce che
  viene da sinistra come nel racconto, il fondo sfumato lontano dietro
  l'orizzonte, un colore pastello (story.pastel).
* La camera e' ferma, alta CAMERA_ELEVATION gradi, e inquadra la sfera che
  contiene W (FRAME_FILL), qualunque sia la sua rotazione.
* Dura un giro (SECONDS_PER_TURN): il primo e l'ultimo fotogramma coincidono,
  e il video si puo' ripetere in loop.
* Il motore e' Cycles, a 256 campioni (m_scene.use_cycles).

Script idempotente, nomi col prefisso WV3_.
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
        txt = bpy.data.texts.get("W.py")
    if txt is None or not txt.filepath:
        raise RuntimeError(
            "non riesco a ricavare il path dello script: il testo non e' salvato "
            "su disco (Text > Save As) oppure e' un blocco 'interno'"
        )
    # attenzione: se il file e' stato aperto con l'opzione 'Relative Path' spuntata,
    # filepath e' del tipo '//../...' (relativo al .blend) e os.path lo interpreta
    # come percorso UNC. bpy.path.abspath lo risolve; sugli assoluti non fa nulla.
    path = os.path.abspath(bpy.path.abspath(txt.filepath))
    # script in src/scripts/v3, librerie in src/libs
    libs = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(path))), "libs")
    if not os.path.isdir(libs):
        raise RuntimeError(f"cartella libs non trovata: {libs}  (filepath: {txt.filepath})")
    return libs


_LIBS = _find_libs_dir()
if _LIBS not in sys.path:
    sys.path.insert(0, _LIBS)

# questo serve nel caso che tu faccia modifiche ai moduli senza interrompere la sessione di Blender
import bl_anim, m_scene, story, deltahedra
for _mod in (bl_anim, m_scene, story, deltahedra):
    importlib.reload(_mod)

from mathutils import Vector


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

PREFIX          = "WV3"
COLLECTION_NAME = "W_v3"

# saffaro/..., accanto al repository: src/libs -> src -> saffaro-delthedra -> saffaro
_SAFFARO   = os.path.dirname(os.path.dirname(os.path.dirname(_LIBS)))
ASSETS_DIR = os.path.join(_SAFFARO, "assets")
MODEL_FILE = os.path.join(_SAFFARO, "modelli-3d", "saffaro-deltahedra", "W.stl")

FPS         = story.FPS
RESOLUTION  = story.RESOLUTION
FRAME_START = 1

SECONDS_PER_TURN = 20.0          # un giro: la durata della scena
HUE        = 20.0                # la tinta OKLCH del pastello (salmone)
ROUGHNESS  = 0.5
FLOOR_GAP  = 0.002               # fra il punto piu' basso e il pavimento: appoggiato

# --- pavimento, luce, fondo: come v2/scene-7 ---
FLOOR_SRGB      = (30, 38, 56)
FLOOR_ROUGHNESS = 0.85
FLOOR_SPECULAR  = 0.05
FLOOR_SIZE      = 800.0
SUN_SIZE_DEG    = 8.0
SKY_SUN_ELEVATION = 30.0
BACKGROUND_DEPTH  = 300.0        # il fondo sfumato, dietro l'orizzonte

# --- la camera ---
CAMERA_ELEVATION = 22.0          # gradi sopra l'orizzonte
CAMERA_LENS      = 50.0          # mm, sensore da 36
FRAME_FILL       = 0.75          # quanta altezza dell'immagine occupa la sfera di W


# =============================================================================
# COSTRUZIONE
# =============================================================================

KIT = m_scene.Kit(PREFIX, COLLECTION_NAME, ASSETS_DIR)
FRAME_END = FRAME_START + int(round(SECONDS_PER_TURN * FPS))


def load_model():
    """(vertici, facce) di W a spigolo medio 1, centrato nel baricentro dei
    vertici."""
    V, faces = deltahedra.load_stl(MODEL_FILE)
    edges = [np.linalg.norm(V[f[k]] - V[f[(k + 1) % 3]]) for f in faces for k in range(3)]
    return V / float(np.mean(edges)), faces


def build():
    KIT.clear_previous_run()
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.render.resolution_x, scene.render.resolution_y = RESOLUTION
    # l'ultimo fotogramma ha fatto un giro intero: e' il primo, quindi lo si
    # lascia fuori, e il loop non ha un fotogramma ripetuto
    scene.frame_start, scene.frame_end = FRAME_START, FRAME_END - 1
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    m_scene.use_cycles(scene)
    KIT.new_collection(scene)

    # --- W, appoggiato: il pavimento e' a z = 0 ---
    V, faces = load_model()
    mesh = bpy.data.meshes.new(KIT.name("W"))
    mesh.from_pydata([tuple(v) for v in V], [], faces)
    mesh.materials.append(m_scene.wire_material(KIT, "W", story.pastel(HUE), roughness=ROUGHNESS))
    mesh.update()
    obj = KIT.new_object("W", mesh)
    obj.location = (0.0, 0.0, -float(V[:, 2].min()) + FLOOR_GAP)
    obj.rotation_mode = 'XYZ'
    bl_anim.key_value(obj, "rotation_euler", [(FRAME_START, (0.0, 0.0, 0.0)),
                                              (FRAME_END, (0.0, 0.0, 2.0 * math.pi))],
                      interpolation='LINEAR')

    # --- pavimento, cielo ---
    m_scene.build_floor(KIT, FLOOR_SRGB, FLOOR_ROUGHNESS, FLOOR_SPECULAR, FLOOR_SIZE)
    m_scene.setup_sky_world(KIT, math.radians(SKY_SUN_ELEVATION),
                            m_scene.sky_rotation(-Vector(story.LIGHT_DIRECTION)), story.SKY_STRENGTH,
                            sun_size=math.radians(SUN_SIZE_DEG))

    # --- la camera: guarda il centro della sfera di W, che occupa FRAME_FILL ---
    rig = story.camera_rig()
    radius = float(np.linalg.norm(V, axis=1).max())
    centre = np.array([0.0, 0.0, obj.location.z])
    view = deltahedra.View(CAMERA_ELEVATION, CAMERA_LENS, rig.sensor_width, rig.aspect)
    target, distance = deltahedra.frame_all(view, [centre], [radius], (1.0, FRAME_FILL))
    cam = rig.build(KIT, Vector(target + view.back * distance), clip_end=BACKGROUND_DEPTH + 20.0)
    cam.data.lens = CAMERA_LENS
    cam.rotation_mode = 'QUATERNION'
    cam.rotation_quaternion = Vector(view.back).to_track_quat('Z', 'Y')
    m_scene.build_background(KIT, rig, cam, CAMERA_LENS, BACKGROUND_DEPTH,
                             story.BACKGROUND_CORNERS_SRGB, story.BACKGROUND_BLEED)

    scene.frame_set(FRAME_START)
    print(f"[W v3] frame {FRAME_START}-{FRAME_END - 1} a {FPS} fps (un giro in {SECONDS_PER_TURN:.0f} s); "
          f"{len(faces)} facce, raggio {radius:.2f} a spigolo medio 1; camera a {distance:.1f}")


build()
