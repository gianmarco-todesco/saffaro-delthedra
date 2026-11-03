"""
v3/scene2b.py -- comincia dove finisce v2/scene-1.py (i 240 triangoli di M
nella griglia), e porta all'icosaedro, a M, al tetraedro e agli otto deltaedri
convessi. E' v2/scene-2.py con due cambiamenti: M e l'icosaedro compaiono
mentre i triangoli stanno ancora sparendo, e i deltaedri convessi che
vengono dopo sono disegnati come scheletri con le facce semitrasparenti.

--------------------------------------------------------------------------
LA SCALETTA (secondi, a 24 fps)
--------------------------------------------------------------------------
   0          l'ultimo fotogramma di v2/scene-1: i 240 triangoli nella
              griglia, stessa camera, stesso fondo, stessa luce, stesso
              materiale
   0.3 - 5.5  i triangoli si rimpiccioliscono fino a sparire, dal centro della
              griglia verso la periferia
   ...        mentre spariscono, M e l'icosaedro crescono insieme al centro
              (ease out), sempre dentro il cerchio che i triangoli hanno gia'
              lasciato libero, girando lentamente su se stessi
  15 - 17     M e l'icosaedro schizzano fuori dall'inquadratura, e fra i due
              cresce il tetraedro, formato a 17 s
  21          entra l'ottaedro (da sinistra), e il tetraedro sale al suo posto
  22          entra l'icosaedro (da destra): col tetraedro e l'ottaedro forma
              un triangolo stretto, nel piano dello schermo
  30          compaiono uno dopo l'altro gli altri cinque deltaedri convessi:
              a sinistra del triangolo le due bipiramidi, una sopra l'altra; a
              destra gli altri tre, su un triangolo con la punta in basso
  34          fine

Ogni poliedro gira sempre su se stesso attorno all'asse verticale.

--------------------------------------------------------------------------
LE SCELTE
--------------------------------------------------------------------------
* Il raccordo: camera, fondo, luce, griglia e materiale dei triangoli vengono
  da libs/story.py, gli stessi conti di scene_1. Il primo fotogramma e'
  l'ultimo di scene_1.
* La texture dei poliedri e' generata (textures.border_triangle): un
  triangolo equilatero con un bordo scuro e il centro chiaro e neutro, che
  ogni materiale moltiplica per il suo colore. Si riscrive in
  assets/face_border.png a ogni corsa. Il bordo e' largo uguale (BORDER_WORLD)
  su tutte le facce di tutti i poliedri: ognuno ingrandisce il triangolo UV
  quanto serve alla grandezza delle sue facce.
* M e l'icosaedro hanno la posa di M nel quadro, e l'icosaedro e' quello su
  cui e' costruita M: la stessa simmetria nella stessa posizione. Gli altri
  vengono da modelli-3d/convex-deltahedra.
* Ogni poliedro sta in una sfera di raggio PAIR_RADIUS (M e l'icosaedro,
  all'inizio) o PIECE_R (gli otto dal tetraedro in poi): l'icosaedro rientra
  piu' piccolo, perche' alla fine ci devono stare otto poliedri. Sono due
  oggetti, scambiati mentre e' fuori campo.
* La disposizione finale: tre gruppi in fila, separati da GROUP_GAP. A
  sinistra le due bipiramidi in colonna; al centro il triangolo del
  tetraedro, dell'ottaedro e dell'icosaedro; a destra gli altri tre su un
  triangolo uguale (raggio INNER_RATIO * PIECE_R) ma con la punta in basso. PIECE_R e' il piu' grande
  per cui la fila occupa WIDTH_FILL della larghezza dell'immagine; la fila e'
  centrata.
* Colori pastello, stessa luminosita' e saturazione in OKLCH (story.pastel);
  M azzurro, l'icosaedro albicocca (il complementare); il tetraedro e' un
  rosso piu' deciso, fuori dalla serie dei pastelli.
* M e l'icosaedro crescono come una coppia, scalata attorno al centro
  dell'immagine: alla scala s i centri stanno a s volte la distanza finale e
  i raggi sono s volte quello finale. A ogni fotogramma lo script calcola la
  scala piu' grande per cui la coppia non tocca nessun triangolo ancora
  presente (nell'immagine: triangoli e poliedri proiettati sullo stesso
  piano, con PAIR_CLEAR di margine), poi sceglie il primo istante da cui la
  crescita (ease out, PAIR_GROW secondi) non supera mai quella scala.
* Il tetraedro e gli altri sette (anche l'icosaedro che rientra) sono
  scheletri: gli spigoli cilindretti e i vertici sferette dello stesso raggio
  (TUBE_RADIUS), nel colore del poliedro, e le facce dello stesso colore,
  semitrasparenti (FACE_OPACITY). M e l'icosaedro della coppia restano col
  triangolo bordato.
* Niente ombre portate, come nelle altre scene.
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
        txt = bpy.data.texts.get("scene2b.py")
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
import geometry, bl_utils, extended_face, pieces, bl_anim, m_scene, story, textures
for _mod in (geometry, bl_utils, extended_face, pieces, bl_anim, m_scene, story, textures):
    importlib.reload(_mod)

from mathutils import Vector


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

PREFIX          = "S2BV3"
COLLECTION_NAME = "scene2b_v3"

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
PAIR_GROW       = 2.5            # M e l'icosaedro crescono in tanto (ease out), appena possono
PAIR_CLEAR      = 0.15           # fra la coppia e i triangoli ancora presenti, nell'immagine (unita' del piano y = 0)
SPLIT_END       = 17.0           # M e l'icosaedro sono fuori, il tetraedro e' formato...
SPLIT_SECONDS   = 2.0            # ... in tanti secondi
# quando entrano i tre del triangolo (il tetraedro sale con l'ottaedro)
TRIO_IN         = {"octa": 21.0, "tetra": 21.0, "ico_ring": 22.0}
TRIO_SECONDS    = 1.8            # quanto ci mettono ad arrivare
FIVE_IN     = 30.0           # compare il primo dei cinque
FIVE_GAP    = 0.4            # fra uno e il successivo
GROW_SECONDS    = 0.8            # quanto ci mette uno dei cinque a comparire
END_AT          = 34.0

SPIN_SECONDS_PER_TURN = 20.0     # ognuno su se stesso

# --- la texture ---
TEXTURE_FILE   = "face_border.png"   # generata in assets a ogni corsa
TEXTURE_SIZE   = 1024
TEXTURE_MARGIN = 0.10            # fra il triangolo disegnato e il bordo dell'immagine
BORDER_DARK    = 0.10            # il grigio del bordo (sRGB, 0..1)
ROUGHNESS      = 0.5
# Lo spessore del bordo scuro, uguale su tutte le facce di tutti i poliedri:
# BORDER_WORLD in unita' del mondo, sul poliedro alla sua grandezza (circa 3
# pixel a 1080 righe). La texture lo disegna sottilissimo (BORDER_DRAWN, in
# frazione dell'inraggio del triangolo), e ogni poliedro lo allarga quanto
# serve alle sue facce ingrandendo il triangolo UV (si veda textures.py).
BORDER_WORLD   = 0.022
BORDER_DRAWN   = 0.04

# --- i poliedri: chiave -> (file, tinta OKLCH, (luminosita', saturazione) o None) ---
# None = il pastello del racconto (story.pastel). M e l'icosaedro hanno la posa
# di M nel quadro; gli altri quella del file. L'icosaedro e' due oggetti: quello
# della coppia con M e quello che rientra piu' piccolo col triangolo (ico_ring),
# perche' con la grandezza cambia anche il triangolo UV che da' lo spessore del
# bordo.
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

# --- la disposizione, nel piano dello schermo (y = 0) ---
PAIR_RADIUS   = 1.0              # M e l'icosaedro, all'inizio
PAIR_GAP      = 0.5              # fra le loro sfere
WIDTH_FILL    = 0.85             # la fila dei tre gruppi occupa tanta larghezza dell'immagine
GROUP_GAP     = 0.4              # fra un gruppo e il successivo, e fra le due bipiramidi
INNER_RATIO   = 1.45             # raggio dei triangoli, in raggi dei pezzi
# gli angoli (gradi; 0 = a destra, 90 = in alto): il tetraedro in alto,
# l'icosaedro in basso a destra (arriva da destra), l'ottaedro in basso a sinistra
TRIO_ANGLES = {"tetra": 90.0, "ico_ring": -30.0, "octa": 210.0}
# gli ultimi cinque, nell'ordine in cui compaiono: le bipiramidi a sinistra
# (dall'alto), gli altri tre a destra, su un triangolo con la punta in basso
# (gli angoli: in alto a sinistra, in alto a destra, in basso)
FIVE = ("tribi", "pentbi", "snub", "triaug", "gyro")
LEFT_COLUMN = ("tribi", "pentbi")
RIGHT_ANGLES = {"snub": 150.0, "triaug": 30.0, "gyro": 270.0}
OUT_MARGIN = 1.0                 # di quanto si esce dall'inquadratura, oltre la sfera

# --- gli scheletri: tutti tranne la coppia ---
SKELETONS    = ("tetra", "ico_ring", "octa", "tribi", "pentbi", "snub", "triaug", "gyro")
TUBE_RADIUS  = 0.03              # cilindretti e sferette, in raggi del poliedro
# Il tetraedro del file, girando attorno alla verticale, tiene una faccia di
# taglio e sembra un triangolo: lo si inclina attorno a x. Col segno meno la
# cima va indietro e si legge sempre come un solido; con +20 a tratti torna a
# sembrare un triangolo, con la base di sbieco.
TETRA_TILT   = -20.0             # gradi
FACE_OPACITY = 0.35              # le facce


# =============================================================================
# LA REGIA
# =============================================================================

T_SPLIT0  = SPLIT_END - SPLIT_SECONDS
T_TRIO0   = min(TRIO_IN.values())
T_TRIO1   = max(TRIO_IN.values()) + TRIO_SECONDS
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


def ease_inout(u):
    return u * u * (3.0 - 2.0 * u)


def _check_schedule():
    marks = [0.0, VANISH[0], VANISH[1], T_SPLIT0, SPLIT_END, T_TRIO0, T_TRIO1,
             FIVE_IN, FIVE_IN + 4 * FIVE_GAP + GROW_SECONDS, END_AT]
    if marks != sorted(marks):
        raise ValueError(f"scaletta fuori ordine: {marks}")


def vanish_start(d, far):
    """Quando comincia a rimpicciolirsi il triangolo a distanza d dal centro
    della griglia (far: la distanza del piu' lontano)."""
    return VANISH[0] + (VANISH[1] - VANISH_SECONDS - VANISH[0]) * d / far


def triangle_scale(t, t0, s):
    """La scala del triangolo che comincia a sparire a t0 (s: la sua scala
    nella griglia)."""
    return s * (1.0 - ease_in(ramp(t, t0, t0 + VANISH_SECONDS)))


class PairGrowth:
    """La crescita della coppia M + icosaedro (si veda LE SCELTE): fit[f] e'
    la scala piu' grande che non tocca i triangoli al fotogramma f, start
    l'istante da cui parte la crescita."""

    def __init__(self, layout, tris_world, tri_radius, grid_scale, far, centre_grid, P):
        eye = np.asarray(layout.eye)
        centre = np.asarray(P["centre"])
        x_pair = PAIR_RADIUS + PAIR_GAP / 2.0
        # i triangoli proiettati sul piano y = 0: centro e raggio, e quando spariscono
        k = (0.0 - eye[1]) / (np.array([w[1] for w in tris_world]) - eye[1])
        self.proj = eye + (np.array([np.asarray(w) for w in tris_world]) - eye) * k[:, None]
        self.proj_r = tri_radius * grid_scale * k
        d = np.array([(w - centre_grid).length for w in tris_world])
        self.t0 = np.array([vanish_start(x, far) for x in d])
        self.grid_scale = grid_scale
        self.centres = [centre + np.array([-x_pair, 0.0, 0.0]), centre + np.array([x_pair, 0.0, 0.0])]
        self.centre = centre
        frames = range(FRAME_START, FRAME_END + 1)
        self.fit = {f: self._fit(time_of(f)) for f in frames}
        self.start = self._start(frames)

    def _clear(self, s, t):
        present = np.array([triangle_scale(t, t0, 1.0) for t0 in self.t0]) > 1e-6
        if not present.any():
            return True
        scale_now = np.array([triangle_scale(t, t0, 1.0) for t0 in self.t0])
        for c in self.centres:
            cc = self.centre + (c - self.centre) * s
            dist = np.linalg.norm((self.proj - cc)[:, [0, 2]], axis=1)
            need = PAIR_RADIUS * s + self.proj_r * scale_now + PAIR_CLEAR
            if np.any((dist < need) & present):
                return False
        return True

    def _fit(self, t):
        if self._clear(1.0, t):
            return 1.0
        lo, hi = 0.0, 1.0
        for _ in range(30):
            mid = 0.5 * (lo + hi)
            if self._clear(mid, t):
                lo = mid
            else:
                hi = mid
        return lo

    def scale(self, t, start=None):
        start = self.start if start is None else start
        return ease_out(ramp(t, start, start + PAIR_GROW))

    def _start(self, frames):
        for f0 in frames:
            t0 = time_of(f0)
            if all(self.scale(time_of(f), t0) <= self.fit[f] + 1e-9 for f in frames):
                return t0
        raise ValueError("la coppia non trova mai posto fra i triangoli")


# =============================================================================
# COSTRUZIONE
# =============================================================================

KIT = m_scene.Kit(PREFIX, COLLECTION_NAME, ASSETS_DIR)


def normalized(V):
    """Vertici centrati nel baricentro e scalati nella sfera unitaria: la
    grandezza la da' la scala dell'oggetto."""
    V = np.asarray(V, dtype=float)
    V = V - V.mean(axis=0)
    return V / np.linalg.norm(V, axis=1).max()


def color(key):
    """Il colore del poliedro, RGBA lineare."""
    _, hue, lc = POLYHEDRA[key]
    if lc is None:
        return story.pastel(hue)
    rgba, clipped = m_scene.oklch_to_linear(lc[0], lc[1], hue)
    if clipped:
        raise ValueError(f"il colore di {key} esce dal gamut sRGB")
    return rgba


def polyhedron_geometry(key, md_m):
    """(vertici, facce) del poliedro `key` nella sfera unitaria, coi vertici
    ripetuti saldati (servono per gli spigoli degli scheletri)."""
    source = POLYHEDRA[key][0]
    R = np.asarray(story.orient_matrix().to_3x3())
    if key == "M":
        V, faces = np.asarray(md_m.vertices) @ R.T, md_m.faces
    elif key in ("ico", "ico_ring"):
        ico = geometry.Polyhedron.ico
        V, faces = np.asarray([v.tup() for v in ico.vertices]) @ R.T, ico.faces
    else:
        md = geometry.read_obj(os.path.join(MODELS_DIR, source))
        V, faces = md.vertices, md.faces
    V = np.asarray(V, dtype=float)
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
    """Lo scheletro: le facce semitrasparenti (l'oggetto, che si muove e
    scala) e un figlio coi cilindretti e le sferette."""
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
    wire = KIT.new_object(f"{key}_wire", m_scene.skeleton_mesh(KIT, f"{key}_wire", V, edges,
                                                               TUBE_RADIUS, wire_mat), parent=obj)
    wire.visible_shadow = False
    return obj


def polyhedron_mesh(key, md_m, material, base_uvs, radius):
    """La mesh del poliedro `key`, nella sfera unitaria, con la stessa UV su
    tutte le facce (sono tutte triangoli equilateri uguali).

    `radius` e' la grandezza a cui lo si vede (la scala dell'oggetto): da li'
    l'inraggio delle facce nel mondo, e l'ingrandimento del triangolo UV per
    cui il bordo scuro e' largo BORDER_WORLD. Restituisce (mesh, frazione
    dell'inraggio occupata dal bordo, ingrandimento)."""
    source = POLYHEDRA[key][0]
    R = np.asarray(story.orient_matrix().to_3x3())
    if key == "M":
        V, faces = np.asarray(md_m.vertices) @ R.T, md_m.faces
    elif key in ("ico", "ico_ring"):
        ico = geometry.Polyhedron.ico
        V, faces = np.asarray([v.tup() for v in ico.vertices]) @ R.T, ico.faces
    else:
        md = geometry.read_obj(os.path.join(MODELS_DIR, source))
        V, faces = md.vertices, md.faces
    V = normalized(V)
    edge = float(np.linalg.norm(V[faces[0][0]] - V[faces[0][1]]))
    inradius = edge * radius * math.sqrt(3.0) / 6.0
    fraction = BORDER_WORLD / inradius
    k = textures.border_scale(fraction, BORDER_DRAWN)
    mesh = bpy.data.meshes.new(KIT.name(key))
    mesh.from_pydata([tuple(v) for v in V], [], [list(f) for f in faces])
    bl_utils.set_triangle_uvs(mesh, textures.scaled_uvs(base_uvs, k))
    mesh.materials.append(material)
    mesh.update()
    return mesh, fraction, k


def build_vanishing_triangles(layout, md):
    """I 240 triangoli dove li lascia scene_1, nel mondo: stessa griglia,
    stessa scala, rotazione identita', stesso materiale a fine esplosione
    (Look 1, Fade 1). Ognuno si rimpicciolisce fino a sparire, prima quelli
    vicini al centro della griglia."""
    face_img = KIT.load_image(m_scene.FACE_TEXTURE_FILE)
    uvs = m_scene.face_uvs(face_img, m_scene.FACE_TEXTURE_UV_PX, m_scene.FACE_TEXTURE_UV_INSET)
    mat = story.face_material(KIT, face_img, uvs)
    mat.node_tree.nodes["Look"].inputs["Fac"].default_value = 1.0
    mesh = m_scene.triangle_mesh(KIT, mat, uvs)
    tris = [m_scene.Tri(p) for p in pieces.m_pieces(md)]
    targets, world, scale = layout.grid(tris)
    centre = sum(world, Vector()) / len(world)
    far = max((w - centre).length for w in world)
    for tri, (loc, quat, s), w in zip(tris, targets, world):
        obj = KIT.new_object(f"tri_{tri.piece.index:03d}", mesh)
        obj.location = loc
        obj.rotation_mode = 'QUATERNION'
        obj.rotation_quaternion = quat
        obj.visible_shadow = False
        t0 = vanish_start((w - centre).length, far)
        f0, f1 = frame_of(t0), frame_of(t0 + VANISH_SECONDS)
        bl_anim.key_value(obj, "scale", [(f, (triangle_scale(time_of(f), t0, s),) * 3)
                                         for f in range(f0, f1 + 1)], interpolation='LINEAR')
        bl_anim.key_visibility(obj, [(FRAME_START, True), (f1 + 1, False)])
        tri.obj = obj
    return tris, world, scale, centre, far


def build_texture():
    img, uvs = textures.border_triangle(size=TEXTURE_SIZE, border=BORDER_DRAWN, dark=BORDER_DARK,
                                        margin=TEXTURE_MARGIN)
    image = m_scene.write_image(os.path.join(ASSETS_DIR, TEXTURE_FILE), img)
    return image, uvs


def plan(layout):
    """Dove sta ogni pezzo, in ogni fase: centri e raggi, nel mondo."""
    _, fh = layout.frame_size(0.0)
    fw, _ = layout.frame_size(0.0)
    centre = layout.screen_to_world(0.5, 0.5)
    right, up = Vector((1.0, 0.0, 0.0)), Vector((0.0, 0.0, 1.0))
    x_pair = PAIR_RADIUS + PAIR_GAP / 2.0
    x_out = fw / 2.0 + PAIR_RADIUS + OUT_MARGIN
    # la fila: [colonna larga 2r] gap [triangolo largo 2h] gap [triangolo largo 2h],
    # con h = r (INNER_RATIO cos 30 + 1) la mezza larghezza di un triangolo
    tri_half = INNER_RATIO * math.cos(math.radians(30.0)) + 1.0
    r = (WIDTH_FILL * fw - 2.0 * GROUP_GAP) / (2.0 + 4.0 * tri_half)
    h = r * tri_half
    left_x = -(h + GROUP_GAP + r)                      # dal centro del triangolo centrale
    right_x = h + GROUP_GAP + h
    shift = -((left_x - r) + (right_x + h)) / 2.0      # la fila centrata
    mid = centre + right * shift

    def on_circle(c, radius, angle_deg):
        a = math.radians(angle_deg)
        return c + right * (radius * math.cos(a)) + up * (radius * math.sin(a))

    column = {k: mid + right * left_x + up * (sign * (r + GROUP_GAP / 2.0))
              for k, sign in zip(LEFT_COLUMN, (1.0, -1.0))}
    right_c = mid + right * right_x
    return {
        "centre": centre, "piece_r": r, "x_out": x_out,
        "ico_pair": centre - right * x_pair, "m_pair": centre + right * x_pair,
        "trio": {k: on_circle(mid, INNER_RATIO * r, a) for k, a in TRIO_ANGLES.items()},
        "five": dict(column, **{k: on_circle(right_c, INNER_RATIO * r, a) for k, a in RIGHT_ANGLES.items()}),
    }


def position(key, t, P):
    """Dove sta il pezzo `key` all'istante t."""
    right = Vector((1.0, 0.0, 0.0))
    out = ease_in(ramp(t, T_SPLIT0, SPLIT_END))
    if key in ("M", "ico"):
        # la coppia, scalata attorno al centro mentre cresce
        pair = P["m_pair"] if key == "M" else P["ico_pair"]
        pair = P["centre"] + (pair - P["centre"]) * P["growth"].scale(t)
        sign = 1.0 if key == "M" else -1.0
        return pair + right * (sign * out * (P["x_out"] - sign * (pair - P["centre"]).x))
    if key in TRIO_ANGLES:
        start = {"ico_ring": P["centre"] + right * P["x_out"], "octa": P["centre"] - right * P["x_out"],
                 "tetra": P["centre"]}[key]
        u = ramp(t, TRIO_IN[key], TRIO_IN[key] + TRIO_SECONDS)
        u = ease_inout(u) if key == "tetra" else ease_out(u)
        return start.lerp(P["trio"][key], u)
    return P["five"][key]


def scale_keys(key, P):
    """(secondi, scala) del pezzo: comparire e' crescere da 0."""
    r = P["piece_r"]
    if key in ("M", "ico"):
        g = P["growth"]
        return [(time_of(f), PAIR_RADIUS * g.scale(time_of(f)))
                for f in range(frame_of(g.start), frame_of(g.start + PAIR_GROW) + 1)]
    if key == "tetra":
        return [(T_SPLIT0, 0.0), (SPLIT_END, r)]
    if key in ("octa", "ico_ring"):
        return [(TRIO_IN[key], r)]
    k = FIVE.index(key)
    t0 = FIVE_IN + k * FIVE_GAP
    return [(t0, 0.0), (t0 + GROW_SECONDS, r)]


def appear_time(key, P):
    start = P["growth"].start
    return {"ico": start, "M": start, "tetra": T_SPLIT0, "octa": TRIO_IN["octa"],
            "ico_ring": TRIO_IN["ico_ring"]}.get(
        key, FIVE_IN + FIVE.index(key) * FIVE_GAP if key in FIVE else 0.0)


def build():
    _check_schedule()
    KIT.clear_previous_run()
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.render.resolution_x, scene.render.resolution_y = RESOLUTION
    scene.frame_start, scene.frame_end = FRAME_START, FRAME_END
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    m_scene.use_cycles(scene)
    scene.cycles.transparent_max_bounces = 32        # le facce semitrasparenti
    KIT.new_collection(scene)

    md = extended_face.make_M()
    painting_img = KIT.load_image(story.PAINTING_FILE)       # serve solo per le sue proporzioni
    layout = story.Layout(md, painting_img.size)
    story.build_camera_and_world(KIT, layout, clip_end=story.CAMERA_DISTANCE + story.GRID_DEPTH + 30.0)

    tris, world, grid_scale, grid_centre, far = build_vanishing_triangles(layout, md)

    texture, uvs = build_texture()
    P = plan(layout)
    tri_radius = pieces.CIRCUMRADIUS                  # il triangolo canonico, lato 1
    P["growth"] = PairGrowth(layout, world, tri_radius, grid_scale, far, grid_centre, P)
    frames = list(range(FRAME_START, FRAME_END + 1))
    spin = 2.0 * math.pi / (SPIN_SECONDS_PER_TURN * FPS)      # radianti a fotogramma
    borders = []
    for n, key in enumerate(POLYHEDRA):
        if key in SKELETONS:
            obj = skeleton_objects(key, *polyhedron_geometry(key, md))
        else:
            mat = m_scene.tinted_texture_material(KIT, f"mat_{key}", texture, color(key), ROUGHNESS)
            mesh, fraction, k = polyhedron_mesh(key, md, mat, uvs, PAIR_RADIUS)
            borders.append(f"{key} {fraction:.2f} (x{k:.3f})")
            obj = KIT.new_object(key, mesh)
        obj.visible_shadow = False
        bl_anim.key_value(obj, "location", [(f, tuple(position(key, time_of(f), P))) for f in frames],
                          interpolation='LINEAR')
        bl_anim.key_value(obj, "scale", [(frame_of(t), (s,) * 3) for t, s in scale_keys(key, P)],
                          interpolation='LINEAR' if key in ("M", "ico") else 'BEZIER')
        # gira sempre, ognuno con la sua fase: due chiavi e una retta
        f0 = frame_of(appear_time(key, P))
        phase = 2.0 * math.pi * ((n * 0.618034) % 1.0)
        obj.rotation_mode = 'XYZ'
        bl_anim.key_value(obj, "rotation_euler",
                          [(f0, (0.0, 0.0, phase)),
                           (FRAME_END, (0.0, 0.0, phase + spin * (FRAME_END - f0)))],
                          interpolation='LINEAR')
        bl_anim.key_visibility(obj, [(FRAME_START, False), (f0, True)]
                               + ([(frame_of(SPLIT_END) + 1, False)] if key in ("M", "ico") else []))

    scene.frame_set(FRAME_START)
    print(f"[scene2b v3] frame {FRAME_START}-{FRAME_END} a {FPS} fps ({END_AT:.1f} s)")
    print(f"[scene2b v3] raccordo: camera in ({layout.eye.x:.3f}, {layout.eye.y:.1f}, {layout.eye.z:.3f}), "
          f"focale {layout.lens:.2f} mm, triangoli scalati a {grid_scale:.3f}")
    print(f"[scene2b v3] M e icosaedro di raggio {PAIR_RADIUS}, poi i pezzi di raggio {P['piece_r']:.3f} "
          f"(i triangoli di raggio {INNER_RATIO * P['piece_r']:.3f}), la fila larga {WIDTH_FILL:.0%} dell'immagine")
    g = P["growth"]
    print(f"[scene2b v3] la coppia cresce fra {g.start:.2f} e {g.start + PAIR_GROW:.2f} s; il primo "
          f"istante in cui c'e' posto per la coppia intera: "
          f"{min(time_of(f) for f, v in g.fit.items() if v >= 1.0):.2f} s")
    print(f"[scene2b v3] split {T_SPLIT0:.3f}-{SPLIT_END:.3f} s, trio {T_TRIO0:.3f}-{T_TRIO1:.3f} s")
    print(f"[scene2b v3] bordo largo {BORDER_WORLD} su M e l'icosaedro; in frazione dell'inraggio "
          f"delle facce (e ingrandimento del triangolo UV): " + ", ".join(borders))
    return tris


TRIS = build()
