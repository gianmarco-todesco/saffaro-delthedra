"""
scene_5a.py -- M sul pavimento, e davanti cinque deltaedri di Saffaro piu'
piccoli.

--------------------------------------------------------------------------
LA SCALETTA (secondi)
--------------------------------------------------------------------------
 0 - 1    M compare (scala da 0 a 1) e gira lentamente su se stesso.
 2        davanti a M compaiono, uno dopo l'altro, cinque deltaedri di
          Saffaro (OTHERS), anche loro girando su se stessi.
 8        fine.

--------------------------------------------------------------------------
LE SCELTE
--------------------------------------------------------------------------
* Il mondo e' quello di cundy_deltahedra: pavimento ardesia, ombre morbide,
  la camera alta CAMERA_ELEVATION gradi, ferma, che inquadra tutto.
* M ha spigolo 1 (circonraggio 2.27) e la texture delle facce del quadro
  (m2face_texture.png, il materiale 'fisico' di m_scene). Gli altri, dai
  modelli di saffaro/modelli-3d/saffaro-deltahedra, hanno tutti lo stesso
  circonraggio, un terzo di quello di M, e colori pastello (stessa
  luminosita' e saturazione in OKLCH, tinte lontane fra loro e dall'azzurro
  di M).
* I cinque stanno su un arco davanti a M, centrato sul suo asse: tutti alla
  stessa distanza da lui, e a distanze uguali fra loro.
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
        txt = bpy.data.texts.get("scene_5a.py")
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
import bl_utils, bl_anim, m_scene, extended_face, deltahedra
for _mod in (bl_utils, bl_anim, m_scene, extended_face, deltahedra):
    importlib.reload(_mod)

from mathutils import Vector


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

PREFIX          = "S5A"
COLLECTION_NAME = "scene_5a"

# saffaro/..., accanto al repository: src/libs -> src -> saffaro-delthedra -> saffaro
_SAFFARO    = os.path.dirname(os.path.dirname(os.path.dirname(_LIBS)))
ASSETS_DIR  = os.path.join(_SAFFARO, "assets")
SAFFARO_DIR = os.path.join(_SAFFARO, "modelli-3d", "saffaro-deltahedra")

FPS         = 24
RESOLUTION  = (1920, 1080)
FRAME_START = 1
SENSOR_W    = 36.0
ASPECT      = RESOLUTION[0] / RESOLUTION[1]

# --- i cinque deltaedri, da sinistra a destra: (file, facce, tinta OKLCH) ---
# Facce diverse, da 16 a 96: a parita' di grandezza, triangoli sempre piu'
# piccoli. Le tinte stanno lontane dall'azzurro della texture di M (circa 220
# gradi) e fra loro, e due vicini non si somigliano.
OTHERS = [
    ("D.stl", 16,  20.0),        # salmone
    ("A.stl", 24, 150.0),        # verde menta
    ("F.stl", 48, 300.0),        # lilla
    ("N.stl", 72,  75.0),        # albicocca
    ("H.stl", 96, 345.0),        # rosa
]
SMALL_FRACTION = 1.0 / 3.0       # circonraggio dei cinque rispetto a quello di M

# --- la disposizione ---
CLEARANCE  = 0.3                 # fra il pavimento e la sfera che contiene il pezzo
ARC_GAP    = 1.6                 # fra la sfera di M e quelle dei cinque
ARC_STEP   = 25.0                # gradi fra due vicini sull'arco

# --- la scaletta, in secondi ---
M_GROW         = 1.0
OTHERS_AT      = 2.0
OTHERS_GAP     = 0.3
OTHERS_GROW    = 0.8
END            = 8.0
M_SECONDS_PER_TURN     = 24.0
OTHER_SECONDS_PER_TURN = 10.0

# --- i colori ---
M_ROUGHNESS = 0.75               # come in deltahedra_1
PASTEL_L   = 0.82                # come in cundy_deltahedra
PASTEL_C   = 0.085
ROUGHNESS  = 0.5

# --- pavimento, luce, camera: come cundy_deltahedra ---
FLOOR_SRGB      = (30, 38, 56)
FLOOR_ROUGHNESS = 0.85
FLOOR_SPECULAR  = 0.05
FLOOR_SIZE      = 400.0
SUN_SIZE_DEG    = 8.0
LIGHT_IN_CAMERA   = (0.866, -0.5, 0.0)
SKY_SUN_ELEVATION = 30.0
SKY_STRENGTH      = 0.1
CAMERA_ELEVATION = 22.0
CAMERA_LENS      = 40.0
FRAME_FILL       = (0.80, 0.72)


# =============================================================================
# LA REGIA
# =============================================================================

FRAME_END = FRAME_START + int(round(END * FPS))


def frame_of(t):
    return FRAME_START + int(round(t * FPS))


def spin_keys(seconds_per_turn, phase):
    """Su se stesso attorno alla verticale, sempre: due chiavi e una retta."""
    spin = 2.0 * math.pi / (seconds_per_turn * FPS)
    return [(FRAME_START, (0.0, 0.0, phase)),
            (FRAME_END, (0.0, 0.0, phase + spin * (FRAME_END - FRAME_START)))]


# =============================================================================
# COSTRUZIONE
# =============================================================================

KIT  = m_scene.Kit(PREFIX, COLLECTION_NAME, ASSETS_DIR)
RIG  = m_scene.CameraRig('PERSP', 10.0, SENSOR_W, RESOLUTION)
VIEW = deltahedra.View(CAMERA_ELEVATION, CAMERA_LENS, SENSOR_W, ASPECT)


def build_m():
    """M con spigolo 1 e la texture del quadro. Restituisce (oggetto,
    circonraggio)."""
    md = extended_face.make_M()
    V = np.asarray(md.vertices, dtype=float)
    f = md.faces[0]
    V = (V - V.mean(axis=0)) / float(np.linalg.norm(V[f[0]] - V[f[1]]))
    md.vertices = [tuple(v) for v in V]
    face_img = KIT.load_image(m_scene.FACE_TEXTURE_FILE)
    uvs = m_scene.face_uvs(face_img, m_scene.FACE_TEXTURE_UV_PX, m_scene.FACE_TEXTURE_UV_INSET)
    mat = m_scene.physical_face_material(KIT, face_img, M_ROUGHNESS)
    obj = KIT.new_object("M", m_scene.merged_mesh(KIT, md, mat, uvs))
    bl_utils.merge_by_distance(obj)
    return obj, float(np.linalg.norm(V, axis=1).max())


def build():
    KIT.clear_previous_run()
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.render.resolution_x, scene.render.resolution_y = RESOLUTION
    scene.frame_start, scene.frame_end = FRAME_START, FRAME_END
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    KIT.new_collection(scene)

    # --- M ---
    m_obj, m_radius = build_m()
    m_obj.location = (0.0, 0.0, m_radius + CLEARANCE)
    bl_anim.key_value(m_obj, "scale", [(FRAME_START, (0.0,) * 3), (frame_of(M_GROW), (1.0,) * 3)])
    m_obj.rotation_mode = 'XYZ'
    bl_anim.key_value(m_obj, "rotation_euler", spin_keys(M_SECONDS_PER_TURN, 0.0), interpolation='LINEAR')

    # --- i cinque, sull'arco davanti a M ---
    r = m_radius * SMALL_FRACTION
    arc = m_radius + ARC_GAP + r
    centres, radii = [m_obj.location[:]], [m_radius]
    report = []
    n = len(OTHERS)
    for k, (fname, n_faces, hue) in enumerate(OTHERS):
        V, faces = deltahedra.load_stl(os.path.join(SAFFARO_DIR, fname))
        if len(faces) != n_faces:
            raise ValueError(f"{fname}: {len(faces)} facce, non {n_faces}")
        R = float(np.linalg.norm(V, axis=1).max())
        V = V * (r / R)
        color, clipped = m_scene.oklch_to_linear(PASTEL_L, PASTEL_C, hue)
        name = os.path.splitext(fname)[0]
        mesh = bpy.data.meshes.new(KIT.name(name))
        mesh.from_pydata([tuple(v) for v in V], [], faces)
        mesh.materials.append(m_scene.wire_material(KIT, f"mat_{name}", color, roughness=ROUGHNESS))
        mesh.update()
        obj = KIT.new_object(name, mesh)
        a = math.radians(ARC_STEP * (k - (n - 1) / 2.0))
        obj.location = (arc * math.sin(a), -arc * math.cos(a), r + CLEARANCE)
        centres.append(obj.location[:])
        radii.append(r)
        t0 = OTHERS_AT + k * OTHERS_GAP
        bl_anim.key_value(obj, "scale", [(frame_of(t0), (0.0,) * 3),
                                         (frame_of(t0 + OTHERS_GROW), (1.0,) * 3)])
        bl_anim.key_visibility(obj, [(FRAME_START, False), (frame_of(t0) + 1, True)])
        obj.rotation_mode = 'XYZ'
        phase = 2.0 * math.pi * ((k * 0.618034) % 1.0)
        bl_anim.key_value(obj, "rotation_euler", spin_keys(OTHER_SECONDS_PER_TURN, phase),
                          interpolation='LINEAR')
        report.append(f"{name} ({n_faces} facce): spigolo {r / R:.3f}, tinta {hue:.0f}"
                      + (" (fuori gamut)" if clipped else ""))

    # --- pavimento, cielo, camera ---
    m_scene.build_floor(KIT, FLOOR_SRGB, FLOOR_ROUGHNESS, FLOOR_SPECULAR, FLOOR_SIZE)
    rot = Vector(VIEW.back).to_track_quat('Z', 'Y')
    light = rot.to_matrix() @ Vector(LIGHT_IN_CAMERA)
    m_scene.setup_sky_world(KIT, math.radians(SKY_SUN_ELEVATION),
                            m_scene.sky_rotation(-light), SKY_STRENGTH,
                            sun_size=math.radians(SUN_SIZE_DEG))
    target, distance = deltahedra.frame_all(VIEW, centres, radii, FRAME_FILL)
    cam = RIG.build(KIT, Vector(target + VIEW.back * distance), clip_end=distance + FLOOR_SIZE)
    cam.data.lens = CAMERA_LENS
    cam.rotation_mode = 'QUATERNION'
    cam.rotation_quaternion = rot
    scene.frame_set(FRAME_START)

    print(f"[scene_5a] frame {FRAME_START}-{FRAME_END} a {FPS} fps ({END:.0f} s); M raggio "
          f"{m_radius:.2f}, gli altri {r:.2f} su un arco di raggio {arc:.2f}; camera a {distance:.2f}")
    for line in report:
        print(f"[scene_5a] {line}")


build()
