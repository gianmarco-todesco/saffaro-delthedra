"""
draft5/scene-2.py -- v5/scene-2 con due cambi:

* le facce degli otto restano trasparenti anche dove le prende il sole: in
  v5 erano un Principled mescolato al trasparente, e la parte illuminata
  diventava chiara e sembrava opaca. Ora la parte colorata e' emissiva
  (FACE_GLOW), quindi non dipende dalla luce: un vetro colorato sempre
  uguale. I fili restano illuminati;
* il tetraedro sta come una piramide: una faccia appoggiata al pavimento e
  il vertice in alto (polyhedron_geometry), invece che inclinato di 20
  gradi;
* alla fine gli otto non svaniscono col fade-out ma rimpiccioliscono fino a
  sparire, nell'ultimo mezzo secondo, scaglionati da sinistra a destra;
  mentre rimpiccioliscono il loro punto piu' basso resta alla stessa quota
  (shrink_keys).

Cambi del 2026-11-15, sulla voce (draft-5/scene-2/scene-2-voice.mp3):
* icosaedro e M crescono un po' piu' piano (PAIR_GROW) e sono interi quando
  la voce dice "icosaedro" (5,55 - 6,25 s) e "M" (6,5 - 6,9 s): PAIR_DONE;
* M e l'icosaedro cominciano a uscire a 12:02 (SPLIT), il tetraedro comincia
  a crescere quando la voce dice "tetraedro" (12,64 s), non prima
  (TETRA_IN); il pavimento e' fermo al suo posto gia' da 12:12 (FLOOR_IN,
  FLOOR_SETTLE), prima che il tetraedro compaia;
* gli otto non toccano il pavimento: ne restano sospesi poco sopra
  (HOVER), perche' le ombre di un pezzo appoggiato non sono belle;
* i tre platonici sono piu' distanti fra loro (TRIO_RATIO, era
  INNER_RATIO) e i loro centri, come li vede l'occhio, stanno ai vertici di
  un triangolo equilatero: si veda visual_offset.

Prefisso S2D5, collezione scene-2_draft5. Il resto e' v5/scene-2:

v5/scene-2.py -- v4/scene-2 coi tempi nuovi: comincia dove finisce
v4/scene-1 (i 240 triangoli nella griglia, davanti alla camera in asse con M),
e porta all'icosaedro, a M, al tetraedro e agli otto deltaedri convessi, che
stanno su un pavimento.

--------------------------------------------------------------------------
LA SCALETTA (secondi, a 24 fps; m:ff vuol dire m secondi e ff fotogrammi)
--------------------------------------------------------------------------
   0           l'ultimo fotogramma di v4/scene-1: la griglia, la stessa camera
   0.3 - 4.3   i triangoli si rimpiccioliscono fino a sparire, dal centro della
               griglia verso la periferia (piu' in fretta che in v4)
   3:10 - 5:22 l'icosaedro cresce (ease out), a sinistra del centro; M da
               4:06 a 6:18, a destra; girano su se stessi
   8:18 - 12:12 il pavimento sale dal basso: il bordo attraversa l'immagine
               (8:18 - 11:18), poi si ferma sotto il tetraedro
  12:02 - 14:02 M e l'icosaedro escono di lato; da 12:16 il tetraedro cresce
               al centro dell'immagine, completo a 13:16
  17:21        entra l'ottaedro (da sinistra), scivolando sul pavimento
  18:20        entra l'icosaedro (da destra); mentre arrivano il tetraedro si
               sposta, finche' i tre stanno ai vertici di un triangolo
               equilatero col centro al centro dell'immagine
  28:21        crescono gli altri cinque, un quarto di secondo l'uno
               dall'altro: prima le due bipiramidi a sinistra, poi i tre a
               destra. I tre platonici non si spostano (per ora): restano
               centrati, e la fila degli otto e' sbilanciata a destra
  36:09 - 36:21 spariscono tutti rimpicciolendo (scala da 1 a 0) sul
               posto, appoggiati al pavimento, scaglionati da sinistra a
               destra (SHRINK_OUT, SHRINK_SECONDS); resta il pavimento
  36:21        fine

--------------------------------------------------------------------------
CHE COSA CAMBIA RISPETTO A v4/scene-2
--------------------------------------------------------------------------
* I tempi (sopra). Si scrivono come in un montaggio: tc(12, 19) e' 12
  secondi e 19 fotogrammi.
* Il triangolo dei tre platonici ha il centro al centro dell'immagine
  (TRIO_CENTERED): in v4 stava gia' dove sarebbe finito con gli altri cinque,
  spostato a sinistra, e lo spettatore non sa ancora perche'. Gli altri
  cinque stanno rispetto ai tre come in v4.
* Nomi: prefisso S2V5, collezione scene-2_v5.

Il resto e' com'era in v4/scene-2; la sua descrizione, qui sotto, vale ancora.

--------------------------------------------------------------------------
LE SCELTE (da v4/scene-2)
--------------------------------------------------------------------------
* Il raccordo: la camera finale di v4/scene-1 e la sua griglia vengono da
  story.ExitView, gli stessi conti; i triangoli hanno lo stesso materiale
  (i colori del quadro, Look 0).
* M e l'icosaedro stanno nel piano perpendicolare all'asse della camera che
  passa per il centro dove si era fermato M, a PAIR_RADIUS, come in
  v3/scene2b. Lo script controlla che crescendo non tocchino i triangoli
  ancora presenti (nell'immagine) e dice di quanto ci passano.
* La camera e' sempre quella dove finisce v4/scene-1, dritta. Il pavimento
  (quello di v2/scene-4, ardesia) e' inclinato verso di lei: e' come se la
  camera guardasse dall'alto (CAMERA_ELEVATION gradi). I conti si fanno in
  quel mondo 'virtuale', con la camera alta che guarda il pavimento
  orizzontale FLOOR_BELOW sotto il centro di M, e il pavimento e gli otto
  sono figli di un perno (floor_frame) che porta quel mondo davanti alla
  camera vera: la rotazione che gira la camera alta su quella dritta.
  L'immagine finale e' quella che si avrebbe con la camera inclinata. Il
  sole gira con loro, perche' le ombre sul pavimento siano le stesse.
* Il pavimento sale dal basso: si sposta lungo l'alto dell'immagine, e
  all'inizio e' tanto in basso che il suo bordo lontano sta sotto
  l'inquadratura (un piano inclinato verso la camera, se e' grande, arriva
  quasi all'orizzonte comunque lo si abbassi: si vede salire il bordo).
  Il moto ha due tempi: in FLOOR_IN il bordo lontano sale da sotto a sopra
  l'inquadratura, poi in FLOOR_SETTLE il pavimento, che riempie gia'
  l'immagine, finisce di salire fino al tetraedro.
* Gli otto deltaedri convessi stanno sospesi poco sopra il pavimento: il
  vertice piu' basso e' HOVER raggi sopra, e girando attorno alla normale
  del pavimento resta a quella quota. La disposizione e' quella di v3/scene2b
  nell'immagine: per ogni pezzo si prende il suo punto nell'immagine (la
  fila dei tre gruppi, larga WIDTH_FILL) e lo si porta sul pavimento lungo
  il raggio della camera alta. Il tetraedro parte dal centro dell'immagine,
  sul pavimento, e va al suo posto.
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
    # script in src/scripts/draft5, librerie in src/libs
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

PREFIX          = "S2D5"
COLLECTION_NAME = "scene-2_draft5"

# saffaro/..., accanto al repository: src/libs -> src -> saffaro-delthedra -> saffaro
_SAFFARO   = os.path.dirname(os.path.dirname(os.path.dirname(_LIBS)))
ASSETS_DIR = os.path.join(_SAFFARO, "assets")
MODELS_DIR = os.path.join(_SAFFARO, "modelli-3d", "convex-deltahedra")

FPS         = story.FPS
RESOLUTION  = story.RESOLUTION
FRAME_START = 1

def tc(seconds, frames=0):
    """Un tempo scritto come nel montaggio: secondi e fotogrammi (a 24 fps)."""
    return seconds + frames / story.FPS


# --- la scaletta, in secondi ---
VANISH          = (0.3, 4.3)     # i triangoli spariscono, dal centro alla periferia
VANISH_SECONDS  = 0.6            # quanto ci mette un triangolo a rimpicciolirsi
PAIR_GROW       = 2.5            # icosaedro e M crescono in tanto (ease out)...
PAIR_DONE       = {"ico": tc(5, 22), "M": tc(6, 18)}   # ... e sono interi quando la voce li nomina
PAIR_IN         = {k: t - PAIR_GROW for k, t in PAIR_DONE.items()}
SPLIT           = (tc(12, 2), tc(14, 2))     # M e l'icosaedro escono di lato (ease-in)
TETRA_IN        = (tc(12, 16), tc(13, 16))   # il tetraedro cresce, al centro: da "tetraedro" (12,64 s)
FLOOR_IN        = (tc(8, 18), tc(11, 18))    # il bordo del pavimento sale per tutta l'immagine...
FLOOR_SETTLE    = (tc(11, 18), tc(12, 12))   # ... poi il pavimento si ferma, prima del tetraedro
SLIDE_IN        = {"octa": tc(17, 21), "ico_ring": tc(18, 20)}   # entrano scivolando sul pavimento
SLIDE_SECONDS   = 1.8
TETRA_MOVE      = (SLIDE_IN["octa"], SLIDE_IN["octa"] + 2.8)   # intanto il tetraedro va al suo posto
FIVE_IN         = tc(28, 21)     # crescono gli altri cinque...
FIVE_GAP        = 0.25           # ... uno dopo l'altro, prima le bipiramidi a sinistra...
GROW_SECONDS    = 0.6            # ... ognuno in tanto
END_AT          = tc(36, 21)
SHRINK_OUT      = (END_AT - 0.5, END_AT)   # nell'ultimo mezzo secondo spariscono tutti...
SHRINK_SECONDS  = 0.25           # ... rimpicciolendo ognuno in tanto, scaglionati da sinistra a destra
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
TRIO_RATIO    = 1.65             # ... e quello dei tre platonici, piu' larghi
TRIO_ANGLES   = {"tetra": 90.0, "ico_ring": -30.0, "octa": 210.0}
FIVE          = ("tribi", "pentbi", "snub", "triaug", "gyro")
LEFT_COLUMN   = ("tribi", "pentbi")
RIGHT_ANGLES  = {"snub": 150.0, "triaug": 30.0, "gyro": 270.0}
# il gruppo di destra, spostato nell'immagine (in raggi dei pezzi): a
# sinistra, e in alto, cioe' piu' lontano sul pavimento (e piu' piccolo)
RIGHT_SHIFT   = (-0.7, 0.6)
PENTBI_SHIFT  = -0.4             # la bipiramide pentagonale, a sinistra (in raggi)

# --- gli scheletri ---
TRIO_CENTERED = True             # i tre platonici attorno al centro dell'immagine
SKELETONS    = ("tetra", "ico_ring", "octa", "tribi", "pentbi", "snub", "triaug", "gyro")
TUBE_RADIUS  = 0.03              # cilindretti e sferette, in raggi del poliedro
FACE_OPACITY = 0.35
FACE_GLOW    = 1.0               # la forza dell'emissione delle facce: il loro colore, senza luce

# --- il pavimento, la luce, la camera finale ---
FLOOR_SRGB      = (30, 38, 56)
FLOOR_ROUGHNESS = 0.85
FLOOR_SPECULAR  = 0.05
FLOOR_SIZE      = 400.0
FLOOR_BELOW     = 2.2            # il pavimento sta tanto sotto il centro di M
FLOOR_RISE_MARGIN = 2.0          # il bordo lontano parte tanto sotto l'inquadratura, e arriva tanto sopra
SUN_SIZE_DEG    = 8.0
HOVER           = 0.12           # gli otto stanno sospesi: il punto piu' basso tanto sopra il pavimento (in raggi)
BACKGROUND_DEPTH = 300.0
CAMERA_ELEVATION = 24.0          # la camera 'virtuale': gradi sopra l'orizzonte del pavimento


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


def base_down(V, faces):
    """La rotazione (3x3) che porta la faccia piu' rivolta in basso a guardare
    esattamente in basso: il tetraedro come una piramide, con la base
    parallela al pavimento e il vertice in alto."""
    V = np.asarray(V, dtype=float)
    centre = V.mean(axis=0)

    def outward(f):
        a, b, c = V[f[0]], V[f[1]], V[f[2]]
        n = np.cross(b - a, c - a)
        n = n / np.linalg.norm(n)
        return n if n @ (a - centre) > 0 else -n

    n = min((outward(f) for f in faces), key=lambda v: v[2])
    down = np.array([0.0, 0.0, -1.0])
    axis = np.cross(n, down)
    s, c = float(np.linalg.norm(axis)), float(n @ down)
    if s < 1e-12:
        return np.eye(3)
    k = axis / s
    K = np.array([[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]])
    return np.eye(3) + s * K + (1.0 - c) * (K @ K)


def glass_material(key, color_rgba):
    """Le facce: trasparente e un'emissione del colore, mescolati dal nodo
    Fade (FACE_OPACITY quando ci sono). L'emissione non dipende dalla luce,
    quindi la faccia resta trasparente uguale anche al sole."""
    mat, nodes, links = KIT.new_material(f"faces_{key}")
    out = nodes.new("ShaderNodeOutputMaterial")
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = tuple(color_rgba[:3]) + (1.0,)
    emit.inputs["Strength"].default_value = FACE_GLOW
    clear = nodes.new("ShaderNodeBsdfTransparent")
    fade = nodes.new("ShaderNodeMixShader")
    fade.name = "Fade"
    fade.inputs["Fac"].default_value = FACE_OPACITY
    links.new(clear.outputs["BSDF"], fade.inputs[1])
    links.new(emit.outputs["Emission"], fade.inputs[2])
    links.new(fade.outputs["Shader"], out.inputs["Surface"])
    mat.diffuse_color = tuple(color_rgba[:3]) + (1.0,)
    return mat


def polyhedron_geometry(key, md_m):
    """(vertici, facce) nella sfera unitaria, coi vertici ripetuti saldati."""
    V, faces = raw_geometry(key, md_m)
    if key == "tetra":
        V = V @ base_down(V, faces).T
    index, remap = {}, []
    for v in V:
        remap.append(index.setdefault(tuple(np.round(v, 5)), len(index)))
    V = normalized(np.asarray(list(index), dtype=float))
    return V, [[remap[i] for i in f] for f in faces]


def skeleton_objects(key, V, faces):
    """Le facce semitrasparenti (l'oggetto) e un figlio coi cilindretti e le
    sferette."""
    c = color(key)
    face_mat = glass_material(key, c)
    mesh = bpy.data.meshes.new(KIT.name(key))
    mesh.from_pydata([tuple(v) for v in V], [], [list(f) for f in faces])
    mesh.materials.append(face_mat)
    mesh.update()
    obj = KIT.new_object(key, mesh)
    edges = sorted({tuple(sorted((f[k], f[(k + 1) % len(f)]))) for f in faces for k in range(len(f))})
    # anche i fili si dissolvono (nodo Fade), per il fade-out finale
    wire_mat = m_scene.fading_material(KIT, f"wire_{key}", c, roughness=0.35)
    wire_mat.node_tree.nodes["Fade"].inputs["Fac"].default_value = 1.0
    KIT.new_object(f"{key}_wire", m_scene.skeleton_mesh(KIT, f"{key}_wire", V, edges, TUBE_RADIUS, wire_mat),
                   parent=obj)
    return obj, face_mat, wire_mat


def shrink_start(x, x_min, x_max):
    """Quando comincia a sparire il pezzo che nell'immagine sta in x: il
    piu' a sinistra a SHRINK_OUT[0], il piu' a destra in tempo per essere
    sparito a SHRINK_OUT[1]."""
    span = SHRINK_OUT[1] - SHRINK_OUT[0] - SHRINK_SECONDS
    return SHRINK_OUT[0] + span * (x - x_min) / (x_max - x_min)


def shrink_keys(obj, t0, r, lowest, floor_z):
    """Le chiavi (un fotogramma ciascuna, lineari) della scala da r a 0 fra
    t0 e t0 + SHRINK_SECONDS, con un raccordo dolce; la quota del centro
    scende con la scala, perche' il punto piu' basso (lowest, nelle
    coordinate del pezzo) resti alla quota floor_z. La posizione orizzontale
    e' quella che il pezzo ha a t0."""
    f0, f1 = frame_of(t0), frame_of(t0 + SHRINK_SECONDS)
    x, y, _ = obj.location
    scales, locs = [], []
    for f in range(f0, f1 + 1):
        k = r * (1.0 - smoother(ramp(time_of(f), t0, t0 + SHRINK_SECONDS)))
        scales.append((f, (k,) * 3))
        locs.append((f, (x, y, floor_z - lowest * k)))
    bl_anim.key_value(obj, "scale", scales, interpolation='LINEAR')
    bl_anim.key_value(obj, "location", locs, interpolation='LINEAR')


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

    if TRIO_CENTERED:
        # i tre platonici attorno al centro dell'immagine; tutto il resto si
        # sposta con loro, cosi' gli altri cinque stanno rispetto ai tre come in v4
        shift = 0.0
    out = {k: on_circle(shift, TRIO_RATIO * r, a) for k, a in TRIO_ANGLES.items()}
    for k, sign in zip(LEFT_COLUMN, (1.0, -1.0)):
        out[k] = (shift + left_x + (PENTBI_SHIFT * r if k == "pentbi" else 0.0),
                  sign * (r + GROUP_GAP / 2.0))
    dx, dz = RIGHT_SHIFT[0] * r, RIGHT_SHIFT[1] * r
    out.update({k: (x + dx, z + dz) for k, (x, z) in
                ((k, on_circle(shift + right_x, INNER_RATIO * r, a)) for k, a in RIGHT_ANGLES.items())})
    return out, r


def visual_offset(basis, distance, V, r, centre):
    """Di quanto il centro che vede l'occhio (il centro del rettangolo che
    contiene il pezzo nell'immagine, in media sul suo giro attorno alla
    verticale) e' spostato rispetto al centro del pezzo, in unita' del piano
    a `distance`. Per l'ottaedro e l'icosaedro e' quasi zero; il tetraedro,
    che ha la base in basso e il vertice in alto, sembra piu' alto del suo
    centro."""
    cx, cy, _ = basis.tangents(centre)
    acc = np.zeros(2)
    angles = np.linspace(0.0, 2.0 * math.pi, 36, endpoint=False)
    for a in angles:
        c, s_ = math.cos(a), math.sin(a)
        Rz = np.array([[c, -s_, 0.0], [s_, c, 0.0], [0.0, 0.0, 1.0]])
        pts = np.array([basis.tangents(centre + Rz @ v * r)[:2] for v in V])
        acc += (pts.min(axis=0) + pts.max(axis=0)) / 2.0
    acc /= len(angles)
    return (acc - np.array([cx, cy])) * distance


def place_visual(basis, distance, xz, V, r, height):
    """Il centro del pezzo per cui il suo centro visivo, nell'immagine, sta
    in xz (unita' del piano a `distance`)."""
    target = np.asarray(xz, dtype=float)
    q = target.copy()
    for _ in range(6):
        home = on_floor(basis, distance, q, height)
        q = target - visual_offset(basis, distance, V, r, home)
    return on_floor(basis, distance, q, height)


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

    # --- la camera: quella finale di v4/scene-1, ferma ---
    eye1, m_end, lens = np.asarray(ev.eye1), np.asarray(ev.m_end), ev.lens_m
    b1 = Basis(eye1, m_end)
    d0 = float(np.linalg.norm(m_end - eye1))
    cam = rig.build(KIT, Vector(eye1), clip_end=BACKGROUND_DEPTH + 20.0)
    cam.data.lens = lens
    cam.rotation_mode = 'QUATERNION'
    cam.rotation_quaternion = story.look_quat(m_end - eye1)

    # --- il mondo del pavimento: la camera alta che lo guarda, e il perno che
    # la porta sulla camera vera ---
    back1 = (eye1 - m_end) / d0
    back_h = np.array([back1[0], back1[1], 0.0]) / math.hypot(back1[0], back1[1])
    floor_z = m_end[2] - FLOOR_BELOW
    target2 = np.array([m_end[0], m_end[1], floor_z + 1.0])
    eye2 = orbit(target2, back_h, math.radians(CAMERA_ELEVATION), d0)
    b2 = Basis(eye2, target2)
    R = np.column_stack([b1.r, b1.f, b1.u]) @ np.column_stack([b2.r, b2.f, b2.u]).T
    to_camera = mathutils.Matrix.Translation(Vector(eye1 - R @ eye2)) @ mathutils.Matrix(R.tolist()).to_4x4()
    frame = KIT.new_object("floor_frame")
    frame.matrix_world = to_camera

    # il sole: dal centro verso il sole come in story, girato col pavimento
    e = math.radians(story.SKY_SUN_ELEVATION)
    h = np.array([-story.LIGHT_DIRECTION[0], -story.LIGHT_DIRECTION[1], 0.0])
    sun = R @ (h / np.linalg.norm(h) * math.cos(e) + np.array([0.0, 0.0, math.sin(e)]))
    m_scene.build_background(KIT, rig, cam, lens, BACKGROUND_DEPTH,
                             story.BACKGROUND_CORNERS_SRGB, story.BACKGROUND_BLEED)
    m_scene.setup_sky_world(KIT, math.asin(sun[2]), m_scene.sky_rotation(sun), story.SKY_STRENGTH,
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

    # --- il pavimento: sale da sotto, lungo l'alto dell'immagine ---
    floor = m_scene.build_floor(KIT, FLOOR_SRGB, FLOOR_ROUGHNESS, FLOOR_SPECULAR, FLOOR_SIZE)
    floor.parent = frame
    home_floor = np.array([target2[0], target2[1], floor_z])
    # di quanto abbassarlo (lungo l'alto dell'immagine) perche' il bordo
    # lontano stia sotto l'inquadratura (rise), e di quanto perche' stia sopra
    # (rise_top): v u - o = depth tan_v nell'immagine e' il bordo in alto
    tan_v = rig.frame_width(lens, 1.0) / rig.aspect / 2.0
    half = FLOOR_SIZE / 2.0
    rise, rise_top = 0.0, 0.0
    for cx, cy in ((-half, -half), (half, -half), (half, half), (-half, half)):
        v = home_floor + np.array([cx, cy, 0.0]) - eye2
        depth = v @ b2.f
        if depth > 0.0:
            rise = max(rise, v @ b2.u + depth * tan_v + FLOOR_RISE_MARGIN)
            rise_top = max(rise_top, v @ b2.u - depth * tan_v - FLOOR_RISE_MARGIN)

    def floor_offset(t):
        if t <= FLOOR_IN[1]:
            return rise_top + (rise - rise_top) * (1.0 - smoother(ramp(t, *FLOOR_IN)))
        return rise_top * (1.0 - smoother(ramp(t, *FLOOR_SETTLE)))

    bl_anim.key_value(floor, "location",
                      [(f, tuple(home_floor - b2.u * floor_offset(time_of(f))))
                       for f in range(frame_of(FLOOR_IN[0]), frame_of(FLOOR_SETTLE[1]) + 1)],
                      interpolation='LINEAR')
    bl_anim.key_visibility(floor, [(FRAME_START, False), (frame_of(FLOOR_IN[0]), True)])

    # --- gli otto, sul pavimento, nella disposizione di v3/scene2b ---
    layout2, r = screen_layout(rig.frame_width(lens, d0))
    x_min = min(x for x, _ in layout2.values())
    x_max = max(x for x, _ in layout2.values())
    homes = {}
    for n, key in enumerate(SKELETONS, start=2):
        V, faces = polyhedron_geometry(key, md)
        obj, face_mat, wire_mat = skeleton_objects(key, V, faces)
        obj.parent = frame
        rest_z = floor_z + HOVER * r                             # il vertice piu' basso, sospeso
        height = rest_z - float(V[:, 2].min()) * r
        if key in TRIO_ANGLES:
            home = place_visual(b2, d0, layout2[key], V, r, height)
        else:
            home = on_floor(b2, d0, layout2[key], height)
        homes[key] = (home, V)
        if key == "tetra":
            # dal centro dell'immagine al suo posto
            centre = place_visual(b2, d0, (0.0, 0.0), V, r, height)
            obj.location = tuple(centre)
            bl_anim.key_value(obj, "location",
                              [(f, tuple(centre + (home - centre) * smoother(ramp(time_of(f), *TETRA_MOVE))))
                               for f in range(frame_of(TETRA_MOVE[0]), frame_of(TETRA_MOVE[1]) + 1)],
                              interpolation='LINEAR')
            bl_anim.key_value(obj, "scale", [(frame_of(TETRA_IN[0]), (0.0,) * 3), (frame_of(TETRA_IN[1]), (r,) * 3)])
            appear = TETRA_IN[0]
        elif key in SLIDE_IN:
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
            appear = FIVE_IN + FIVE.index(key) * FIVE_GAP
            bl_anim.key_value(obj, "scale", [(frame_of(appear), (0.0,) * 3),
                                             (frame_of(appear + GROW_SECONDS), (r,) * 3)])
        f0 = frame_of(appear)
        obj.rotation_mode = 'XYZ'
        phase = 2.0 * math.pi * ((n * 0.618034) % 1.0)
        bl_anim.key_value(obj, "rotation_euler", [(f0, (0.0, 0.0, phase)),
                                                  (FRAME_END, (0.0, 0.0, phase + spin * (FRAME_END - f0)))],
                          interpolation='LINEAR')
        # alla fine: rimpicciolisce sul posto, col punto piu' basso alla stessa quota
        obj.location = tuple(home)
        shrink_keys(obj, shrink_start(layout2[key][0], x_min, x_max), r, float(V[:, 2].min()), rest_z)
        bl_anim.key_visibility(obj, [(FRAME_START, False), (f0, True)])

    scene.frame_set(FRAME_START)
    print(f"[scene-2 draft5] frame {FRAME_START}-{FRAME_END} a {FPS} fps ({END_AT:.3f} s); camera ferma, "
          f"pavimento inclinato di {CAMERA_ELEVATION} gradi, sale di {rise:.1f} ({rise - rise_top:.1f} col bordo "
          f"in vista)")
    print(f"[scene-2 draft5] la coppia passa dai triangoli ancora presenti, al minimo, a {margin_min:.2f} "
          f"(unita' del piano di M; negativo = li tocca)")
    half_w = rig.frame_width(lens, d0) / 2.0
    # i centri visivi dei tre platonici, e i lati del loro triangolo
    vis = {}
    for key in TRIO_ANGLES:
        home, V = homes[key]
        tx, ty, _ = b2.tangents(home)
        vis[key] = np.array([tx, ty]) * d0 + visual_offset(b2, d0, V, r, home)
    keys = list(TRIO_ANGLES)
    sides = [float(np.linalg.norm(vis[keys[i]] - vis[keys[(i + 1) % 3]])) for i in range(3)]
    print(f"[scene-2 draft5] i centri visivi dei tre platonici: lati "
          f"{', '.join(f'{x:.3f}' for x in sides)} (in raggi: {', '.join(f'{x / r:.2f}' for x in sides)})")
    # quanto sono staccati, nell'immagine, i pezzi della disposizione finale
    hulls = {}
    for key, (home, V) in homes.items():
        pts = []
        for a in np.linspace(0.0, 2.0 * math.pi, 24, endpoint=False):
            c, s_ = math.cos(a), math.sin(a)
            Rz = np.array([[c, -s_, 0.0], [s_, c, 0.0], [0.0, 0.0, 1.0]])
            pts += [np.array(b2.tangents(home + Rz @ v * r)[:2]) * d0 for v in V]
        hulls[key] = np.array(pts)
    worst = (math.inf, None)
    ks = list(hulls)
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            A, B = hulls[ks[i]], hulls[ks[j]]
            ca, cb = A.mean(axis=0), B.mean(axis=0)
            n = (cb - ca) / np.linalg.norm(cb - ca)
            gap = float((B @ n).min() - (A @ n).max())
            if gap < worst[0]:
                worst = (gap, (ks[i], ks[j]))
    print(f"[scene-2 draft5] i due piu' vicini nell'immagine: {worst[1]}, staccati di {worst[0] / r:.2f} raggi "
          f"(lungo la congiungente dei centri, con tutto il giro)")
    xs = [x for x, _ in layout2.values()]
    print(f"[scene-2 draft5] gli otto di raggio {r:.3f}; pavimento a z = {floor_z:.2f}; nell'immagine "
          f"la fila va da {(min(xs) - r) / half_w:+.2f} a {(max(xs) + r) / half_w:+.2f} "
          f"(i bordi sono -1 e +1, misurati sul piano di M)")


build()
