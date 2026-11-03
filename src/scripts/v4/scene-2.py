"""
v4/scene-2.py -- comincia dove finisce v4/scene-1 (i 240 triangoli nella
griglia, davanti alla camera di lato), e porta all'icosaedro, a M, al
tetraedro e agli otto deltaedri convessi, che stanno su un pavimento. E'
v3/scene2b portata sulla camera di v4 e sul pavimento.

--------------------------------------------------------------------------
LA SCALETTA (secondi, a 24 fps)
--------------------------------------------------------------------------
   0          l'ultimo fotogramma di v4/scene-1: la griglia, la stessa camera
   0.3 - 5.5  i triangoli si rimpiccioliscono fino a sparire, dal centro della
              griglia verso la periferia
   5          l'icosaedro cresce (ease out), a sinistra del centro; M mezzo
              secondo dopo, a destra; girano su se stessi
  17 - 19     M e l'icosaedro escono di lato
  18          il tetraedro compare, appoggiato sul pavimento, che sale da
              sotto (18 - 19.5); la camera si inclina piano verso il basso
              (18 - 22), perche' il pavimento riempia l'immagine
  23          entra l'ottaedro (da sinistra), scivolando sul pavimento
  24          entra l'icosaedro (da destra)
  32          crescono gli altri cinque, sul pavimento: a 33 s ci sono tutti
  34          fine

--------------------------------------------------------------------------
LE SCELTE
--------------------------------------------------------------------------
* Il raccordo: la camera finale di v4/scene-1 e la sua griglia vengono da
  story.ExitView, gli stessi conti; i triangoli hanno lo stesso materiale
  (i colori del quadro, Look 0).
* M e l'icosaedro stanno nel piano perpendicolare all'asse della camera che
  passa per il centro dove si era fermato M, a PAIR_RADIUS, come in
  v3/scene2b. Lo script controlla che crescendo non tocchino i triangoli
  ancora presenti (nell'immagine) e dice di quanto ci passano.
* Il pavimento e' quello di v2/scene-4 (ardesia), FLOOR_BELOW sotto il
  centro di M. Sale da FLOOR_RISE piu' in basso.
* Gli otto deltaedri convessi stanno appoggiati sul pavimento: il vertice
  piu' basso lo sfiora, e girando attorno alla verticale continua a
  sfiorarlo. La disposizione e' quella di v3/scene2b nell'immagine: per ogni
  pezzo si prende il suo punto nell'immagine (la fila dei tre gruppi, larga
  WIDTH_FILL, vista dalla camera finale) e lo si porta sul pavimento lungo
  il raggio della camera. Per questo la camera finale guarda piu' in basso
  (CAMERA_ELEVATION): i pezzi piu' in alto nell'immagine stanno piu'
  lontani, e il raggio che li raggiunge deve scendere.
* Gli otto sono scheletri come in v3/scene2b (cilindretti, sferette, facce
  semitrasparenti) e fanno ombra sul pavimento; il sole del racconto ha qui
  il disco largo (SUN_SIZE_DEG), per ombre morbide.
* Il fondo sfumato sta lontano (BACKGROUND_DEPTH): la camera vede il
  pavimento fino in fondo, e il fondo vicino lo taglierebbe.
* Il motore e' Cycles, a 256 campioni (m_scene.use_cycles).
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
        txt = bpy.data.texts.get("scene-2.py")
    if txt is None or not txt.filepath:
        raise RuntimeError(
            "non riesco a ricavare il path dello script: il testo non e' salvato "
            "su disco (Text > Save As) oppure e' un blocco 'interno'"
        )
    # attenzione: se il file e' stato aperto con l'opzione 'Relative Path' spuntata,
    # filepath e' del tipo '//../...' (relativo al .blend) e os.path lo interpreta
    # come percorso UNC. bpy.path.abspath lo risolve; sugli assoluti non fa nulla.
    path = os.path.abspath(bpy.path.abspath(txt.filepath))
    # script in src/scripts/v4, librerie in src/libs
    libs = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(path))), "libs")
    if not os.path.isdir(libs):
        raise RuntimeError(f"cartella libs non trovata: {libs}  (filepath: {txt.filepath})")
    return libs


_LIBS = _find_libs_dir()
if _LIBS not in sys.path:
    sys.path.insert(0, _LIBS)

# questo serve nel caso che tu faccia modifiche ai moduli senza interrompere la sessione di Blender
import geometry, bl_utils, extended_face, pieces, bl_anim, m_scene, story, textures
for _mod in (geometry, bl_utils, extended_face, pieces, bl_anim, m_scene, story, textures):
    importlib.reload(_mod)

from mathutils import Vector


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

PREFIX          = "S2V4"
COLLECTION_NAME = "scene-2_v4"

# saffaro/..., accanto al repository: src/libs -> src -> saffaro-delthedra -> saffaro
_SAFFARO   = os.path.dirname(os.path.dirname(os.path.dirname(_LIBS)))
ASSETS_DIR = os.path.join(_SAFFARO, "assets")
MODELS_DIR = os.path.join(_SAFFARO, "modelli-3d", "convex-deltahedra")

FPS         = story.FPS
RESOLUTION  = story.RESOLUTION
FRAME_START = 1

# --- la scaletta, in secondi ---
VANISH          = (0.3, 5.5)     # i triangoli spariscono, dal centro alla periferia
VANISH_SECONDS  = 0.8            # quanto ci mette un triangolo a rimpicciolirsi
PAIR_IN         = {"ico": 5.0, "M": 5.5}   # quando cominciano a crescere
PAIR_GROW       = 2.0            # in tanto (ease out)
SPLIT           = (17.0, 19.0)   # M e l'icosaedro escono di lato
TETRA_IN        = (18.0, 19.0)   # il tetraedro cresce, al suo posto sul pavimento
FLOOR_IN        = (18.0, 19.5)   # il pavimento sale
CAMERA_TILT     = (18.0, 22.0)   # la camera si inclina verso il basso
SLIDE_IN        = {"octa": 23.0, "ico_ring": 24.0}   # entrano scivolando sul pavimento
SLIDE_SECONDS   = 1.8
FIVE_IN         = 32.0           # crescono gli altri cinque...
FIVE_GAP        = 0.1            # ... uno dopo l'altro...
GROW_SECONDS    = 0.6            # ... ognuno in tanto: a 33 s ci sono tutti
END_AT          = 34.0
SPIN_SECONDS_PER_TURN = 20.0     # ognuno su se stesso

# --- la texture (M e l'icosaedro della coppia, come v3/scene2b) ---
TEXTURE_FILE   = "face_border.png"
TEXTURE_SIZE   = 1024
TEXTURE_MARGIN = 0.10
BORDER_DARK    = 0.10
ROUGHNESS      = 0.5
BORDER_WORLD   = 0.022
BORDER_DRAWN   = 0.04

# --- i poliedri: chiave -> (file, tinta OKLCH, (luminosita', saturazione) o None) ---
POLYHEDRA = {
    "M":        (None,                                     230.0, None),          # azzurro
    "ico":      (None,                                      70.0, None),          # albicocca
    "tetra":    ("01_Regular_Tetrahedron.obj",              25.0, (0.65, 0.18)),  # rosso deciso
    "ico_ring": (None,                                      70.0, None),
    "octa":     ("03_Regular_Octahedron.obj",              150.0, None),          # verde menta
    "tribi":    ("02_Triangular_Bipyramid.obj",            300.0, None),          # lilla
    "pentbi":   ("04_Pentagonal_Bipyramid.obj",            190.0, None),          # verde acqua
    "snub":     ("05_Snub_Disphenoid.obj",                 110.0, None),          # giallo
    "triaug":   ("06_Triaugmented_Triangular_Prism.obj",   350.0, None),          # rosa
    "gyro":     ("07_Gyroelongated_Square_Bipyramid.obj",  275.0, None),          # lavanda
}

# --- la coppia ---
PAIR_RADIUS   = 1.0              # M e l'icosaedro
PAIR_GAP      = 0.5              # fra le loro sfere
OUT_MARGIN    = 1.0              # di quanto si esce dall'inquadratura, oltre la sfera

# --- la disposizione nell'immagine: come v3/scene2b ---
WIDTH_FILL    = 0.85             # la fila dei tre gruppi occupa tanta larghezza dell'immagine
GROUP_GAP     = 0.4              # fra un gruppo e il successivo, e fra le due bipiramidi
INNER_RATIO   = 1.45             # raggio dei triangoli, in raggi dei pezzi
TRIO_ANGLES   = {"tetra": 90.0, "ico_ring": -30.0, "octa": 210.0}
FIVE          = ("tribi", "pentbi", "snub", "triaug", "gyro")
LEFT_COLUMN   = ("tribi", "pentbi")
RIGHT_ANGLES  = {"snub": 150.0, "triaug": 30.0, "gyro": 270.0}

# --- gli scheletri ---
SKELETONS    = ("tetra", "ico_ring", "octa", "tribi", "pentbi", "snub", "triaug", "gyro")
TUBE_RADIUS  = 0.03              # cilindretti e sferette, in raggi del poliedro
TETRA_TILT   = -20.0             # gradi attorno a x: si legge sempre come un solido
FACE_OPACITY = 0.35

# --- il pavimento, la luce, la camera finale ---
FLOOR_SRGB      = (30, 38, 56)
FLOOR_ROUGHNESS = 0.85
FLOOR_SPECULAR  = 0.05
FLOOR_SIZE      = 400.0
FLOOR_BELOW     = 2.2            # il pavimento sta tanto sotto il centro di M
FLOOR_RISE      = 6.0            # ... e sale da tanto piu' in basso
SUN_SIZE_DEG    = 8.0
BACKGROUND_DEPTH = 300.0
CAMERA_ELEVATION = 24.0          # la camera finale: gradi sopra l'orizzonte


# =============================================================================
# LA REGIA
# =============================================================================

FRAME_END = FRAME_START + int(round(END_AT * FPS))


def frame_of(t):
    return FRAME_START + int(round(t * FPS))


def time_of(frame):
    return (frame - FRAME_START) / FPS


def ramp(t, t0, t1):
    return min(1.0, max(0.0, (t - t0) / (t1 - t0)))


def ease_in(u):
    return u ** 3


def ease_out(u):
    return 1.0 - (1.0 - u) ** 3


def smoother(u):
    return u * u * u * (u * (6.0 * u - 15.0) + 10.0)


def vanish_start(d, far):
    """Quando comincia a rimpicciolirsi il triangolo a distanza d dal centro
    della griglia (far: la distanza del piu' lontano)."""
    return VANISH[0] + (VANISH[1] - VANISH_SECONDS - VANISH[0]) * d / far


def triangle_scale(t, t0, s):
    return s * (1.0 - ease_in(ramp(t, t0, t0 + VANISH_SECONDS)))


def pair_scale(key, t):
    return ease_out(ramp(t, PAIR_IN[key], PAIR_IN[key] + PAIR_GROW))


# =============================================================================
# LA CAMERA
# =============================================================================

class Basis:
    """Gli assi di una camera in `eye` che guarda `target` con l'orizzonte
    dritto: forward, right, up."""

    def __init__(self, eye, target):
        self.eye = np.asarray(eye, dtype=float)
        f = np.asarray(target, dtype=float) - self.eye
        self.f = f / np.linalg.norm(f)
        r = np.cross(self.f, [0.0, 0.0, 1.0])
        self.r = r / np.linalg.norm(r)
        self.u = np.cross(self.r, self.f)

    def tangents(self, p):
        v = np.asarray(p) - self.eye
        d = v @ self.f
        return (v @ self.r) / d, (v @ self.u) / d, d

    def ray(self, tx, ty):
        d = self.f + tx * self.r + ty * self.u
        return d / np.linalg.norm(d)


def orbit(target, back_h, elevation, distance):
    """La camera a `distance` da `target`, dalla parte di `back_h`
    (orizzontale, unitario), alta `elevation` radianti."""
    return target + (back_h * math.cos(elevation) + np.array([0.0, 0.0, math.sin(elevation)])) * distance


# =============================================================================
# I POLIEDRI
# =============================================================================

KIT = m_scene.Kit(PREFIX, COLLECTION_NAME, ASSETS_DIR)


def normalized(V):
    V = np.asarray(V, dtype=float)
    V = V - V.mean(axis=0)
    return V / np.linalg.norm(V, axis=1).max()


def color(key):
    _, hue, lc = POLYHEDRA[key]
    if lc is None:
        return story.pastel(hue)
    rgba, clipped = m_scene.oklch_to_linear(lc[0], lc[1], hue)
    if clipped:
        raise ValueError(f"il colore di {key} esce dal gamut sRGB")
    return rgba


def raw_geometry(key, md_m):
    source = POLYHEDRA[key][0]
    R = np.asarray(story.orient_matrix().to_3x3())
    if key == "M":
        return np.asarray(md_m.vertices) @ R.T, md_m.faces
    if key in ("ico", "ico_ring"):
        ico = geometry.Polyhedron.ico
        return np.asarray([v.tup() for v in ico.vertices]) @ R.T, ico.faces
    md = geometry.read_obj(os.path.join(MODELS_DIR, source))
    return np.asarray(md.vertices, dtype=float), md.faces


def polyhedron_geometry(key, md_m):
    """(vertici, facce) nella sfera unitaria, coi vertici ripetuti saldati."""
    V, faces = raw_geometry(key, md_m)
    if key == "tetra":
        a = math.radians(TETRA_TILT)
        Rx = np.array([[1.0, 0.0, 0.0], [0.0, math.cos(a), -math.sin(a)], [0.0, math.sin(a), math.cos(a)]])
        V = V @ Rx.T
    index, remap = {}, []
    for v in V:
        remap.append(index.setdefault(tuple(np.round(v, 5)), len(index)))
    V = normalized(np.asarray(list(index), dtype=float))
    return V, [[remap[i] for i in f] for f in faces]


def skeleton_objects(key, V, faces):
    """Le facce semitrasparenti (l'oggetto) e un figlio coi cilindretti e le
    sferette."""
    c = color(key)
    face_mat = m_scene.fading_material(KIT, f"faces_{key}", c, roughness=ROUGHNESS)
    face_mat.node_tree.nodes["Fade"].inputs["Fac"].default_value = FACE_OPACITY
    mesh = bpy.data.meshes.new(KIT.name(key))
    mesh.from_pydata([tuple(v) for v in V], [], [list(f) for f in faces])
    mesh.materials.append(face_mat)
    mesh.update()
    obj = KIT.new_object(key, mesh)
    edges = sorted({tuple(sorted((f[k], f[(k + 1) % len(f)]))) for f in faces for k in range(len(f))})
    wire_mat = m_scene.wire_material(KIT, f"wire_{key}", c, roughness=0.35)
    KIT.new_object(f"{key}_wire", m_scene.skeleton_mesh(KIT, f"{key}_wire", V, edges, TUBE_RADIUS, wire_mat),
                   parent=obj)
    return obj


def textured_object(key, md_m, material, base_uvs, radius):
    """M e l'icosaedro della coppia, col triangolo bordato (si veda
    v2/scene-2)."""
    V, faces = raw_geometry(key, md_m)
    V = normalized(V)
    edge = float(np.linalg.norm(V[faces[0][0]] - V[faces[0][1]]))
    k = textures.border_scale(BORDER_WORLD / (edge * radius * math.sqrt(3.0) / 6.0), BORDER_DRAWN)
    mesh = bpy.data.meshes.new(KIT.name(key))
    mesh.from_pydata([tuple(v) for v in V], [], [list(f) for f in faces])
    bl_utils.set_triangle_uvs(mesh, textures.scaled_uvs(base_uvs, k))
    mesh.materials.append(material)
    mesh.update()
    obj = KIT.new_object(key, mesh)
    obj.visible_shadow = False
    return obj


# =============================================================================
# LE POSIZIONI
# =============================================================================

def screen_layout(frame_w):
    """La disposizione di v3/scene2b, in unita' del piano a cui l'inquadratura
    e' larga frame_w, attorno al suo centro: {chiave: (x, z)}, e il raggio dei
    pezzi."""
    tri_half = INNER_RATIO * math.cos(math.radians(30.0)) + 1.0
    r = (WIDTH_FILL * frame_w - 2.0 * GROUP_GAP) / (2.0 + 4.0 * tri_half)
    h = r * tri_half
    left_x = -(h + GROUP_GAP + r)
    right_x = h + GROUP_GAP + h
    shift = -((left_x - r) + (right_x + h)) / 2.0

    def on_circle(cx, radius, angle_deg):
        a = math.radians(angle_deg)
        return (cx + radius * math.cos(a), radius * math.sin(a))

    out = {k: on_circle(shift, INNER_RATIO * r, a) for k, a in TRIO_ANGLES.items()}
    for k, sign in zip(LEFT_COLUMN, (1.0, -1.0)):
        out[k] = (shift + left_x, sign * (r + GROUP_GAP / 2.0))
    out.update({k: on_circle(shift + right_x, INNER_RATIO * r, a) for k, a in RIGHT_ANGLES.items()})
    return out, r


def on_floor(basis, distance, xz, centre_height):
    """Il punto dove sta il centro del pezzo che, nell'immagine, sta dove
    starebbe il punto (x, z) del piano a `distance`: lungo quel raggio, alla
    quota centre_height."""
    d = basis.ray(xz[0] / distance, xz[1] / distance)
    if d[2] >= -1e-6:
        raise ValueError("il raggio non scende: alzare CAMERA_ELEVATION")
    s = (centre_height - basis.eye[2]) / d[2]
    return basis.eye + d * s


# =============================================================================
# COSTRUZIONE
# =============================================================================

def build():
    KIT.clear_previous_run()
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.render.resolution_x, scene.render.resolution_y = RESOLUTION
    scene.frame_start, scene.frame_end = FRAME_START, FRAME_END
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    m_scene.use_cycles(scene)
    scene.cycles.transparent_max_bounces = 32
    KIT.new_collection(scene)
    frames = list(range(FRAME_START, FRAME_END + 1))

    md = extended_face.make_M()
    painting_img = KIT.load_image(story.PAINTING_FILE)
    ev = story.ExitView(md, painting_img.size)
    rig = ev.layout.rig

    # --- la camera: da quella finale di v4/scene-1 a quella del pavimento ---
    eye1, m_end, lens = np.asarray(ev.eye1), np.asarray(ev.m_end), ev.lens_m
    b1 = Basis(eye1, m_end)
    d0 = float(np.linalg.norm(m_end - eye1))
    back1 = (eye1 - m_end) / d0
    back_h = np.array([back1[0], back1[1], 0.0]) / math.hypot(back1[0], back1[1])
    e1 = math.asin(back1[2])
    floor_z = m_end[2] - FLOOR_BELOW
    target2 = np.array([m_end[0], m_end[1], floor_z + 1.0])
    e2 = math.radians(CAMERA_ELEVATION)
    eye2 = orbit(target2, back_h, e2, d0)
    b2 = Basis(eye2, target2)

    cam = rig.build(KIT, Vector(eye1), clip_end=BACKGROUND_DEPTH + 20.0)
    cam.data.lens = lens
    cam.rotation_mode = 'QUATERNION'
    keys_loc, keys_rot = [], []
    for f in frames:
        w = smoother(ramp(time_of(f), *CAMERA_TILT))
        target = m_end + (target2 - m_end) * w
        eye = orbit(target, back_h, e1 + (e2 - e1) * w, d0)
        keys_loc.append((f, tuple(eye)))
        keys_rot.append((f, tuple(story.look_quat(target - eye))))
    bl_anim.key_value(cam, "location", keys_loc, interpolation='LINEAR')
    bl_anim.key_value(cam, "rotation_quaternion", keys_rot, interpolation='LINEAR')
    m_scene.build_background(KIT, rig, cam, lens, BACKGROUND_DEPTH,
                             story.BACKGROUND_CORNERS_SRGB, story.BACKGROUND_BLEED)
    m_scene.setup_sky_world(KIT, math.radians(story.SKY_SUN_ELEVATION),
                            m_scene.sky_rotation(-Vector(story.LIGHT_DIRECTION)), story.SKY_STRENGTH,
                            sun_size=math.radians(SUN_SIZE_DEG))

    # --- i triangoli, dove li lascia v4/scene-1 ---
    face_img = KIT.load_image(m_scene.FACE_TEXTURE_FILE)
    uvs_m = m_scene.face_uvs(face_img, m_scene.FACE_TEXTURE_UV_PX, m_scene.FACE_TEXTURE_UV_INSET)
    tri_mesh = m_scene.triangle_mesh(KIT, story.face_material(KIT, face_img, uvs_m), uvs_m)
    tris = [m_scene.Tri(p) for p in pieces.m_pieces(md)]
    targets = ev.grid_poses(tris)
    grid_centre = sum((t[0] for t in targets), Vector()) / len(targets)
    far = max((t[0] - grid_centre).length for t in targets)
    starts = []
    for tri, (loc, quat, s) in zip(tris, targets):
        obj = KIT.new_object(f"tri_{tri.piece.index:03d}", tri_mesh)
        obj.location = loc
        obj.rotation_mode = 'QUATERNION'
        obj.rotation_quaternion = quat
        obj.visible_shadow = False
        t0 = vanish_start((loc - grid_centre).length, far)
        f0, f1 = frame_of(t0), frame_of(t0 + VANISH_SECONDS)
        bl_anim.key_value(obj, "scale", [(f, (triangle_scale(time_of(f), t0, s),) * 3)
                                         for f in range(f0, f1 + 1)], interpolation='LINEAR')
        bl_anim.key_visibility(obj, [(FRAME_START, True), (f1 + 1, False)])
        starts.append((np.asarray(loc), s * pieces.CIRCUMRADIUS, t0))

    # --- la coppia: nel piano dell'immagine per il centro di M ---
    img, base_uvs = textures.border_triangle(size=TEXTURE_SIZE, border=BORDER_DRAWN, dark=BORDER_DARK,
                                             margin=TEXTURE_MARGIN)
    texture = m_scene.write_image(os.path.join(ASSETS_DIR, TEXTURE_FILE), img)
    x_pair = PAIR_RADIUS + PAIR_GAP / 2.0
    x_out = rig.frame_width(lens, d0) / 2.0 + PAIR_RADIUS + OUT_MARGIN
    spin = 2.0 * math.pi / (SPIN_SECONDS_PER_TURN * FPS)
    margin_min = math.inf
    for n, (key, sign) in enumerate((("ico", -1.0), ("M", 1.0))):
        mat = m_scene.tinted_texture_material(KIT, f"mat_{key}", texture, color(key), ROUGHNESS)
        obj = textured_object(key, md, mat, base_uvs, PAIR_RADIUS)
        locs, scales = [], []
        for f in frames:
            t = time_of(f)
            s = pair_scale(key, t)
            out = ease_in(ramp(t, *SPLIT))
            c = m_end + b1.r * (sign * (x_pair + (x_out - x_pair) * out))
            locs.append((f, tuple(c)))
            scales.append((f, (PAIR_RADIUS * s,) * 3))
            # quanto ci passa dai triangoli ancora presenti, nell'immagine
            if s > 0.0 and out == 0.0:
                cx, cy, _ = b1.tangents(c)
                for p, rad, t0 in starts:
                    sc = triangle_scale(t, t0, 1.0)
                    if sc <= 0.0:
                        continue
                    px, py, depth = b1.tangents(p)
                    gap = math.hypot(px - cx, py - cy) - PAIR_RADIUS * s / d0 - rad * sc / depth
                    margin_min = min(margin_min, gap * d0)
        bl_anim.key_value(obj, "location", locs, interpolation='LINEAR')
        bl_anim.key_value(obj, "scale", scales, interpolation='LINEAR')
        f0 = frame_of(PAIR_IN[key])
        obj.rotation_mode = 'XYZ'
        phase = 2.0 * math.pi * ((n * 0.618034) % 1.0)
        bl_anim.key_value(obj, "rotation_euler", [(f0, (0.0, 0.0, phase)),
                                                  (FRAME_END, (0.0, 0.0, phase + spin * (FRAME_END - f0)))],
                          interpolation='LINEAR')
        bl_anim.key_visibility(obj, [(FRAME_START, False), (f0, True), (frame_of(SPLIT[1]) + 1, False)])

    # --- il pavimento: sale da sotto ---
    floor = m_scene.build_floor(KIT, FLOOR_SRGB, FLOOR_ROUGHNESS, FLOOR_SPECULAR, FLOOR_SIZE)
    floor.location = (target2[0], target2[1], floor_z)
    bl_anim.key_value(floor, "location",
                      [(f, (target2[0], target2[1], floor_z - FLOOR_RISE * (1.0 - ease_out(ramp(time_of(f), *FLOOR_IN)))))
                       for f in range(frame_of(FLOOR_IN[0]), frame_of(FLOOR_IN[1]) + 1)],
                      interpolation='LINEAR')
    bl_anim.key_visibility(floor, [(FRAME_START, False), (frame_of(FLOOR_IN[0]), True)])

    # --- gli otto, sul pavimento, nella disposizione di v3/scene2b ---
    layout2, r = screen_layout(rig.frame_width(lens, d0))
    for n, key in enumerate(SKELETONS, start=2):
        V, faces = polyhedron_geometry(key, md)
        obj = skeleton_objects(key, V, faces)
        height = floor_z - float(V[:, 2].min()) * r            # il vertice piu' basso sul pavimento
        home = on_floor(b2, d0, layout2[key], height)
        if key in SLIDE_IN:
            # da fuori dall'inquadratura, scivolando sul pavimento lungo la sua orizzontale
            _, _, depth = b2.tangents(home)
            side = -1.0 if key == "octa" else 1.0
            start = home + b2.r * side * (rig.frame_width(lens, depth) / 2.0 + abs(b2.tangents(home)[0]) * depth
                                          + r + OUT_MARGIN)
            t0 = SLIDE_IN[key]
            bl_anim.key_value(obj, "location",
                              [(f, tuple(start + (home - start) * ease_out(ramp(time_of(f), t0, t0 + SLIDE_SECONDS))))
                               for f in range(frame_of(t0), frame_of(t0 + SLIDE_SECONDS) + 1)],
                              interpolation='LINEAR')
            obj.scale = (r,) * 3
            appear = t0
        else:
            obj.location = tuple(home)
            appear = TETRA_IN[0] if key == "tetra" else FIVE_IN + FIVE.index(key) * FIVE_GAP
            grow = TETRA_IN[1] - TETRA_IN[0] if key == "tetra" else GROW_SECONDS
            bl_anim.key_value(obj, "scale", [(frame_of(appear), (0.0,) * 3), (frame_of(appear + grow), (r,) * 3)])
        f0 = frame_of(appear)
        obj.rotation_mode = 'XYZ'
        phase = 2.0 * math.pi * ((n * 0.618034) % 1.0)
        bl_anim.key_value(obj, "rotation_euler", [(f0, (0.0, 0.0, phase)),
                                                  (FRAME_END, (0.0, 0.0, phase + spin * (FRAME_END - f0)))],
                          interpolation='LINEAR')
        bl_anim.key_visibility(obj, [(FRAME_START, False), (f0, True)])

    scene.frame_set(FRAME_START)
    print(f"[scene-2 v4] frame {FRAME_START}-{FRAME_END} a {FPS} fps ({END_AT:.0f} s); camera da "
          f"{CAMERA_TILT[0]} a {CAMERA_TILT[1]} s, da {math.degrees(e1):.1f} a {CAMERA_ELEVATION} gradi")
    print(f"[scene-2 v4] la coppia passa dai triangoli ancora presenti, al minimo, a {margin_min:.2f} "
          f"(unita' del piano di M; negativo = li tocca)")
    print(f"[scene-2 v4] gli otto di raggio {r:.3f}; pavimento a z = {floor_z:.2f}")


build()
