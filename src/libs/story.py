"""
story.py -- quello che le scene del racconto di M (scene_1, scene_2, ...)
devono avere in comune perche' si raccordino esattamente: la posa di M nel
quadro, la camera, la griglia dei 240 triangoli, i colori, il fondo e la luce.

Una scena che comincia dove finisce la precedente deve ricostruire la stessa
inquadratura e gli stessi oggetti negli stessi posti: se ognuna rifacesse i
conti per conto suo, basterebbe cambiare un numero in una per perdere il
raccordo senza accorgersene. Qui i numeri ci sono una volta sola, e anche i
conti che ne derivano.

NB: richiede `bpy` e `mathutils` -> eseguibile solo dentro Blender.
"""

import math

import mathutils
import numpy as np

import geometry
import pieces
import m_scene


# =============================================================================
# LE COSTANTI DEL RACCONTO
# =============================================================================

FPS        = 24
RESOLUTION = (1920, 1080)

# il quadro e la posa di M che ci combacia (trovata a occhio in M_video)
PAINTING_FILE      = "m.jpg"
ORIENT_EULER_DEG   = (20.7862, 0.0, 0.0)
PAINTING_MODEL_BOX = (66, 107, 814, 797)    # il poliedro dipinto, in pixel
CAMERA_DISTANCE    = 15.0                   # dal centro di M, lungo -Y
SENSOR_WIDTH       = 36.0

# i colori pastello: stessa luminosita' e saturazione in OKLCH
PASTEL_L, PASTEL_C = 0.82, 0.085
M_HUE        = 245.0             # M, quando diventa fisica: blu, come nel quadro
FACE_GRAIN   = 1.0               # quanto della grana della texture del quadro resta
M_ROUGHNESS  = 0.6

# l'icosaedro-gabbia di M: decide anche dove sta il quadro (davanti a lui)
ICO_MARGIN = 1.0

# la griglia dei 240 triangoli: 20 gruppi da 12 (5 x 4 gruppi, 4 x 3 triangoli),
# su un piano parallelo allo schermo, dietro al centro di M
GRID = pieces.Grid(group_cols=5, group_rows=4, cols_per_group=4, rows_per_group=3,
                   spacing=1.2, group_gap=0.6)
GRID_DEPTH = 2.0
GRID_FILL  = 0.80                # quanta parte dell'immagine occupa: margine ampio

# fondo e luce
BACKGROUND_CORNERS_SRGB = {
    "top_left":     (34, 46, 70),
    "top_right":    (16, 22, 38),
    "bottom_left":  (20, 28, 46),
    "bottom_right": (6, 8, 16),
}
BACKGROUND_BLEED  = 1.02
# verso cui va la luce, nel piano dell'immagine (da sinistra, un po' dall'alto):
# e' quella della tavolozza del quadro e quella del sole del cielo
LIGHT_DIRECTION   = (0.866, 0.0, -0.5)
SKY_SUN_ELEVATION = 15.0
SKY_STRENGTH      = 0.1


# =============================================================================
# I CONTI
# =============================================================================

def camera_rig():
    return m_scene.CameraRig('PERSP', CAMERA_DISTANCE, SENSOR_WIDTH, RESOLUTION)


def orient_matrix():
    """La posa di M nel quadro."""
    return mathutils.Euler([math.radians(a) for a in ORIENT_EULER_DEG], 'XYZ').to_matrix().to_4x4()


def pastel(hue):
    """Il pastello della tinta data, in RGBA lineare; errore se esce dal
    gamut sRGB (verrebbe tagliato, e non avrebbe piu' la luminosita' degli
    altri)."""
    color, clipped = m_scene.oklch_to_linear(PASTEL_L, PASTEL_C, hue)
    if clipped:
        raise ValueError(f"il pastello di tinta {hue} esce dal gamut sRGB")
    return color


def model_points(md):
    R = np.asarray(orient_matrix().to_3x3())
    return np.asarray(md.vertices, dtype=float) @ R.T


class Layout:
    """L'inquadratura del racconto: dove sta il quadro, dove sta la camera e
    con che focale. Si calcola da M e dalle dimensioni del quadro.

    Il quadro sta sul piano y = painting_depth (davanti alla gabbia di M),
    scalato e spostato perche' il poliedro dipinto abbia l'altezza e il centro
    di M visto dalla camera; la camera guarda il centro del quadro, e la
    focale lo fa alto quanto l'inquadratura. Quadro e camera dipendono l'uno
    dall'altra (la proiezione dipende da dove sta la camera), quindi si itera
    finche' smettono di cambiare."""

    def __init__(self, md, painting_size):
        self.rig = camera_rig()
        self.ico_scale = geometry.enclosing_scale(md.vertices, geometry.Polyhedron.ico) * ICO_MARGIN
        self.painting_depth = -(self.ico_scale + 1.0)
        w_px, h_px = painting_size
        x0, y0, x1, y1 = PAINTING_MODEL_BOX
        P = model_points(md)
        lo, hi = P.min(axis=0), P.max(axis=0)
        eye = self.rig.location(((lo[0] + hi[0]) / 2, (lo[2] + hi[2]) / 2))
        for _ in range(20):
            Q = self.rig.project_on_plane(P, eye, self.painting_depth)
            qlo, qhi = Q.min(axis=0), Q.max(axis=0)
            k = (qhi[2] - qlo[2]) / (y1 - y0)                    # unita' mondo per pixel
            cx, cz = (qlo[0] + qhi[0]) / 2, (qlo[2] + qhi[2]) / 2
            px = cx - ((x0 + x1) / 2 - w_px / 2) * k
            pz = cz + ((y0 + y1) / 2 - h_px / 2) * k
            moved = abs(px - eye.x) + abs(pz - eye.z)
            eye = mathutils.Vector((px, eye.y, pz))
            if moved < 1e-9:
                break
        self.painting_center = (px, pz)
        self.painting_height = h_px * k
        self.painting_width = w_px * k
        self.eye = eye
        self.lens = self.rig.zoom_for_width(self.painting_height * self.rig.aspect,
                                            self.painting_depth - eye.y)

    def frame_size(self, y):
        """(larghezza, altezza) dell'inquadratura sul piano y."""
        w = self.rig.frame_width(self.lens, y - self.eye.y)
        return w, w / self.rig.aspect

    def screen_to_world(self, fx, fy, y=0.0):
        """Il punto del piano y che nell'immagine sta in (fx, fy), frazioni
        dell'immagine con y verso l'alto."""
        w, h = self.frame_size(y)
        return mathutils.Vector((self.eye.x + (fx - 0.5) * w, y, self.eye.z + (fy - 0.5) * h))

    def grid(self, tris, orient_world=None):
        """Le pose finali dei triangoli nella griglia: m_scene.grid_targets coi
        parametri del racconto. Con orient_world=None le pose sono nel mondo
        (rotazione identita'); altrimenti nel riferimento di quel padre.
        Restituisce (pose, posizioni nel mondo, scala)."""
        w, h = self.frame_size(GRID_DEPTH)
        if orient_world is None:
            orient_world = mathutils.Matrix.Identity(4)
        return m_scene.grid_targets(tris, orient_world, (self.eye.x, self.eye.z), GRID,
                                    GRID_DEPTH, w, h, GRID_FILL)


def build_camera_and_world(kit, layout, clip_end):
    """La camera dell'inquadratura, il fondo sfumato e il cielo."""
    cam = layout.rig.build(kit, layout.eye, clip_end=clip_end)
    cam.data.lens = layout.lens
    m_scene.build_background(kit, layout.rig, cam, layout.lens, CAMERA_DISTANCE + GRID_DEPTH + 10.0,
                             BACKGROUND_CORNERS_SRGB, BACKGROUND_BLEED)
    m_scene.setup_sky_world(kit, math.radians(SKY_SUN_ELEVATION),
                            m_scene.sky_rotation(-mathutils.Vector(LIGHT_DIRECTION)), SKY_STRENGTH)
    return cam


def face_material(kit, face_img, uvs):
    """Il materiale di M e dei suoi triangoli: dai colori del quadro al
    pastello fisico (nodi 'Look' e 'Fade', si veda m_scene.look_face_material)."""
    return m_scene.look_face_material(kit, face_img, uvs, m_scene.PAINTING_PALETTE,
                                      LIGHT_DIRECTION, FACE_GRAIN, pastel(M_HUE), M_ROUGHNESS)
