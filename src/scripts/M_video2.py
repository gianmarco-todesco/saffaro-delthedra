"""
M_video2.py -- il secondo video: niente quadro, fondo scuro sfumato. M compare
nella posa del quadro, gira lentamente, si mostra dentro l'icosaedro, sparisce
lasciando solo la gabbia, ricompare, ed esplode nei suoi 240 triangoli.

Come M_video.py: una sola scena, tutto bakerato in keyframe (nessun handler),
script idempotente, nomi col prefisso MV2_ (puo' stare nello stesso .blend di
M_video, ma la scena -- camera, mondo, intervallo, gestione del colore -- la
imposta l'ultimo dei due che gira). I pezzi in comune stanno in libs/m_scene.py.

--------------------------------------------------------------------------
LA SCALETTA (in fotogrammi, a 24 fps)
--------------------------------------------------------------------------
     1           M e' in scena, ferma, nella posa del quadro
    25           comincia a girare attorno all'asse verticale, lentamente
   320           compare l'icosaedro (i tubi crescono di spessore)
   420           M sparisce in dissolvenza: resta solo l'icosaedro
   700           M ricompare in dissolvenza
   860 - 980     esplosione; la rotazione ha frenato fino a fermarsi a 860,
                 l'icosaedro sparisce, la camera allarga il campo
  1000           fine

La rotazione accelera e frena con un raccordo (SPIN_RAMP_FRAMES) e in mezzo e'
a velocita' costante; deve fermarsi all'inizio dell'esplosione perche' la
griglia e' calcolata col perno fermo.

--------------------------------------------------------------------------
IL FONDO
--------------------------------------------------------------------------
Un piano attaccato alla camera, dietro a tutto, che riempie esattamente
l'inquadratura: il colore e' la sfumatura bilineare fra i quattro colori agli
angoli (BACKGROUND_CORNERS_SRGB). Quando la camera allarga il campo, un driver
ingrandisce il piano della stessa misura, cosi' gli angoli dei colori restano
agli angoli dell'immagine. Il driver e' un'espressione semplice (una
divisione), che Blender valuta senza Python: funziona anche con l'esecuzione
automatica degli script disattivata.

--------------------------------------------------------------------------
DOVE SI METTONO LE MANI
--------------------------------------------------------------------------
* la scaletta (SPIN_START, ICO_IN, M_OUT, M_IN, EXPLODE, FRAME_END) e le durate
  delle transizioni (FADE_FRAMES, ICO_GROW_FRAMES)
* SPIN_SECONDS_PER_TURN, SPIN_RAMP_FRAMES  -> la rotazione
* BACKGROUND_CORNERS_SRGB                  -> il fondo
* MODEL_FILL                               -> quanto e' grande M (con la gabbia)
* explosion_keys(), start_delay()          -> la traiettoria dei triangoli
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
        txt = bpy.data.texts.get("M_video2.py")
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
import geometry, bl_utils, extended_face, pieces, bl_anim, m_scene
for _mod in (geometry, bl_utils, extended_face, pieces, bl_anim, m_scene):
    importlib.reload(_mod)

from bl_anim import Key


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

PREFIX          = "MV2"
COLLECTION_NAME = "M_video2"

# saffaro/assets, accanto al repository: src/libs -> src -> saffaro-delthedra -> saffaro
ASSETS_DIR        = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(_LIBS))), "assets")
FACE_TEXTURE_FILE = "m2face_texture.png"

FPS         = 24
RESOLUTION  = (1920, 1080)

# --- la scaletta, in fotogrammi ---
FRAME_START = 1
SPIN_START  = 25                # M ferma per un secondo, poi comincia a girare
ICO_IN      = 320               # compare l'icosaedro
M_OUT       = 420               # M comincia a sparire
M_IN        = 700               # M comincia a ricomparire
EXPLODE     = (860, 980)        # inizio e fine dell'esplosione
FRAME_END   = 1000

FADE_FRAMES     = 30            # durata delle dissolvenze di M
ICO_GROW_FRAMES = 24            # quanto ci mettono i tubi a crescere (e a sparire)

# --- la rotazione ---
SPIN_SECONDS_PER_TURN = 20.0    # a regime: un giro ogni 20 secondi
SPIN_RAMP_FRAMES      = 48      # accelerazione dopo SPIN_START, frenata prima di EXPLODE

# La posa di M nel quadro: e' quella di M_video.py, trovata sulla dissolvenza.
ORIENT_EULER_DEG = (20.7862, 0.0, 0.0)

# --- il fondo ---
# I quattro angoli dell'inquadratura, sRGB. La sfumatura e' bilineare, fatta in
# colori lineari.
BACKGROUND_CORNERS_SRGB = {
    "top_left":     (34, 46, 70),
    "top_right":    (16, 22, 38),
    "bottom_left":  (20, 28, 46),
    "bottom_right": (6, 8, 16),
}
AMBIENT           = 0.5         # luce d'ambiente (del colore medio del fondo): tocca solo l'icosaedro
USE_STANDARD_VIEW = True        # i colori escono come sono scritti (con AgX no)

# --- luce e colori di M: come in M_video.py ---
LIGHT_DIRECTION = (0.866, 0.0, -0.5)   # verso cui va la luce: da sinistra, un po' dall'alto
LIGHT_STRENGTH  = 3.0                  # il sole illumina solo l'icosaedro

FACE_UV_PX    = m_scene.FACE_TEXTURE_UV_PX     # misure sulle immagini: si veda m_scene
FACE_UV_INSET = m_scene.FACE_TEXTURE_UV_INSET
FACE_PALETTE  = m_scene.PAINTING_PALETTE
FACE_GRAIN = 1.0

# --- l'icosaedro ---
ICO_MARGIN         = 1.0
ICO_WIRE_THICKNESS = 0.06
ICO_COLOR          = (0.95, 0.72, 0.15, 1.0)

# --- la camera ---
# Prospettica, alla stessa distanza di M_video.py: la prospettiva e' la stessa.
# La focale si calcola perche' la sfera che contiene la gabbia occupi
# MODEL_FILL dell'altezza dell'inquadratura.
CAMERA_TYPE     = 'PERSP'
CAMERA_DISTANCE = 15.0
SENSOR_WIDTH    = 36.0
MODEL_FILL      = 0.80

# --- l'esplosione ---
GRID = pieces.Grid(group_cols=5, group_rows=4, cols_per_group=4, rows_per_group=3,
                   spacing=1.2, group_gap=0.6)
GRID_DEPTH      = 4.0           # y del piano della griglia: dietro a M
GRID_FILL       = 0.90
CAMERA_ZOOM_OUT = 1.25          # di quanto la camera allarga il campo durante l'esplosione
ZOOM_FRACTION   = 0.5           # in quanta parte dell'esplosione
STAGGER_SECONDS = 1.5           # fra il primo triangolo che parte e l'ultimo
POP_DISTANCE    = 0.8           # di quanto si stacca lungo la normale, prima di volare
POP_FRACTION    = 0.25          # in quanta parte del volo

BACKGROUND_MARGIN = 5.0         # di quanto il fondo sta dietro la griglia
BACKGROUND_BLEED  = 1.02        # il fondo sborda del 2%, per non vederne il bordo


# =============================================================================
# LA REGIA
# =============================================================================

def _check_schedule():
    """La scaletta dev'essere in ordine: un errore qui darebbe animazioni che
    si sovrappongono senza che nulla lo segnali."""
    marks = [FRAME_START, SPIN_START, ICO_IN, M_OUT, M_OUT + FADE_FRAMES, M_IN,
             M_IN + FADE_FRAMES, EXPLODE[0], EXPLODE[1], FRAME_END]
    if marks != sorted(marks):
        raise ValueError(f"scaletta fuori ordine: {marks}")
    if EXPLODE[0] - SPIN_START < 2 * SPIN_RAMP_FRAMES:
        raise ValueError("SPIN_RAMP_FRAMES: accelerazione e frenata non ci stanno")


def spin_angles():
    """L'angolo del perno, fotogramma per fotogramma, da SPIN_START a
    EXPLODE[0]: velocita' che sale da zero con un raccordo a coseno in
    SPIN_RAMP_FRAMES, costante, e scende a zero allo stesso modo, finendo
    esattamente a EXPLODE[0]. Restituisce [(frame, angolo)]."""
    omega = 2.0 * math.pi / (SPIN_SECONDS_PER_TURN * FPS)    # radianti per fotogramma
    f0, f1, ramp = SPIN_START, EXPLODE[0], SPIN_RAMP_FRAMES

    def speed(t):
        if t <= f0 or t >= f1:
            return 0.0
        k = min(1.0, (t - f0) / ramp, (f1 - t) / ramp)
        return omega * (1.0 - math.cos(math.pi * k)) / 2.0

    keys, angle, steps = [(f0, 0.0)], 0.0, 16
    for f in range(f0, f1):
        # integrale della velocita' su [f, f+1], punto medio su `steps` passi
        angle += sum(speed(f + (i + 0.5) / steps) for i in range(steps)) / steps
        keys.append((f + 1, angle))
    return keys


def orient_matrix():
    return mathutils.Euler([math.radians(a) for a in ORIENT_EULER_DEG], 'XYZ') \
        .to_matrix().to_4x4()


# =============================================================================
# L'ESPLOSIONE  --  e' qui che si mettono le mani
# =============================================================================

def start_delay(tri, ranks):
    """Ritardo (frame) con cui parte il triangolo. Default: un ventaglio alla
    volta, prima quelli verso la camera; `ranks[fan]` va da 0 (il piu' vicino)
    a 19."""
    return STAGGER_SECONDS * FPS * ranks[tri.piece.fan] / 19.0


def explosion_keys(tri, target, ranks):
    """Keyframe del triangolo: fermo in M, poi si stacca lungo la normale e
    vola alla sua cella. `target` = (location, quaternione, scala) nel
    riferimento di MV2_orient."""
    e0, e1 = EXPLODE
    fly = (e1 - e0) - STAGGER_SECONDS * FPS
    t1 = e0 + start_delay(tri, ranks)
    t2 = t1 + fly
    normal = mathutils.Vector(tri.piece.normal)
    return [
        Key(FRAME_START, tri.loc, tri.quat, 1.0),
        Key(t1, tri.loc, tri.quat, 1.0),
        Key(t1 + POP_FRACTION * fly, tri.loc + normal * POP_DISTANCE, tri.quat, 1.0),
        Key(t2, *target),
    ]


# =============================================================================
# COSTRUZIONE
# =============================================================================

KIT = m_scene.Kit(PREFIX, COLLECTION_NAME, ASSETS_DIR)
CAMERA = m_scene.CameraRig(CAMERA_TYPE, CAMERA_DISTANCE, SENSOR_WIDTH, RESOLUTION)


def model_frame(md):
    """Centro (x, z) dell'ingombro di M nella posa del quadro: e' dove punta
    la camera."""
    R = np.asarray(orient_matrix().to_3x3())
    P = np.asarray(md.vertices, dtype=float) @ R.T
    lo, hi = P.min(axis=0), P.max(axis=0)
    return (lo[0] + hi[0]) / 2, (lo[2] + hi[2]) / 2


def build_background(cam, zoom):
    """Il fondo sfumato, a BACKGROUND_MARGIN dietro la griglia: si veda
    m_scene.build_background."""
    depth = CAMERA_DISTANCE + GRID_DEPTH + BACKGROUND_MARGIN      # dalla camera
    return m_scene.build_background(KIT, CAMERA, cam, zoom, depth,
                                    BACKGROUND_CORNERS_SRGB, BACKGROUND_BLEED)


def build_camera(eye, cage_radius):
    """La camera, ferma in `eye`. La focale (o ortho_scale) e' quella per cui
    la sfera di raggio `cage_radius` attorno all'origine -- quella che contiene
    la gabbia in qualsiasi rotazione -- occupa MODEL_FILL dell'altezza.
    Durante l'esplosione allarga il campo di CAMERA_ZOOM_OUT."""
    cam = CAMERA.build(KIT, eye, clip_end=CAMERA_DISTANCE + GRID_DEPTH + BACKGROUND_MARGIN + 10.0)
    d = -eye.y
    # semialtezza apparente della sfera vista da d (in prospettiva il bordo e'
    # il cono tangente, non il raggio), piu' lo scarto fra centro di M e origine
    half = cage_radius if CAMERA_TYPE == 'ORTHO' else cage_radius * d / math.sqrt(d * d - cage_radius ** 2)
    half += abs(eye.z)
    zoom = CAMERA.zoom_for_width(2.0 * half / MODEL_FILL * CAMERA.aspect, d)

    e0, e1 = EXPLODE
    bl_anim.key_value(cam.data, CAMERA.zoom_path, [
        (FRAME_START, zoom), (e0, zoom),
        (e0 + ZOOM_FRACTION * (e1 - e0), CAMERA.zoom_out(zoom, CAMERA_ZOOM_OUT)),
    ])
    return cam, zoom


def build():
    _check_schedule()
    KIT.clear_previous_run()

    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.render.resolution_x, scene.render.resolution_y = RESOLUTION
    scene.frame_start, scene.frame_end = FRAME_START, FRAME_END
    if USE_STANDARD_VIEW:
        scene.view_settings.view_transform = 'Standard'
        scene.view_settings.look = 'None'

    KIT.new_collection(scene)
    m_scene.setup_world(KIT, m_scene.mean_srgb(BACKGROUND_CORNERS_SRGB.values()), AMBIENT)
    m_scene.build_light(KIT, LIGHT_DIRECTION, LIGHT_STRENGTH)

    md = extended_face.make_M()
    face_img = KIT.load_image(FACE_TEXTURE_FILE)
    uvs = m_scene.face_uvs(face_img, FACE_UV_PX, FACE_UV_INSET)
    face_mat = m_scene.painted_face_material(KIT, face_img, uvs, FACE_PALETTE,
                                             LIGHT_DIRECTION, FACE_GRAIN, fade=True)

    # --- perno e posa ---
    spin = spin_angles()
    pivot = KIT.new_object("pivot")
    pivot.empty_display_size = 0.5
    bl_anim.apply_euler_keys(pivot, [(f, (0.0, 0.0, a)) for f, a in spin])
    # un keyframe per fotogramma, gia' raccordato: fra l'uno e l'altro, retta
    bl_anim.set_interpolation(pivot, 'LINEAR', ("rotation_euler",))
    orient = KIT.new_object("orient", parent=pivot)
    orient.empty_display_type = 'ARROWS'
    orient.rotation_euler = [math.radians(a) for a in ORIENT_EULER_DEG]
    orient_world = mathutils.Matrix.Rotation(spin[-1][1], 4, 'Z') @ orient_matrix()

    # --- l'icosaedro ---
    e0, e1 = EXPLODE
    ico, ico_scale = m_scene.build_ico(KIT, orient, md, ICO_MARGIN, ICO_COLOR)
    bl_anim.key_value(ico, m_scene.WIRE_THICKNESS_PATH, [
        (ICO_IN, 0.0), (ICO_IN + ICO_GROW_FRAMES, ICO_WIRE_THICKNESS),
        (e0, ICO_WIRE_THICKNESS), (e0 + ICO_GROW_FRAMES, 0.0)])
    bl_anim.key_visibility(ico, [(FRAME_START, False), (ICO_IN, True),
                                 (e0 + ICO_GROW_FRAMES + 1, False)])

    # --- camera e fondo ---
    eye = CAMERA.location(model_frame(md))
    # la gabbia ha circonraggio ico_scale (l'icosaedro di riferimento ha raggio 1)
    cam, zoom = build_camera(eye, ico_scale * (1.0 + ICO_WIRE_THICKNESS))
    final_zoom = CAMERA.zoom_out(zoom, CAMERA_ZOOM_OUT)
    build_background(cam, zoom)

    # --- M intera: sparisce e ricompare in dissolvenza ---
    m_obj = KIT.new_object("M", m_scene.merged_mesh(KIT, md, face_mat, uvs), parent=orient)
    bl_utils.merge_by_distance(m_obj)
    bl_anim.key_value(face_mat.node_tree, m_scene.FADE_PATH, [
        (M_OUT, 1.0), (M_OUT + FADE_FRAMES, 0.0), (M_IN, 0.0), (M_IN + FADE_FRAMES, 1.0)])
    bl_anim.key_visibility(m_obj, [(FRAME_START, True), (M_OUT + FADE_FRAMES + 1, False),
                                   (M_IN, True), (e0, False)])

    # --- i 240 triangoli, al posto di M dall'inizio dell'esplosione ---
    mesh = m_scene.triangle_mesh(KIT, face_mat, uvs)
    tris = [m_scene.Tri(p) for p in pieces.m_pieces(md)]
    frame_w = CAMERA.frame_width(final_zoom, GRID_DEPTH - eye.y)
    targets, world_targets, grid_scale = m_scene.grid_targets(
        tris, orient_world, (eye.x, eye.z), GRID, GRID_DEPTH,
        frame_w, frame_w / CAMERA.aspect, GRID_FILL)
    ranks = m_scene.fan_ranks(tris, orient_world)
    for tri, target in zip(tris, targets):
        obj = KIT.new_object(f"tri_{tri.piece.index:03d}", mesh, parent=orient)
        tri.obj = obj
        bl_anim.apply_keys(obj, explosion_keys(tri, target, ranks))
        bl_anim.key_visibility(obj, [(FRAME_START, False), (e0, True)])

    # --- verifica: a fine esplosione i triangoli sono dove dovevano andare ---
    miss, tilt = m_scene.check_targets(tris, world_targets, scene, FRAME_END)
    scene.frame_set(FRAME_START)

    turns = spin[-1][1] / (2.0 * math.pi)
    unit = "ortho_scale" if CAMERA_TYPE == 'ORTHO' else "focale (mm)"
    print(f"[M_video2] frame {FRAME_START}-{FRAME_END} a {FPS} fps "
          f"({(FRAME_END - FRAME_START + 1) / FPS:.1f} s), {RESOLUTION[0]}x{RESOLUTION[1]}")
    print(f"[M_video2] rotazione da {SPIN_START} a {e0}: {turns:.3f} giri; "
          f"icosaedro {ICO_IN}-{e0 + ICO_GROW_FRAMES}; M via a {M_OUT}, di nuovo a {M_IN}; "
          f"esplosione {e0}-{e1}")
    print(f"[M_video2] camera {CAMERA_TYPE} a distanza {CAMERA_DISTANCE}, "
          f"{unit} {zoom:.3f} -> {final_zoom:.3f}; triangoli scalati a {grid_scale:.3f}")
    print(f"[M_video2] a fine esplosione: scarto di posizione {miss:.2e}, "
          f"di rotazione {tilt:.2e} gradi")
    return tris


TRIS = build()
