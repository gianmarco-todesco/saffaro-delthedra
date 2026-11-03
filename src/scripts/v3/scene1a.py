"""
v3/scene1a.py -- un altro inizio per scene-1: M esce dal quadro.

--------------------------------------------------------------------------
LA SCALETTA (secondi, a 24 fps)
--------------------------------------------------------------------------
   0 - 2      il quadro, fermo. M c'e' gia', coi colori del quadro, ma sta
              dietro, e il quadro (opaco) lo nasconde
   2 - 7      M viene avanti lungo l'asse y, verso la camera, e attraversa il
              quadro: se ne vede uscire la parte che lo ha gia' passato
   7 - 10     M davanti al quadro, fermo

--------------------------------------------------------------------------
LE SCELTE
--------------------------------------------------------------------------
* La camera guarda lungo +y, e il suo asse passa per il centro di M
  (story.AxisLayout): cosi' M che si muove lungo y resta sempre allo stesso
  posto nell'immagine. E'
  diversa dalla camera del racconto (story.Layout), che guarda il centro del
  quadro e ha M un po' fuori asse: li' M, muovendosi lungo y, scivolerebbe di
  lato. Il quadro e' rifatto per questa camera, con gli stessi conti di
  story.Layout: sul suo piano, scalato e spostato perche' il poliedro
  dipinto combaci con M visto dalla camera. La focale lo fa entrare tutto
  nell'inquadratura; siccome M e' nella parte alta del quadro, e M sta al
  centro, sotto il quadro resta piu' spazio che sopra.
* Con KEEP_APPARENT_SIZE M, mentre viene avanti, si rimpicciolisce in
  proporzione alla distanza dalla camera: visto dalla camera resta identico
  al poliedro dipinto, in ogni istante (e' una scala attorno all'occhio).
  Senza, cresce man mano che si avvicina.
* Il materiale di M e' quello di scene-1 (story.face_material) nell'aspetto
  del quadro (Look 0). Quadro e M sono opachi; il quadro non fa ombra ne'
  riceve luce.
* Il motore e' Cycles, a 256 campioni (m_scene.use_cycles).

Una sola scena, tutto in keyframe (nessun handler), script idempotente, nomi
col prefisso S1AV3_.
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
        txt = bpy.data.texts.get("scene1a.py")
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
import geometry, bl_utils, extended_face, bl_anim, m_scene, story
for _mod in (geometry, bl_utils, extended_face, bl_anim, m_scene, story):
    importlib.reload(_mod)

from mathutils import Vector


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

PREFIX          = "S1AV3"
COLLECTION_NAME = "scene1a_v3"

# saffaro/assets, accanto al repository: src/libs -> src -> saffaro-delthedra -> saffaro
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(_LIBS))), "assets")

FPS         = story.FPS
RESOLUTION  = story.RESOLUTION
FRAME_START = 1

# --- la scaletta, in secondi ---
EMERGE = (2.0, 7.0)              # M viene avanti e attraversa il quadro
END    = 10.0

KEEP_APPARENT_SIZE = True        # M resta, visto dalla camera, identico al dipinto
FRAME_MARGIN = 1.03              # il quadro intero nell'inquadratura, con un po' di margine
CROSS_MARGIN = 0.05              # all'inizio M sta tutto dietro il quadro, alla fine tutto davanti


# =============================================================================
# LA REGIA
# =============================================================================

FRAME_END = FRAME_START + int(round(END * FPS))


def frame_of(t):
    return FRAME_START + int(round(t * FPS))


def time_of(frame):
    return (frame - FRAME_START) / FPS


def smoothstep(x, x0, x1):
    u = min(1.0, max(0.0, (x - x0) / (x1 - x0)))
    return u * u * (3.0 - 2.0 * u)


# =============================================================================
# COSTRUZIONE
# =============================================================================

KIT = m_scene.Kit(PREFIX, COLLECTION_NAME, ASSETS_DIR)


def crossing_depths(P, eye, plane):
    """Le posizioni del centro di M (lungo y) all'inizio e alla fine: tutto
    dietro il piano del quadro, e tutto davanti, di CROSS_MARGIN. Con
    KEEP_APPARENT_SIZE la scala dipende dalla posizione, e lo stesso
    l'ingombro: si cerca per bisezione."""
    ymin, ymax = P[:, 1].min(), P[:, 1].max()

    def scale(y):
        return (y - eye.y) / (0.0 - eye.y) if KEEP_APPARENT_SIZE else 1.0

    def solve(f):
        lo, hi = plane - 20.0, plane + 20.0
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            if f(mid) > 0:
                hi = mid
            else:
                lo = mid
        return 0.5 * (lo + hi)

    behind = solve(lambda y: y + scale(y) * ymin - (plane + CROSS_MARGIN))   # il punto piu' vicino, dietro
    front = solve(lambda y: y + scale(y) * ymax - (plane - CROSS_MARGIN))    # il piu' lontano, davanti
    return behind, front, scale


def build():
    KIT.clear_previous_run()
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.render.resolution_x, scene.render.resolution_y = RESOLUTION
    scene.frame_start, scene.frame_end = FRAME_START, FRAME_END
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    m_scene.use_cycles(scene)
    KIT.new_collection(scene)

    md = extended_face.make_M()
    painting_img = KIT.load_image(story.PAINTING_FILE)
    layout = story.AxisLayout(md, painting_img.size, FRAME_MARGIN)
    story.build_camera_and_world(KIT, layout, clip_end=story.CAMERA_DISTANCE + story.GRID_DEPTH + 30.0)
    story.build_painting(KIT, painting_img, layout)

    # --- M: mover (posizione lungo y e scala) -> orient (la posa del quadro) -> M ---
    face_img = KIT.load_image(m_scene.FACE_TEXTURE_FILE)
    uvs = m_scene.face_uvs(face_img, m_scene.FACE_TEXTURE_UV_PX, m_scene.FACE_TEXTURE_UV_INSET)
    m_mat = story.face_material(KIT, face_img, uvs)          # Look 0: i colori del quadro
    mover = KIT.new_object("mover")
    mover.empty_display_size = 0.5
    orient = KIT.new_object("orient", parent=mover)
    orient.rotation_euler = [math.radians(a) for a in story.ORIENT_EULER_DEG]
    m_obj = KIT.new_object("M", m_scene.merged_mesh(KIT, md, m_mat, uvs), parent=orient)
    bl_utils.merge_by_distance(m_obj)
    m_obj.visible_shadow = False

    P = story.model_points(md)
    y0, y1, scale = crossing_depths(P, layout.eye, layout.painting_depth)
    frames = range(FRAME_START, FRAME_END + 1)
    ys = [y0 + (y1 - y0) * smoothstep(time_of(f), *EMERGE) for f in frames]
    bl_anim.key_value(mover, "location", [(f, (0.0, y, 0.0)) for f, y in zip(frames, ys)],
                      interpolation='LINEAR')
    bl_anim.key_value(mover, "scale", [(f, (scale(y),) * 3) for f, y in zip(frames, ys)],
                      interpolation='LINEAR')

    scene.frame_set(FRAME_START)
    print(f"[scene1a v3] frame {FRAME_START}-{FRAME_END} a {FPS} fps ({END:.0f} s); camera in "
          f"{tuple(round(c, 3) for c in layout.eye)}, focale {layout.lens:.2f} mm")
    print(f"[scene1a v3] quadro sul piano y = {layout.painting_depth:.3f}, alto {layout.painting_height:.3f}, "
          f"centrato in ({layout.painting_center[0]:.3f}, {layout.painting_center[1]:.3f})")
    print(f"[scene1a v3] M va da y = {y0:.3f} (scala {scale(y0):.3f}) a y = {y1:.3f} "
          f"(scala {scale(y1):.3f}); con y = 0 e scala 1 combacia col dipinto")


build()
