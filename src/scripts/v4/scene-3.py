"""
v4/scene-3.py -- i deltaedri non convessi sul pavimento di v4/scene-2; poi il
composto di tre tetraedri si sdoppia, e ogni copia nuova cresce di un
tetraedro: una fila di catene sempre piu' lunghe, che si sdoppia sempre piu'
in fretta.

--------------------------------------------------------------------------
LA SCALETTA (secondi, a 24 fps)
--------------------------------------------------------------------------
   0 - 1.7    compaiono, uno dopo l'altro, sei deltaedri non convessi
              appoggiati sul pavimento: il composto di tre tetraedri in
              catena, in piedi, in basso al centro dell'immagine, e cinque
              deltaedri di Cundy (OTHERS), in
              posizioni a caso. Tutti girano lentamente su se stessi, e le
              catene non smettono piu'
   4 - 4.5    spariscono tutti, salvo il composto
   8          il composto si sdoppia: lui va a sinistra, e la copia, che
              nasce sovrapposta e trasparente, va a destra comparendo; a 9
              sulla copia di destra cresce un tetraedro nuovo, in cima
  11          di nuovo: le catene che ci sono vanno a sinistra, una copia
              dell'ultima (la piu' lunga) va a destra e cresce di un
              tetraedro. Poi a 12, a 12.5, e sempre piu' in fretta (ogni
              intervallo e' SPEEDUP volte il precedente, ma non meno di
              MIN_GAP): le catene vecchie escono a sinistra
  13 - 17     la camera gira piano verso sinistra, fino a inquadrare tutta
              la fila
  16 - 17     tutto svanisce, salvo il pavimento; gli sdoppiamenti non si
              fermano: la cosa potrebbe andare avanti all'infinito
  17          fine

--------------------------------------------------------------------------
LE SCELTE
--------------------------------------------------------------------------
* Camera, pavimento, sole e fondo sono quelli della fine di v4/scene-2: la
  camera dritta dove la lascia v4/scene-1 (finche' non arretra), e il pavimento inclinato verso di
  lei, come se la guardasse dall'alto di CAMERA_ELEVATION gradi. I conti si
  fanno nel mondo 'virtuale' della camera alta, e il pavimento e i solidi
  sono figli del perno floor_frame che lo porta davanti alla camera vera.
* Le catene sono l'elica di Boerdijk-Coxeter (come v2/scene-3): il vertice
  nuovo e' il riflesso, attraverso la faccia formata dagli ultimi tre, di
  quello che li precede. I vertici dell'elica stanno tutti sul cilindro
  attorno all'asse. Le catene stanno in piedi, con l'asse perpendicolare al
  pavimento e il vertice piu' basso che lo tocca, e crescono verso l'alto:
  il piede sta in basso nell'immagine (BASE_SCREEN), per lasciare spazio.
* La camera arretra lungo il suo asse quanto basta perche' la catena nuova
  (la piu' alta, la piu' a destra) resti dentro FRAME_FILL dell'immagine: da
  quando comincia a non starci, sempre di piu', con una media mobile di
  ZOOM_SMOOTH secondi perche' non segua gli scatti. In PAN gira verso
  sinistra attorno alla normale del pavimento (nel mondo virtuale e' una
  panoramica: il pavimento non si inclina di lato), e arretra ancora, fino a
  inquadrare alla fine tutta la fila, centrata. Per questo e' figlia di
  floor_frame e si muove nel mondo virtuale.
* Ogni catena e' un perno (chain_NN) coi suoi tetraedri, uno per oggetto: le
  facce in comune restano dentro il solido e non si vedono. Le catene girano
  tutte insieme, con la stessa fase. La copia nasce sovrapposta
  all'originale e si sposta solo di lato; separandosi, i due solidi si
  compenetrano, e perche' non si vedano le facce dell'uno passare attraverso
  l'altro la copia compare con una dissolvenza lungo tutto lo spostamento.
  La trasparenza e' per oggetto: il materiale delle catene moltiplica il suo
  'Fade' per la proprieta' 'alpha' dell'oggetto (un nodo Attribute), che i
  tetraedri della copia portano da 0 a 1. Gli originali si spostano a
  sinistra di
  SPACING (1 - b) e la copia a destra di SPACING b, con b = 0.5 finche' gli
  intervalli sono lunghi e via via meno quando si accorciano: la catena
  nuova non deve uscire a destra. Lo spostamento occupa la prima meta'
  dell'intervallo (non piu' di un secondo), la crescita del tetraedro la
  seconda.
* Il tetraedro nuovo esce dalla faccia a cui si attacca: la faccia resta
  ferma e il quarto vertice si allontana fino al suo posto.
* Il materiale e' quello di v2/scene-3 (il triangolo col bordo scuro), con
  in piu' il nodo 'Fade' per svanire alla fine. I solidi fanno ombra sul
  pavimento.
* Il motore e' Cycles, a 256 campioni (m_scene.use_cycles).

Una sola scena, tutto in keyframe (nessun handler), script idempotente, nomi
col prefisso S3V4_.
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
        txt = bpy.data.texts.get("scene-3.py")
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
import geometry, bl_utils, extended_face, bl_anim, m_scene, story, textures, deltahedra
for _mod in (geometry, bl_utils, extended_face, bl_anim, m_scene, story, textures, deltahedra):
    importlib.reload(_mod)

from mathutils import Vector, Matrix, Quaternion


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

PREFIX          = "S3V4"
COLLECTION_NAME = "scene-3_v4"

# saffaro/..., accanto al repository: src/libs -> src -> saffaro-delthedra -> saffaro
_SAFFARO   = os.path.dirname(os.path.dirname(os.path.dirname(_LIBS)))
ASSETS_DIR = os.path.join(_SAFFARO, "assets")
MODELS_DIR = os.path.join(_SAFFARO, "3dmodels", "cundy", "D2-Deltaedri di Cundy")

FPS         = story.FPS
RESOLUTION  = story.RESOLUTION
FRAME_START = 1

# --- la scaletta, in secondi ---
APPEAR_START   = 0.2             # il primo deltaedro comincia a comparire...
APPEAR_STAGGER = 0.25            # ... e gli altri dopo, a questo intervallo
APPEAR_SECONDS = 0.5             # quanto ci mette uno a comparire
VANISH         = (4.0, 4.5)      # gli altri spariscono
SPLITS         = (8.0, 11.0, 12.0, 12.5)   # i primi sdoppiamenti...
SPEEDUP        = 0.92            # ... poi ogni intervallo e' tanto il precedente...
MIN_GAP        = 3.0 / 24.0      # ... ma non meno di questo
MOVE_MAX       = 1.0             # lo spostamento e la crescita: meta' intervallo, non piu' di tanto
FADE_OUT       = (16.0, 17.0)    # tutto svanisce
END            = 17.0
OTHER_SECONDS_PER_TURN = 20.0    # gli altri deltaedri, attorno alla verticale
CHAIN_SECONDS_PER_TURN = 20.0    # le catene, attorno al loro asse, sempre
PAN            = (13.0, 17.0)    # la camera gira piano verso sinistra, fino a inquadrare tutta la fila

# --- la geometria ---
EDGE         = 1.0               # lo spigolo di tutti i solidi
SPACING      = 1.5               # fra le catene, in spigoli
BASE_SCREEN  = -0.6              # il piede delle catene, nell'immagine: frazione della meta' altezza
START_SPIN   = 0.0               # gradi: la rotazione delle catene attorno al loro asse
FRAME_FILL   = 0.9               # la catena nuova sta dentro tanto della meta' immagine, in alto e a destra
ZOOM_SMOOTH  = 0.75              # secondi: la media mobile dell'arretramento della camera
SEED         = 3
SCREEN_GAP   = 0.03              # fra due solidi, nell'immagine (tangenti)
SCREEN_EDGE  = 0.03              # e dal bordo

# --- gli altri deltaedri: i cinque di Cundy con meno facce, come v2/scene-3 ---
# chiave -> (file, tinta OKLCH)
OTHERS = {
    "tetraug":  ("01_Tetraugmented_Tetrahedron.obj",  70.0),   # 12 facce, albicocca
    "gyraug":   ("04_Gyraugmented_Octahedron.obj",   150.0),   # 14, verde menta
    "digyraug": ("05_Digyraugmented_Octahedron.obj", 230.0),   # 20, azzurro
    "trisphen": ("23_Trispheniated_Octahedron.obj",  300.0),   # 20, lilla
    "stella":   ("06_Octaugmented_Octahedron.obj",   110.0),   # 24, giallo
}

# --- il materiale: come v2/scene-3 ---
TEXTURE_FILE   = "face_border.png"
TEXTURE_SIZE   = 1024
TEXTURE_MARGIN = 0.10
BORDER_DARK    = 0.10
BORDER_DRAWN   = 0.04
BORDER_WORLD   = 0.022
COLOR_LCH      = (0.92, 0.035, 5.0)   # rosa chiarissimo; gli altri cambiano solo la tinta
ROUGHNESS      = 0.5

# --- il pavimento e la camera: come alla fine di v4/scene-2 ---
FLOOR_SRGB       = (30, 38, 56)
FLOOR_ROUGHNESS  = 0.85
FLOOR_SPECULAR   = 0.05
FLOOR_SIZE       = 400.0
FLOOR_BELOW      = 2.2
SUN_SIZE_DEG     = 8.0
BACKGROUND_DEPTH = 300.0
CAMERA_ELEVATION = 24.0


# =============================================================================
# LA REGIA
# =============================================================================

FRAME_END = FRAME_START + int(round(END * FPS))


def frame_of(t):
    return FRAME_START + int(round(t * FPS))


def time_of(frame):
    return (frame - FRAME_START) / FPS


def ramp(t, t0, t1):
    return min(1.0, max(0.0, (t - t0) / (t1 - t0)))


def smoother(u):
    return u * u * u * (u * (6.0 * u - 15.0) + 10.0)


def split_times():
    """Gli istanti degli sdoppiamenti e i loro intervalli: SPLITS, poi ogni
    intervallo SPEEDUP volte il precedente (non meno di MIN_GAP), fino alla
    fine: non si fermano durante la dissolvenza."""
    times = list(SPLITS)
    gap = SPLITS[-1] - SPLITS[-2]
    while True:
        gap = max(MIN_GAP, gap * SPEEDUP)
        if times[-1] + 2.0 * gap > END + 1e-9:
            break
        times.append(times[-1] + gap)
    gaps = [b - a for a, b in zip(times, times[1:])]
    gaps.append(min(gaps[-1], END - times[-1]))
    return times, gaps


# =============================================================================
# LA CAMERA E IL PAVIMENTO
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
    return target + (back_h * math.cos(elevation) + np.array([0.0, 0.0, math.sin(elevation)])) * distance


def at_height(basis, tx, ty, z):
    """Il punto alla quota z lungo il raggio della camera per (tx, ty)."""
    d = basis.ray(tx, ty)
    if d[2] >= -1e-6:
        raise ValueError("il raggio non scende: alzare CAMERA_ELEVATION")
    return basis.eye + d * ((z - basis.eye[2]) / d[2])


# =============================================================================
# I SOLIDI
# =============================================================================

KIT = m_scene.Kit(PREFIX, COLLECTION_NAME, ASSETS_DIR)


def helix_vertices(n):
    """I primi n vertici dell'elica di Boerdijk-Coxeter, spigolo 1 (si veda
    v2/scene-3): il tetraedro i-esimo e' (v[i], v[i+1], v[i+2], v[i+3])."""
    def reflect(p, a, b, c):
        nrm = np.cross(b - a, c - a)
        nrm = nrm / np.linalg.norm(nrm)
        return p - 2.0 * np.dot(p - a, nrm) * nrm
    V = [np.array([0.0, 0.0, 0.0]), np.array([1.0, 0.0, 0.0]),
         np.array([0.5, math.sqrt(3) / 2, 0.0]),
         np.array([0.5, math.sqrt(3) / 6, math.sqrt(2.0 / 3.0)])]
    while len(V) < n:
        V.append(reflect(V[-4], V[-3], V[-2], V[-1]))
    return np.array(V)


def helix_axis(V):
    """Un punto dell'asse e la direzione, verso cui cresce l'elica."""
    c = V.mean(axis=0)
    _, _, vt = np.linalg.svd(V - c)
    d = vt[0]
    if np.dot(V[-1] - V[0], d) < 0:
        d = -d
    return c, d


def tetra_mesh(name, base, apex, material, uvs):
    """La mesh di un tetraedro nel riferimento della sua faccia d'attacco
    (si veda v2/scene-3): scalando l'oggetto in z da 0 a 1 il tetraedro esce
    dalla faccia. Restituisce (mesh, matrice di posa)."""
    b = [Vector(p) for p in base]
    c = (b[0] + b[1] + b[2]) / 3.0
    z = (Vector(apex) - c).normalized()
    x = (b[0] - c).normalized()
    y = z.cross(x)
    R = Matrix((x, y, z)).transposed()
    pose = Matrix.Translation(c) @ R.to_4x4()
    inv = pose.inverted()
    verts = [inv @ p for p in b] + [inv @ Vector(apex)]
    centre = sum(verts, Vector()) / 4.0
    faces = []
    for f in ((0, 1, 2), (0, 1, 3), (1, 2, 3), (2, 0, 3)):
        p0, p1, p2 = (verts[i] for i in f)
        if (p1 - p0).cross(p2 - p0).dot(p0 - centre) < 0:
            f = (f[0], f[2], f[1])
        faces.append(f)
    mesh = bpy.data.meshes.new(KIT.name(name))
    mesh.from_pydata([tuple(v) for v in verts], [], faces)
    bl_utils.set_triangle_uvs(mesh, uvs)
    mesh.materials.append(material)
    mesh.update()
    return mesh, pose


ALPHA_PROP = "alpha"
GLOBAL_PATH = 'nodes["Global"].outputs[0].default_value'


def tinted(suffix, texture, hue, per_object=False):
    """Il materiale di v2/scene-3, col nodo 'Fade' (parte da 1, pieno), che
    svanisce in FADE_OUT. Con per_object il 'Fade' e' il prodotto del valore
    del nodo 'Global' (che svanisce) per la proprieta' ALPHA_PROP
    dell'oggetto: va messa su ogni oggetto che lo usa, o Cycles la legge 0."""
    rgba, clipped = m_scene.oklch_to_linear(COLOR_LCH[0], COLOR_LCH[1], hue)
    if clipped:
        raise ValueError(f"il colore di {suffix} esce dal gamut sRGB")
    mat = m_scene.tinted_texture_material(KIT, suffix, texture, rgba, ROUGHNESS)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    out = next(n for n in nodes if n.type == 'OUTPUT_MATERIAL')
    surface = out.inputs["Surface"].links[0].from_socket
    clear = nodes.new("ShaderNodeBsdfTransparent")
    fade = nodes.new("ShaderNodeMixShader")
    fade.name = "Fade"
    fade.inputs["Fac"].default_value = 1.0
    links.new(clear.outputs["BSDF"], fade.inputs[1])
    links.new(surface, fade.inputs[2])
    links.new(fade.outputs["Shader"], out.inputs["Surface"])
    keys = [(frame_of(FADE_OUT[0]), 1.0), (frame_of(FADE_OUT[1]), 0.0)]
    if not per_object:
        bl_anim.key_value(mat.node_tree, m_scene.FADE_PATH, keys)
        return mat
    glob = nodes.new("ShaderNodeValue")
    glob.name = "Global"
    glob.outputs[0].default_value = 1.0
    alpha = nodes.new("ShaderNodeAttribute")
    alpha.attribute_type = 'OBJECT'
    alpha.attribute_name = ALPHA_PROP
    times = nodes.new("ShaderNodeMath")
    times.operation = 'MULTIPLY'
    links.new(glob.outputs[0], times.inputs[0])
    links.new(alpha.outputs["Fac"], times.inputs[1])
    links.new(times.outputs[0], fade.inputs["Fac"])
    bl_anim.key_value(mat.node_tree, GLOBAL_PATH, keys)
    return mat


def load_other(path):
    """Il deltaedro del file, centrato, con lo spigolo EDGE: (vertici, facce)."""
    V, faces = deltahedra.load_welded(path)
    return V * (EDGE / float(np.linalg.norm(V[faces[0][0]] - V[faces[0][1]]))), faces


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

    md = extended_face.make_M()
    painting_img = KIT.load_image(story.PAINTING_FILE)
    ev = story.ExitView(md, painting_img.size)
    rig = ev.layout.rig

    # --- la camera, il mondo del pavimento e il sole: come alla fine di v4/scene-2 ---
    eye1, m_end, lens = np.asarray(ev.eye1), np.asarray(ev.m_end), ev.lens_m
    b1 = Basis(eye1, m_end)
    d0 = float(np.linalg.norm(m_end - eye1))
    cam = rig.build(KIT, Vector(eye1), clip_end=BACKGROUND_DEPTH + 20.0)
    cam.data.lens = lens
    cam.rotation_mode = 'QUATERNION'
    cam.rotation_quaternion = story.look_quat(m_end - eye1)
    back1 = (eye1 - m_end) / d0
    back_h = np.array([back1[0], back1[1], 0.0]) / math.hypot(back1[0], back1[1])
    floor_z = m_end[2] - FLOOR_BELOW
    target2 = np.array([m_end[0], m_end[1], floor_z + 1.0])
    eye2 = orbit(target2, back_h, math.radians(CAMERA_ELEVATION), d0)
    b2 = Basis(eye2, target2)
    R = np.column_stack([b1.r, b1.f, b1.u]) @ np.column_stack([b2.r, b2.f, b2.u]).T
    frame = KIT.new_object("floor_frame")
    frame.matrix_world = (Matrix.Translation(Vector(eye1 - R @ eye2)) @ Matrix(R.tolist()).to_4x4())
    e = math.radians(story.SKY_SUN_ELEVATION)
    h = np.array([-story.LIGHT_DIRECTION[0], -story.LIGHT_DIRECTION[1], 0.0])
    sun = R @ (h / np.linalg.norm(h) * math.cos(e) + np.array([0.0, 0.0, math.sin(e)]))
    m_scene.build_background(KIT, rig, cam, lens, BACKGROUND_DEPTH,
                             story.BACKGROUND_CORNERS_SRGB, story.BACKGROUND_BLEED)
    m_scene.setup_sky_world(KIT, math.asin(sun[2]), m_scene.sky_rotation(sun), story.SKY_STRENGTH,
                            sun_size=math.radians(SUN_SIZE_DEG))
    floor = m_scene.build_floor(KIT, FLOOR_SRGB, FLOOR_ROUGHNESS, FLOOR_SPECULAR, FLOOR_SIZE)
    floor.parent = frame
    floor.location = (target2[0], target2[1], floor_z)

    # --- i materiali ---
    img, base_uvs = textures.border_triangle(size=TEXTURE_SIZE, border=BORDER_DRAWN,
                                             dark=BORDER_DARK, margin=TEXTURE_MARGIN)
    texture = m_scene.write_image(os.path.join(ASSETS_DIR, TEXTURE_FILE), img)
    fraction = BORDER_WORLD / (EDGE * math.sqrt(3.0) / 6.0)
    uvs = textures.scaled_uvs(base_uvs, textures.border_scale(fraction, BORDER_DRAWN))
    mat = tinted("face", texture, COLOR_LCH[2], per_object=True)

    # --- gli sdoppiamenti ---
    times, gaps = split_times()
    n_chains = len(times) + 1
    n_tetra = 3 + len(times)

    # --- l'elica, in piedi: l'asse lungo la verticale del mondo virtuale (la
    # normale del pavimento), il vertice piu' basso sul pavimento, il piede
    # nel punto dell'immagine BASE_SCREEN; cresce verso l'alto ---
    V = helix_vertices(n_tetra + 3 + 200) * EDGE
    c, d = helix_axis(V)
    to_z = Vector(d).rotation_difference(Vector((0.0, 0.0, 1.0))).to_matrix()
    turn = Matrix.Rotation(math.radians(START_SPIN), 3, 'Z')
    P = np.asarray([turn @ to_z @ Vector(v - c) for v in V])[:n_tetra + 3]   # asse: x = y = 0
    rho = float(np.mean(np.hypot(P[:, 0], P[:, 1])))
    P[:, 2] -= P[:, 2].min()
    tan_v = rig.frame_width(lens, 1.0) / rig.aspect / 2.0
    origin = at_height(b2, 0.0, BASE_SCREEN * tan_v, floor_z)
    centre = origin + P[:6].mean(axis=0)
    meshes = []
    for i in range(n_tetra):
        a_, b_, c_, d_ = (P[i + k] for k in range(4))
        meshes.append(tetra_mesh(f"tetra_{i:02d}", (a_, b_, c_), d_, mat, uvs))
    radius3 = float(np.linalg.norm(P[:6] - P[:6].mean(axis=0), axis=1).max())

    # --- le posizioni delle catene lungo x ---
    s = SPACING * EDGE
    moves = [[] for _ in range(n_chains)]       # per catena: (t0, t1, dx)
    starts = [0.0] * n_chains
    first_seen = [0.0] * n_chains
    births = [None] * n_chains                  # per catena: (t, durata dello spostamento)

    def x_at(j, t):
        return starts[j] + sum(dx * smoother(ramp(t, t0, t1)) for t0, t1, dx in moves[j])

    windows = []
    for k, (t, gap) in enumerate(zip(times, gaps), start=1):
        half = min(MOVE_MAX, gap / 2.0)
        beta = 0.5 * min(1.0, gap)
        starts[k] = x_at(k - 1, t)
        first_seen[k] = t
        births[k] = (t, half)
        for j in range(k):
            moves[j].append((t, t + half, -s * (1.0 - beta)))
        moves[k].append((t, t + half, s * beta))
        windows.append((t + half, t + half + min(MOVE_MAX, gap / 2.0)))

    # --- l'ordine delle comparse: il composto e gli altri, a caso ---
    rng = np.random.default_rng(SEED)
    order = ["compound"] + list(OTHERS)
    rng.shuffle(order)
    appear = {key: APPEAR_START + n * APPEAR_STAGGER for n, key in enumerate(order)}

    frames = list(range(FRAME_START, FRAME_END + 1))
    omega = 2.0 * math.pi / (CHAIN_SECONDS_PER_TURN * FPS)
    for j in range(n_chains):
        pivot = KIT.new_object(f"chain_{j:02d}", parent=frame)
        pivot.empty_display_size = 0.3
        bl_anim.key_value(pivot, "location",
                          [(f, tuple(origin + np.array([x_at(j, time_of(f)), 0.0, 0.0]))) for f in frames],
                          interpolation='LINEAR')
        # tutte girano insieme, alla stessa velocita' e con la stessa fase: la
        # copia e' girata come l'originale
        pivot.rotation_mode = 'XYZ'
        bl_anim.key_value(pivot, "rotation_euler", [(FRAME_START, (0.0, 0.0, 0.0)),
                                                    (FRAME_END, (0.0, 0.0, omega * (FRAME_END - FRAME_START)))],
                          interpolation='LINEAR')
        f_seen = frame_of(first_seen[j])
        for i in range(3 + j):
            mesh, pose = meshes[i]
            obj = KIT.new_object(f"chain_{j:02d}_tetra_{i:02d}", mesh, parent=pivot)
            loc, rot, _ = pose.decompose()
            obj.location = loc
            obj.rotation_mode = 'QUATERNION'
            obj.rotation_quaternion = rot
            obj[ALPHA_PROP] = 1.0
            if j == 0:
                t0 = appear["compound"]
                bl_anim.key_value(obj, "scale", [(frame_of(t0), (0.0,) * 3),
                                                 (frame_of(t0 + APPEAR_SECONDS), (1.0,) * 3)])
            elif i == 2 + j:
                # il tetraedro nuovo di questa catena: esce dalla faccia
                g0, g1 = windows[j - 1]
                bl_anim.key_value(obj, "scale", [(frame_of(g0), (1.0, 1.0, 0.0)),
                                                 (max(frame_of(g1), frame_of(g0) + 1), (1.0, 1.0, 1.0))])
                bl_anim.key_visibility(obj, [(FRAME_START, False), (frame_of(g0) + 1, True)])
                continue
            if j > 0:
                # la copia: compare con una dissolvenza lungo lo spostamento
                t0, half = births[j]
                bl_anim.key_value(obj, f'["{ALPHA_PROP}"]', [(frame_of(t0), 0.0),
                                                             (max(frame_of(t0 + half), frame_of(t0) + 1), 1.0)])
                bl_anim.key_visibility(obj, [(FRAME_START, False), (f_seen, True)])

    # --- gli altri: compaiono uno dopo l'altro, girano, spariscono ---
    tan_h = rig.frame_width(lens, 1.0) / 2.0
    cx, cy, depth_c = b2.tangents(centre)
    placed = [(cx, cy, radius3 / depth_c)]
    for key, (path, hue) in OTHERS.items():
        Vk, faces = load_other(os.path.join(MODELS_DIR, path))
        radius = float(np.linalg.norm(Vk, axis=1).max())
        height = floor_z - float(Vk[:, 2].min())
        for _ in range(20000):
            tx = rng.uniform(-tan_h, tan_h)
            ty = rng.uniform(-tan_v, tan_v)
            loc = at_height(b2, tx, ty, height)
            _, _, depth = b2.tangents(loc)
            rho_s = radius / depth
            if abs(tx) + rho_s > tan_h - SCREEN_EDGE or abs(ty) + rho_s > tan_v - SCREEN_EDGE:
                continue
            if all(math.hypot(tx - qx, ty - qy) > rho_s + qr + SCREEN_GAP for qx, qy, qr in placed):
                break
        else:
            raise ValueError(f"non trovo posto per {key}")
        placed.append((tx, ty, rho_s))
        mesh = bpy.data.meshes.new(KIT.name(key))
        mesh.from_pydata([tuple(v) for v in Vk], [], faces)
        bl_utils.set_triangle_uvs(mesh, uvs)
        mesh.materials.append(tinted(f"mat_{key}", texture, hue))
        mesh.update()
        obj = KIT.new_object(key, mesh, parent=frame)
        obj.location = tuple(loc)
        obj.rotation_mode = 'XYZ'
        phase = rng.uniform(0.0, 2.0 * math.pi)
        omega = 2.0 * math.pi / (OTHER_SECONDS_PER_TURN * FPS)
        f_out = frame_of(VANISH[1])
        bl_anim.key_value(obj, "rotation_euler", [(FRAME_START, (0.0, 0.0, phase)),
                                                  (f_out, (0.0, 0.0, phase + omega * (f_out - FRAME_START)))],
                          interpolation='LINEAR')
        bl_anim.key_value(obj, "scale", [(frame_of(appear[key]), (0.0,) * 3),
                                         (frame_of(appear[key] + APPEAR_SECONDS), (1.0,) * 3),
                                         (frame_of(VANISH[0]), (1.0,) * 3), (f_out, (0.0,) * 3)])
        bl_anim.key_visibility(obj, [(FRAME_START, True), (f_out + 1, False)])

    # --- la camera: arretra quanto basta perche' la catena nuova, a destra e
    # in cima, resti dentro l'immagine (FRAME_FILL); in PAN gira piano verso
    # sinistra (attorno alla normale del pavimento: nel mondo virtuale e' una
    # panoramica) fino a inquadrare tutta la fila. Si muove nel mondo
    # virtuale, figlia di floor_frame ---
    def top_z(j, t):
        """L'altezza della cima della catena j: i vertici v0..v[j+4], piu'
        il vertice v[j+5] del tetraedro che sta crescendo, dalla sua faccia."""
        if j == 0:
            return float(P[:6, 2].max())
        g0, g1 = windows[j - 1]
        u = ramp(t, g0, max(g1, g0 + 1.0 / FPS))
        face_z = float(P[j + 2:j + 5, 2].mean())
        return max(float(P[:j + 5, 2].max()), face_z + (P[j + 5, 2] - face_z) * u)

    tan_h = rig.frame_width(lens, 1.0) / 2.0

    def basis_at(delta, phi):
        """La camera virtuale arretrata di delta lungo l'asse iniziale e girata
        di phi verso sinistra: (occhio, avanti, destra, alto)."""
        Rz = np.array([[math.cos(phi), -math.sin(phi), 0.0], [math.sin(phi), math.cos(phi), 0.0],
                       [0.0, 0.0, 1.0]])
        return eye2 - b2.f * delta, Rz @ b2.f, Rz @ b2.r, Rz @ b2.u

    def inside(points, delta, phi):
        eye, f_, r_, u_ = basis_at(delta, phi)
        for q, kind in points:
            v = q - eye
            depth = v @ f_
            if depth <= 0.0:
                return False
            if kind == "right" and (v @ r_) / depth > FRAME_FILL * tan_h:
                return False
            if kind == "left" and (v @ r_) / depth < -FRAME_FILL * tan_h:
                return False
            if kind == "top" and (v @ u_) / depth > FRAME_FILL * tan_v:
                return False
        return True

    def required(points, phi):
        """Quanto deve arretrare almeno la camera girata di phi perche' i
        punti stiano dentro."""
        if inside(points, 0.0, phi):
            return 0.0
        lo, hi = 0.0, 1.0
        while not inside(points, hi, phi):
            hi *= 2.0
        for _ in range(40):
            mid = (lo + hi) / 2.0
            lo, hi = (lo, mid) if inside(points, mid, phi) else (mid, hi)
        return hi

    def chain_points(j, t, kinds):
        x, z = x_at(j, t), top_z(j, t)
        pts = []
        if "top" in kinds:
            pts.append((origin + np.array([x, 0.0, z]), "top"))
        for kind, side in (("right", rho), ("left", -rho)):
            if kind in kinds:
                pts += [(origin + np.array([x + side, 0.0, zz]), kind) for zz in (0.0, z)]
        return pts

    # la fine: tutta la fila, centrata
    every = []
    for j in range(n_chains):
        every += chain_points(j, END, ("top", "right", "left"))
    phi_end, delta_end = 0.0, 0.0
    for _ in range(30):
        delta_end = required(every, phi_end)
        eye, f_, r_, _ = basis_at(delta_end, phi_end)
        tx = [((q - eye) @ r_) / ((q - eye) @ f_) for q, _ in every]
        phi_end -= math.atan((min(tx) + max(tx)) / 2.0)
    delta_end = required(every, phi_end)

    need = []
    for f in frames:
        t = time_of(f)
        w = smoother(ramp(t, *PAN))
        newest = max(j for j in range(n_chains) if j == 0 or t >= first_seen[j])
        back = max(required(chain_points(newest, t, ("top", "right")), phi_end * w), delta_end * w)
        need.append(max(need[-1] if need else 0.0, back))
    half = int(round(ZOOM_SMOOTH * FPS / 2.0))
    padded = [need[0]] * half + need + [need[-1]] * half
    retreat = [sum(padded[k:k + 2 * half + 1]) / (2 * half + 1) for k in range(len(need))]
    cam.parent = frame
    cam.matrix_parent_inverse = Matrix.Identity(4)
    keys_loc, keys_rot = [], []
    for f, r in zip(frames, retreat):
        eye, f_, r_, u_ = basis_at(r, phi_end * smoother(ramp(time_of(f), *PAN)))
        keys_loc.append((f, tuple(eye)))
        keys_rot.append((f, tuple(Matrix([r_, u_, -f_]).transposed().to_quaternion())))
    bl_anim.key_value(cam, "location", keys_loc, interpolation='LINEAR')
    bl_anim.key_value(cam, "rotation_quaternion", keys_rot, interpolation='LINEAR')

    scene.frame_set(FRAME_START)
    newest = x_at(n_chains - 1, END)
    print(f"[scene-3 v4] frame {FRAME_START}-{FRAME_END} a {FPS} fps ({END:.0f} s); "
          f"{len(times)} sdoppiamenti, da {times[0]} a {times[-1]:.2f} s (l'ultimo intervallo "
          f"{gaps[-1]:.3f} s); la catena piu' lunga ha {n_tetra} tetraedri")
    print(f"[scene-3 v4] la catena nuova finisce a x = {newest:.2f}; raggio dell'elica {rho:.3f}; "
          f"la camera arretra di {retreat[-1]:.1f} e gira a sinistra di {math.degrees(phi_end):.1f} gradi")
    print(f"[scene-3 v4] comparse: " + ", ".join(f"{k} {appear[k]:.2f}" for k in order))


build()
