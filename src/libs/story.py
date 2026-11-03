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

import bpy
import mathutils
import numpy as np

import bl_utils
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


class AxisLayout:
    """Come Layout, ma con l'asse della camera che passa per il centro
    di M: la camera sta in (0, -CAMERA_DISTANCE, 0) e guarda lungo +y. Il
    quadro sta sullo stesso piano di Layout, scalato e spostato perche'
    il poliedro dipinto abbia l'altezza e il centro di M visto da qui; la
    focale fa entrare il quadro intero (con frame_margin). Ha gli attributi
    che usano build_camera_and_world e build_painting.

    Serve alle scene in cui M si muove lungo y restando, visto dalla camera,
    dove sta nel quadro (v3/scene1a): con la camera di Layout, che guarda il
    centro del quadro, M scivolerebbe di lato."""

    def __init__(self, md, painting_size, frame_margin=1.03):
        ref = Layout(md, painting_size)          # per il piano del quadro e la camera
        self.rig = ref.rig
        self.painting_depth = ref.painting_depth
        self.eye = mathutils.Vector((0.0, -CAMERA_DISTANCE, 0.0))
        w_px, h_px = painting_size
        x0, y0, x1, y1 = PAINTING_MODEL_BOX
        Q = self.rig.project_on_plane(model_points(md), self.eye, self.painting_depth)
        qlo, qhi = Q.min(axis=0), Q.max(axis=0)
        k = (qhi[2] - qlo[2]) / (y1 - y0)                # unita' mondo per pixel
        cx, cz = (qlo[0] + qhi[0]) / 2, (qlo[2] + qhi[2]) / 2
        px = cx - ((x0 + x1) / 2 - w_px / 2) * k
        pz = cz + ((y0 + y1) / 2 - h_px / 2) * k
        self.painting_center = (px, pz)
        self.painting_height = h_px * k
        self.painting_width = w_px * k
        # la focale: il quadro intero, attorno all'asse (che non e' il suo centro)
        half_w = max(abs(px - self.painting_width / 2), abs(px + self.painting_width / 2))
        half_h = max(abs(pz - self.painting_height / 2), abs(pz + self.painting_height / 2))
        width = 2.0 * max(half_w, half_h * self.rig.aspect) * frame_margin
        self.lens = self.rig.zoom_for_width(width, self.painting_depth - self.eye.y)


# =============================================================================
# L'USCITA DAL QUADRO (v4): M esce dal quadro verso la camera di lato
# =============================================================================
#
# I conti che v4/scene-1 e v4/scene-2 devono fare uguali perche' la seconda
# cominci dove finisce la prima: dove si ferma M, la camera di lato e quella
# finale (girata su M), e la griglia dei 240 triangoli davanti a lei.

EXIT_CROSS_MARGIN = 0.05         # all'inizio M e' subito dietro il quadro
EXIT_FINAL_GAP    = 1.0          # dopo l'uscita, fra il retro di M e il quadro
EXIT_SCREEN_GAP   = 0.05         # ... e fra M e il quadro nell'immagine (frazione della larghezza)
EXIT_SIDE_ANGLE   = 35.0         # la camera di lato: gradi attorno alla verticale (verso destra)
EXIT_ELEVATION    = 8.0          # ... gradi in alto
EXIT_DISTANCE     = 14.0         # ... dal punto che guarda
EXIT_FRAME_FILL   = 0.85         # ... e quanta immagine occupano M e il quadro
EXIT_M_FILL       = 0.7          # alla fine, quanta ne occupa la gabbia di M
EXIT_GRID_BEHIND  = 3.0          # la griglia e' tanto piu' lontana del centro di M


def camera_back(side_deg, elevation_deg):
    """Dal punto guardato verso la camera: (0, -1, 0) con angoli nulli."""
    a, e = math.radians(side_deg), math.radians(elevation_deg)
    return np.array([math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)])


def screen_coords(eye, target, points):
    """I punti nell'immagine della camera in `eye` che guarda `target` con
    l'orizzonte dritto, in tangenti dell'angolo dall'asse: (x, y)."""
    f = (target - eye) / np.linalg.norm(target - eye)
    r = np.cross(f, [0.0, 0.0, 1.0])
    r = r / np.linalg.norm(r)
    u = np.cross(r, f)
    v = np.asarray(points) - eye
    depth = v @ f
    return (v @ r) / depth, (v @ u) / depth


def lens_to_fit(rig, eye, target, points, fill):
    """La focale per cui i punti, visti da `eye` che guarda `target`,
    occupano `fill` dell'immagine nella dimensione che arriva prima al
    bordo."""
    x, y = screen_coords(eye, target, points)
    tan_half = max(np.abs(x).max(), np.abs(y).max() * rig.aspect) / fill
    return rig.sensor_width / 2.0 / tan_half


def look_quat(direction):
    """La rotazione della camera che guarda lungo `direction`, con
    l'orizzonte dritto."""
    return mathutils.Vector(direction).normalized().to_track_quat('-Z', 'Y')


class ExitView:
    """Le posizioni dell'uscita dal quadro di v4/scene-1, da M e dalle
    dimensioni del quadro. Attributi: layout (AxisLayout), plane (il piano
    del quadro), s0 (la scala di M), y0 e y1 (dove sta M prima e dopo),
    side (di quanto M va di lato, verso -x), m_end (il centro di M dopo),
    target1, eye1, lens1 (la camera di lato), lens_m (la camera finale: sta
    in eye1 e guarda m_end), ico_scale (la gabbia di M)."""

    def __init__(self, md, painting_size):
        self.layout = layout = AxisLayout(md, painting_size)
        self.plane = plane = layout.painting_depth
        P = model_points(md)
        self.P = P
        eye0 = np.asarray(layout.eye)
        ymin, ymax = P[:, 1].min(), P[:, 1].max()
        # il punto piu' vicino di M a EXIT_CROSS_MARGIN dietro il piano: y + s(y) ymin,
        # con s(y) = (y - eye.y) / (0 - eye.y), e' lineare in y
        k = -eye0[1]
        self.y0 = (plane + EXIT_CROSS_MARGIN - ymin) / (1.0 + ymin / k)
        self.s0 = (self.y0 + k) / k
        self.y1 = plane - EXIT_FINAL_GAP - self.s0 * ymax
        radius = self.s0 * float(np.linalg.norm(P, axis=1).max())
        sphere = [radius * np.array(v) for v in
                  ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
        self.side, self.target1, self.eye1, self.lens1 = self._side_view(sphere)
        self.m_end = np.array([-self.side, self.y1, 0.0])
        self.ico_scale = geometry.enclosing_scale(md.vertices, geometry.Polyhedron.ico) * ICO_MARGIN
        cage = [self.m_end + self.s0 * self.ico_scale * np.array(v) for v in
                ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]
        self.lens_m = lens_to_fit(layout.rig, self.eye1, self.m_end, cage, EXIT_M_FILL)

    def _side_view(self, m_points):
        """La camera laterale: di quanto M va di lato (verso -x), il punto
        guardato, la camera e la focale. Lo spostamento cresce a passi di 5 cm
        finche' fra M e il quadro (fermo) resta EXIT_SCREEN_GAP della
        larghezza dell'immagine. `m_points` sono i punti di M attorno al suo
        centro."""
        layout = self.layout
        px, pz = layout.painting_center
        hw, hh = layout.painting_width / 2.0, layout.painting_height / 2.0
        p_centre = np.array([px, layout.painting_depth, pz])
        corners = [p_centre + np.array([sx * hw, 0.0, sz * hh]) for sx in (-1, 1) for sz in (-1, 1)]
        side = 0.0
        while True:
            m_end = np.array([-side, self.y1, 0.0])
            target = (m_end + p_centre) / 2.0
            eye = target + camera_back(EXIT_SIDE_ANGLE, EXIT_ELEVATION) * EXIT_DISTANCE
            pts = [m_end + q for q in m_points]
            lens = lens_to_fit(layout.rig, eye, target, corners + pts, EXIT_FRAME_FILL)
            tan_half = layout.rig.sensor_width / 2.0 / lens
            gap = (screen_coords(eye, target, corners)[0].min()
                   - screen_coords(eye, target, pts)[0].max()) / (2.0 * tan_half)
            if gap >= EXIT_SCREEN_GAP:
                return side, target, eye, lens
            side += 0.05
            if side > 20.0:
                raise ValueError("non riesco a separare M dal quadro")

    def end_rotation(self):
        """La rotazione della camera finale (in eye1, verso m_end)."""
        return look_quat(self.m_end - self.eye1)

    def grid_distance(self):
        return float(np.linalg.norm(self.m_end - self.eye1)) + EXIT_GRID_BEHIND

    def grid_poses(self, tris):
        """La posa finale di ogni triangolo nel mondo: la griglia di GRID
        (m_scene.grid_targets, come se la camera guardasse lungo +y) portata
        davanti alla camera finale, sul piano perpendicolare al suo asse a
        grid_distance(). Restituisce [(location, quaternione, scala)]."""
        rig, distance = self.layout.rig, self.grid_distance()
        w = rig.frame_width(self.lens_m, distance)
        _, virtual, s = m_scene.grid_targets(tris, mathutils.Matrix.Identity(4), (0.0, 0.0), GRID, 0.0,
                                             w, w / rig.aspect, GRID_FILL)
        R = self.end_rotation().to_matrix()
        # dal riferimento 'camera lungo +y' a quello della camera: x resta x, la
        # profondita' (+y) va lungo -z, l'alto (+z) lungo +y
        C = mathutils.Matrix(((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0)))
        q = (R @ C).to_quaternion()
        eye = mathutils.Vector(self.eye1)
        return [(eye + R @ mathutils.Vector((p.x, p.z, -distance)), q, s) for p in virtual]


def build_camera_and_world(kit, layout, clip_end):
    """La camera dell'inquadratura, il fondo sfumato e il cielo."""
    cam = layout.rig.build(kit, layout.eye, clip_end=clip_end)
    cam.data.lens = layout.lens
    m_scene.build_background(kit, layout.rig, cam, layout.lens, CAMERA_DISTANCE + GRID_DEPTH + 10.0,
                             BACKGROUND_CORNERS_SRGB, BACKGROUND_BLEED)
    m_scene.setup_sky_world(kit, math.radians(SKY_SUN_ELEVATION),
                            m_scene.sky_rotation(-mathutils.Vector(LIGHT_DIRECTION)), SKY_STRENGTH)
    return cam


def build_painting(kit, image, layout):
    """Il quadro: un rettangolo emissivo con l'immagine, nella posizione e
    nella grandezza di `layout` (il poliedro dipinto combacia con M visto
    dalla camera), fuori dall'illuminazione. Il materiale ha il nodo 'Fade'
    (0 = invisibile, 1 = pieno, che e' il valore di partenza): le chiavi le
    mette chi chiama, su m_scene.FADE_PATH. Restituisce (oggetto, materiale)."""
    width, height = layout.painting_width, layout.painting_height
    mesh = bpy.data.meshes.new(kit.name("painting"))
    mesh.from_pydata([(-width / 2, 0, -height / 2), (width / 2, 0, -height / 2),
                      (width / 2, 0, height / 2), (-width / 2, 0, height / 2)], [], [(0, 1, 2, 3)])
    layer = mesh.uv_layers.new(name="UVMap")
    for li, uv in zip(mesh.polygons[0].loop_indices, ((0, 0), (1, 0), (1, 1), (0, 1))):
        layer.data[li].uv = uv
    mat, nodes, links = kit.new_material("painting")
    out = nodes.new("ShaderNodeOutputMaterial")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    emit = nodes.new("ShaderNodeEmission")
    clear = nodes.new("ShaderNodeBsdfTransparent")
    mix = nodes.new("ShaderNodeMixShader")
    mix.name = "Fade"
    mix.inputs["Fac"].default_value = 1.0
    links.new(tex.outputs["Color"], emit.inputs["Color"])
    links.new(clear.outputs["BSDF"], mix.inputs[1])
    links.new(emit.outputs["Emission"], mix.inputs[2])
    links.new(mix.outputs["Shader"], out.inputs["Surface"])
    bl_utils.set_blended(mat)
    mesh.materials.append(mat)
    obj = kit.new_object("painting", mesh)
    center = layout.painting_center
    obj.location = (center[0], layout.painting_depth, center[1])
    m_scene.hide_from_light(obj)
    return obj, mat


def face_material(kit, face_img, uvs):
    """Il materiale di M e dei suoi triangoli: dai colori del quadro al
    pastello fisico (nodi 'Look' e 'Fade', si veda m_scene.look_face_material)."""
    return m_scene.look_face_material(kit, face_img, uvs, m_scene.PAINTING_PALETTE,
                                      LIGHT_DIRECTION, FACE_GRAIN, pastel(M_HUE), M_ROUGHNESS)
