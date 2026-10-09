"""
scene_3.py -- i deltaedri non convessi; poi la catena di tre tetraedri si
allunga, un tetraedro alla volta, nell'elica di Boerdijk-Coxeter, fino a
uscire dall'immagine.

--------------------------------------------------------------------------
LA SCALETTA (secondi)
--------------------------------------------------------------------------
 0 - 2.5  compaiono, uno dopo l'altro e in posizioni casuali, sei deltaedri
          non convessi: il composto di tre tetraedri in catena, esattamente
          al centro, e cinque deltaedri di Cundy fra quelli con meno facce
          (OTHERS). Girano lentamente.
 8        tutti i deltaedri, salvo il composto, escono di colpo
          dall'inquadratura, ognuno allontanandosi dal centro.
10        si incolla il primo tetraedro nuovo; poi altri, lentamente
          (SLOW_GAP).
16        il ritmo diventa piu' veloce: gli intervalli sono quelli che
          servono perche' l'ultimo tetraedro, quello che porta l'elica fuori
          dall'immagine, finisca TAIL_SECONDS prima della fine.
24        fine.

Ogni tetraedro nuovo esce dalla faccia a cui si attacca: la faccia resta
ferma e il quarto vertice si solleva fino al suo posto. La colonna sta in
verticale e cresce dalle due parti: i primi due tetraedri nuovi in alto, il
terzo in basso, poi alternando (il quarto in alto, il quinto in basso...),
cosi' resta centrata. Quando sta per toccare i bordi dell'immagine la si
rimpicciolisce, come se la camera indietreggiasse: alla fine sborda di
pochissimo (FILL_END). Intanto gira lentamente attorno al proprio asse. Il
composto parte ruotato di START_SPIN attorno all'asse, perche' la faccia a
cui si attacca il primo tetraedro sia ben visibile.

La costruzione e' quella di Creating_Helix.py (lo studente): il vertice nuovo
e' il riflesso, attraverso la faccia formata dagli ultimi tre, del vertice
che la precede. Mettendo sempre il tetraedro sull'ultima faccia si ottiene
l'elica di Boerdijk-Coxeter, che ha un asse dritto: e' quello che qui sta in
verticale, nel mezzo dell'immagine. In basso l'elica si prolunga allo stesso
modo all'indietro: il vertice nuovo e' il riflesso, attraverso i primi tre,
del quarto.

--------------------------------------------------------------------------
LE SCELTE
--------------------------------------------------------------------------
* Camera, fondo e luce sono quelli del racconto (libs/story.py).
* Il materiale e' quello di scene_2: la texture del triangolo col bordo scuro
  (textures.border_triangle), col bordo largo BORDER_WORLD. Tutti i solidi
  hanno lo stesso spigolo EDGE, quindi basta un solo triangolo UV. Il
  composto e' rosa chiarissimo e poco saturo; gli altri hanno la stessa
  luminosita' e saturazione, con tinte diverse.
* Il composto sta sul piano y = 0; gli altri piu' indietro, a profondita'
  casuali: a grandezza piena non ci starebbero tutti nell'inquadratura senza
  toccarsi. Le posizioni sono estratte con un seme fisso (SEED): ogni corsa
  da' la stessa scena. Non si sovrappongono nell'immagine e ci stanno dentro.
* Il composto gira attorno all'asse dell'elica, che passa a meno di un
  decimo di spigolo dal suo baricentro: il baricentro e' al centro
  dell'immagine all'inizio, e poi ci gira attorno di pochissimo.
* Ogni tetraedro e' un oggetto: le facce in comune fra due tetraedri restano
  dentro il solido e non si vedono, e quelle che si vedono sono proprio le
  facce del deltaedro.
* Niente ombre portate, come nelle altre scene.
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
        txt = bpy.data.texts.get("scene_3.py")
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
import geometry, bl_utils, extended_face, bl_anim, m_scene, story, textures, deltahedra
for _mod in (geometry, bl_utils, extended_face, bl_anim, m_scene, story, textures, deltahedra):
    importlib.reload(_mod)

from mathutils import Vector, Matrix, Quaternion


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

PREFIX          = "S3"
COLLECTION_NAME = "scene_3"

# saffaro/..., accanto al repository: src/libs -> src -> saffaro-delthedra -> saffaro
_SAFFARO   = os.path.dirname(os.path.dirname(os.path.dirname(_LIBS)))
ASSETS_DIR = os.path.join(_SAFFARO, "assets")
MODELS_DIR = os.path.join(_SAFFARO, "3dmodels", "cundy", "D2-Deltaedri di Cundy")

FPS         = story.FPS
RESOLUTION  = story.RESOLUTION
FRAME_START = 1

# --- la scaletta, in secondi ---
APPEAR_START      = 0.3          # il primo deltaedro comincia a comparire...
APPEAR_STAGGER    = 0.35         # ... e gli altri dopo, a questo intervallo
APPEAR_SECONDS    = 0.6          # quanto ci mette uno a comparire
EXIT_START        = 8.0          # gli altri escono di colpo
EXIT_SECONDS      = 0.45
GROW_START        = 10.0         # il primo tetraedro nuovo
SLOW_GAP          = 1.5          # fra i tetraedri nuovi, prima di FAST_START
SLOW_GROW_SECONDS = 0.6          # quanto ci mette un tetraedro a uscire, prima...
FAST_START        = 16.0         # ... e da qui in poi
FAST_GROW_SECONDS = 0.3
END               = 24.0
TAIL_SECONDS      = 1.5          # fra l'ultimo tetraedro e la fine
SPIN_SECONDS_PER_TURN  = 24.0    # il composto (e poi l'elica) attorno al proprio asse
OTHER_SECONDS_PER_TURN = 16.0    # gli altri deltaedri, attorno a un asse casuale

# --- la geometria e la posa ---
EDGE         = 1.3               # lo spigolo di tutti i solidi, nel mondo
N_NEW        = 25                # i tetraedri nuovi
# Il rimpicciolimento: l'altezza della torre in frazione di quella
# dell'immagine. Finche' sta sotto FILL_GROW la torre e' a grandezza piena;
# poi la si rimpicciolisce perche' ne occupi FILL_GROW, frazione che sale fino
# a FILL_END quando l'ultimo tetraedro ha finito di uscire (sopra 1 sborda).
# La scala si liscia con una media mobile di ZOOM_SMOOTH secondi, perche' la
# camera virtuale non segua gli scatti di ogni tetraedro.
FILL_GROW    = 0.85
FILL_END     = 1.05
ZOOM_SMOOTH  = 0.75
# gradi: la rotazione iniziale del composto attorno all'asse (verso l'alto,
# regola della mano destra). A -100 la faccia su cui si attacca il primo
# tetraedro, a 10 s, guarda la camera quasi al meglio possibile (-126 gradi):
# con la colonna in verticale non la si vede mai di fronte, perche' e'
# inclinata di 39 gradi sull'asse. A +100 si vedrebbe da dietro.
START_SPIN   = -100.0

# --- gli altri deltaedri: i cinque di Cundy con meno facce ---
# chiave -> (file, tinta OKLCH)
OTHERS = {
    "tetraug":  ("01_Tetraugmented_Tetrahedron.obj",  70.0),   # 12 facce, albicocca
    "gyraug":   ("04_Gyraugmented_Octahedron.obj",   150.0),   # 14, verde menta
    "digyraug": ("05_Digyraugmented_Octahedron.obj", 230.0),   # 20, azzurro
    "trisphen": ("23_Trispheniated_Octahedron.obj",  300.0),   # 20, lilla
    "stella":   ("06_Octaugmented_Octahedron.obj",   110.0),   # 24, giallo
}
SEED         = 3
DEPTH_RANGE  = (1.0, 7.0)        # profondita' (y) fra cui stanno gli altri
SCREEN_GAP   = 0.025             # distanza minima fra due solidi, in frazioni della larghezza
SCREEN_EDGE  = 0.02              # e dal bordo dell'immagine

# --- il materiale: come scene_2 ---
TEXTURE_FILE   = "face_border.png"
TEXTURE_SIZE   = 1024
TEXTURE_MARGIN = 0.10
BORDER_DARK    = 0.10
BORDER_DRAWN   = 0.04
BORDER_WORLD   = 0.022
# rosa chiarissimo, poco saturo (OKLCH); gli altri cambiano solo la tinta
COLOR_LCH      = (0.92, 0.035, 5.0)
ROUGHNESS      = 0.5


# =============================================================================
# L'ELICA
# =============================================================================

def helix_vertices(n, n_back):
    """I vertici dell'elica di Boerdijk-Coxeter, spigolo 1, da v[-n_back] a
    v[n-1]: si parte da un tetraedro regolare (v[0]..v[3]), e ogni vertice
    nuovo e' il riflesso del vertice di quattro posti prima attraverso il
    piano dei tre che lo seguono; all'indietro, di quello di quattro posti
    dopo attraverso i tre che lo precedono. Il tetraedro i-esimo e' (v[i],
    v[i+1], v[i+2], v[i+3]). Restituisce l'array e la posizione di v[0]."""
    def reflect(p, a, b, c):
        nrm = np.cross(b - a, c - a)
        nrm = nrm / np.linalg.norm(nrm)
        return p - 2.0 * np.dot(p - a, nrm) * nrm
    V = [np.array([0.0, 0.0, 0.0]), np.array([1.0, 0.0, 0.0]),
         np.array([0.5, math.sqrt(3) / 2, 0.0]),
         np.array([0.5, math.sqrt(3) / 6, math.sqrt(2.0 / 3.0)])]
    while len(V) < n:
        V.append(reflect(V[-4], V[-3], V[-2], V[-1]))
    for _ in range(n_back):
        V.insert(0, reflect(V[3], V[0], V[1], V[2]))
    return np.array(V), n_back


def helix_axis(V):
    """L'asse dell'elica: un punto e la direzione (versore), dalla direzione
    principale dei vertici. L'elica di Boerdijk-Coxeter ha l'asse dritto, e
    con abbastanza vertici la direzione principale e' quella; il verso e'
    quello in cui cresce."""
    c = V.mean(axis=0)
    _, _, vt = np.linalg.svd(V - c)
    d = vt[0]
    if np.dot(V[-1] - V[0], d) < 0:
        d = -d
    return c, d


# =============================================================================
# GLI ALTRI DELTAEDRI
# =============================================================================

def load_other(path):
    """Il deltaedro del file, coi vertici saldati, centrato e con lo spigolo
    EDGE: (vertici, facce, circonraggio)."""
    V, faces = deltahedra.load_welded(path)
    V = V * (EDGE / float(np.linalg.norm(V[faces[0][0]] - V[faces[0][1]])))
    return V, faces, float(np.linalg.norm(V, axis=1).max())


def place_others(layout, radii, centre_radius, rng):
    """Le posizioni nel mondo dei deltaedri di raggio `radii`: profondita' a
    caso in DEPTH_RANGE, e un punto a caso dell'immagine dove il solido ci sta
    tutto e non tocca gli altri ne' il composto (al centro, raggio
    `centre_radius` sul piano y = 0). Il confronto si fa nell'immagine, coi
    raggi proiettati, in frazioni della larghezza."""
    aspect = layout.rig.aspect
    w0, _ = layout.frame_size(0.0)
    placed = [(0.5, 0.5 / aspect, centre_radius / w0)] # (fx, fy in unita' della larghezza, raggio)
    out = []
    for r in radii:
        for _ in range(10000):
            y = rng.uniform(*DEPTH_RANGE)
            rho = r / layout.frame_size(y)[0]
            fx = rng.uniform(rho + SCREEN_EDGE, 1.0 - rho - SCREEN_EDGE)
            fy = rng.uniform(rho + SCREEN_EDGE, 1.0 / aspect - rho - SCREEN_EDGE)
            if all(math.hypot(fx - qx, fy - qy) > rho + qr + SCREEN_GAP for qx, qy, qr in placed):
                break
        else:
            raise ValueError("non trovo posto per tutti i deltaedri: allargare DEPTH_RANGE "
                             "o ridurre SCREEN_GAP")
        placed.append((fx, fy, rho))
        out.append(layout.screen_to_world(fx, fy * aspect, y))
    return out


def exit_distance(layout, location, radius):
    """Il versore (nel piano dell'immagine) che porta il solido via dal
    centro, e quanto deve spostarsi per uscire tutto dall'inquadratura."""
    w, h = layout.frame_size(location.y)
    d = Vector((location.x - layout.eye.x, 0.0, location.z - layout.eye.z))
    d = d.normalized() if d.length > 1e-6 else Vector((1.0, 0.0, 0.0))
    steps = []
    for k, half in ((0, w / 2.0), (2, h / 2.0)):
        if abs(d[k]) > 1e-6:
            rel = location[k] - (layout.eye.x if k == 0 else layout.eye.z)
            steps.append((half + radius - rel * math.copysign(1.0, d[k])) / abs(d[k]))
    return d, min(steps) * 1.05


# =============================================================================
# LA REGIA
# =============================================================================

def frame_of(t):
    return FRAME_START + int(round(t * FPS))


def growth_sequence(n):
    """Gli n tetraedri nuovi, in ordine: (indice i del tetraedro, in_alto). I
    primi due in alto, poi uno in basso e uno in alto alternati.

    In alto il tetraedro i = 3, 4, ... porta il vertice nuovo v[i+3]; in basso
    il tetraedro i = -1, -2, ... porta v[i]."""
    seq, top, bottom = [], 3, -1
    for k in range(n):
        go_up = k < 2 or not seq[-1][1]
        if go_up:
            seq.append((top, True))
            top += 1
        else:
            seq.append((bottom, False))
            bottom -= 1
    return seq


def grow_times(n_new):
    """(inizio, durata) della crescita di ciascuno degli n_new tetraedri
    nuovi: SLOW_GAP fino a FAST_START, poi gli intervalli uguali per cui
    l'ultimo finisce TAIL_SECONDS prima di END."""
    times = []
    t = GROW_START
    while t < FAST_START - 1e-9 and len(times) < n_new:
        times.append((t, SLOW_GROW_SECONDS))
        t += SLOW_GAP
    n_fast = n_new - len(times)
    if n_fast > 0:
        last = END - TAIL_SECONDS - FAST_GROW_SECONDS
        gap = (last - FAST_START) / max(1, n_fast - 1)
        if gap < 1.0 / FPS:
            raise ValueError(f"{n_fast} tetraedri non stanno fra {FAST_START} e {last:.2f} s")
        times += [(FAST_START + j * gap, FAST_GROW_SECONDS) for j in range(n_fast)]
    return times


def spin_keys(axis, seconds_per_turn, f0, f1):
    """Una chiave di quaternione per fotogramma: la rotazione attorno a un
    asse qualsiasi, a velocita' costante."""
    omega = 2.0 * math.pi / (seconds_per_turn * FPS)
    return [(f, tuple(Quaternion(axis, omega * (f - FRAME_START)))) for f in range(f0, f1 + 1)]


def appear_keys(t0, scale=1.0):
    """La comparsa: la scala da 0 a `scale`, con un attacco e un arrivo morbidi."""
    return [(frame_of(t0), (0.0, 0.0, 0.0)), (frame_of(t0 + APPEAR_SECONDS), (scale,) * 3)]


def appear_scale(f, keys):
    """La scala della comparsa al fotogramma f, da appear_keys: da 0 a 1 con
    attacco e arrivo morbidi (smoothstep)."""
    (f0, _), (f1, v1) = sorted(keys.items())
    u = min(1.0, max(0.0, (f - f0) / (f1 - f0)))
    return v1[0] * u * u * (3.0 - 2.0 * u)


def zoom_keys(compound, grown, frame_h, t_full, frame_end):
    """Per ogni fotogramma la scala della torre e lo spostamento verticale del
    perno che ne tiene al centro il punto di mezzo. L'altezza della torre si
    calcola dalle curve d'animazione dei tetraedri (la crescita in z), cosi'
    e' esatta anche per quelli a meta'. `grown` e' [(oggetto, quota della
    base, quota del vertice nuovo)] nel riferimento del perno."""
    curves = {}
    for obj, _, _ in grown:
        curves[obj.name] = next(fc for fc in bl_anim.action_fcurves(obj)
                                if fc.data_path == "scale" and fc.array_index == 2)
    z0 = [q[2] for q in compound]
    frames = list(range(FRAME_START, frame_end + 1))
    mids, raw = [], []
    for f in frames:
        t = (f - FRAME_START) / FPS
        zs = list(z0)
        for obj, zb, za in grown:
            u = curves[obj.name].evaluate(f)
            if u > 1e-6:
                zs.append(zb + (za - zb) * u)
        lo, hi = min(zs), max(zs)
        u = min(1.0, max(0.0, (t - GROW_START) / (t_full - GROW_START)))
        fill = FILL_GROW + (FILL_END - FILL_GROW) * u
        raw.append(min(1.0, fill * frame_h / (hi - lo)))
        mids.append((hi + lo) / 2.0)
    # media mobile, coi bordi tenuti fermi
    half = int(round(ZOOM_SMOOTH * FPS / 2.0))
    padded = [raw[0]] * half + raw + [raw[-1]] * half
    zoom = [sum(padded[k:k + 2 * half + 1]) / (2 * half + 1) for k in range(len(raw))]
    # il punto di mezzo della torre resta dov'era quello del composto
    shift = [mids[0] - z * m for z, m in zip(zoom, mids)]
    return zoom, shift


# =============================================================================
# COSTRUZIONE
# =============================================================================

KIT = m_scene.Kit(PREFIX, COLLECTION_NAME, ASSETS_DIR)


def tetra_mesh(name, base, apex, material, uvs):
    """La mesh di un tetraedro nel riferimento della sua faccia d'attacco:
    la faccia `base` sta nel piano z = 0 col baricentro nell'origine, il
    vertice `apex` sull'asse z positivo. Cosi' scalando l'oggetto in z da 0 a
    1 il tetraedro esce dalla faccia. Restituisce (mesh, matrice di posa)."""
    b = [Vector(p) for p in base]
    c = (b[0] + b[1] + b[2]) / 3.0
    z = (Vector(apex) - c).normalized()
    x = (b[0] - c).normalized()
    y = z.cross(x)
    R = Matrix((x, y, z)).transposed()          # colonne: gli assi locali
    pose = Matrix.Translation(c) @ R.to_4x4()
    inv = pose.inverted()
    verts = [inv @ p for p in b] + [inv @ Vector(apex)]
    # normali verso l'esterno: ogni faccia si gira se guarda verso il centro
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


def tinted(suffix, texture, hue):
    rgba, clipped = m_scene.oklch_to_linear(COLOR_LCH[0], COLOR_LCH[1], hue)
    if clipped:
        raise ValueError(f"il colore di {suffix} esce dal gamut sRGB")
    return m_scene.tinted_texture_material(KIT, suffix, texture, rgba, ROUGHNESS)


def build():
    KIT.clear_previous_run()
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.render.resolution_x, scene.render.resolution_y = RESOLUTION
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    KIT.new_collection(scene)
    frame_end = frame_of(END)
    scene.frame_start, scene.frame_end = FRAME_START, frame_end

    md = extended_face.make_M()
    painting_img = KIT.load_image(story.PAINTING_FILE)       # serve solo per le sue proporzioni
    layout = story.Layout(md, painting_img.size)
    story.build_camera_and_world(KIT, layout, clip_end=story.CAMERA_DISTANCE + 60.0)

    # --- i materiali: una texture, un triangolo UV, una tinta per solido ---
    img, base_uvs = textures.border_triangle(size=TEXTURE_SIZE, border=BORDER_DRAWN,
                                             dark=BORDER_DARK, margin=TEXTURE_MARGIN)
    texture = m_scene.write_image(os.path.join(ASSETS_DIR, TEXTURE_FILE), img)
    fraction = BORDER_WORLD / (EDGE * math.sqrt(3.0) / 6.0)
    uvs = textures.scaled_uvs(base_uvs, textures.border_scale(fraction, BORDER_DRAWN))
    mat = tinted("face", texture, COLOR_LCH[2])

    # --- l'elica: quanti tetraedri servono per uscire dall'immagine ---
    _, fh = layout.frame_size(0.0)
    centre_world = layout.screen_to_world(0.5, 0.5)
    V, o = helix_vertices(200, 200)
    V = V * EDGE
    centre, axis = helix_axis(V)
    # posa: il verso in cui cresce l'elica sull'asse x, poi START_SPIN attorno
    # all'asse, poi l'asse in verticale (x -> z, crescendo verso l'alto); il
    # baricentro del composto iniziale (v[0]..v[5]) al centro dell'immagine
    target_axis = Vector((0.0, 0.0, 1.0))
    R = (Matrix.Rotation(-math.pi / 2.0, 3, 'Y')
         @ Matrix.Rotation(math.radians(START_SPIN), 3, 'X')
         @ Vector(axis).rotation_difference(Vector((1.0, 0.0, 0.0))).to_matrix())
    first = np.asarray([R @ Vector(v) for v in V[o:o + 6]]).mean(axis=0)
    placed = np.asarray([R @ Vector(v) for v in V]) - first
    compound_radius = float(np.linalg.norm(placed[o:o + 6], axis=1).max())
    # il perno sta sull'asse dell'elica, nel punto piu' vicino al baricentro
    # del composto: girando attorno a lui l'elica gira su se stessa
    t_axis = np.asarray(target_axis)
    a0 = np.asarray(R @ Vector(centre)) - first
    on_axis = a0 - t_axis * np.dot(a0, t_axis)
    sequence = growth_sequence(N_NEW)
    times = grow_times(len(sequence))

    # --- l'ordine delle comparse: il composto e gli altri, a caso ---
    rng = np.random.default_rng(SEED)
    others = {key: load_other(os.path.join(MODELS_DIR, f)) for key, (f, _) in OTHERS.items()}
    order = ["compound"] + list(OTHERS)
    rng.shuffle(order)
    appear = {key: APPEAR_START + n * APPEAR_STAGGER for n, key in enumerate(order)}
    locations = dict(zip(OTHERS, place_others(layout, [others[k][2] for k in OTHERS],
                                              compound_radius, rng)))

    # --- il perno: compare, e gira attorno all'asse dell'elica ---
    pivot = KIT.new_object("pivot")
    pivot.location = centre_world + Vector(tuple(on_axis))
    pivot.empty_display_size = 0.5
    pivot.rotation_mode = 'QUATERNION'
    bl_anim.key_value(pivot, "rotation_quaternion",
                      spin_keys(target_axis, SPIN_SECONDS_PER_TURN, FRAME_START, frame_end),
                      interpolation='LINEAR')
    placed = placed - on_axis
    grown = []                  # (oggetto, quota del baricentro della base, quota del vertice nuovo)

    # --- i tetraedri: i primi tre sono il composto, gli altri escono dalla faccia ---
    for n, (i, up) in enumerate([(0, True), (1, True), (2, True)] + sequence):
        # il tetraedro i e' (v[i], v[i+1], v[i+2], v[i+3]). In alto la faccia
        # d'attacco, in comune col tetraedro i-1, e' (v[i], v[i+1], v[i+2]) e il
        # vertice nuovo e' v[i+3]; in basso la faccia e' quella in comune col
        # tetraedro i+1, (v[i+1], v[i+2], v[i+3]), e il vertice nuovo e' v[i]
        a, b, c, d = (placed[o + i + k] for k in range(4))
        name = f"tetra_{n:03d}"
        mesh, pose = (tetra_mesh(name, (a, b, c), d, mat, uvs) if up
                      else tetra_mesh(name, (b, c, d), a, mat, uvs))
        obj = KIT.new_object(name, mesh, parent=pivot)
        obj.matrix_parent_inverse = Matrix.Identity(4)
        loc, rot, _ = pose.decompose()
        obj.location = loc
        obj.rotation_mode = 'QUATERNION'
        obj.rotation_quaternion = rot
        obj.visible_shadow = False
        if n >= 3:
            t0, dt = times[n - 3]
            bl_anim.key_value(obj, "scale", [(frame_of(t0), (1.0, 1.0, 0.0)),
                                             (frame_of(t0 + dt), (1.0, 1.0, 1.0))])
            # a scala 0 starebbe sulla faccia del solido e la coprirebbe a chiazze:
            # compare dal fotogramma dopo, quando ha gia' uno spessore
            bl_anim.key_visibility(obj, [(FRAME_START, False), (frame_of(t0) + 1, True)])
            base, apex = ((a, b, c), d) if up else ((b, c, d), a)
            grown.append((obj, sum(q[2] for q in base) / 3.0, apex[2]))

    # --- il perno: compare, poi si rimpicciolisce e si ricentra ---
    zoom, shift = zoom_keys(placed[o:o + 6], grown, fh, times[-1][0] + times[-1][1], frame_end)
    start_scale = dict(appear_keys(appear["compound"]))
    bl_anim.key_value(pivot, "scale",
                      [(f, (appear_scale(f, start_scale) * z,) * 3)
                       for f, z in zip(range(FRAME_START, frame_end + 1), zoom)],
                      interpolation='LINEAR')
    bl_anim.key_value(pivot, "location",
                      [(f, tuple(pivot.location + Vector((0.0, 0.0, dz))))
                       for f, dz in zip(range(FRAME_START, frame_end + 1), shift)],
                      interpolation='LINEAR')

    # --- gli altri deltaedri: compaiono, girano, ed escono di colpo ---
    f_exit0, f_exit1 = frame_of(EXIT_START), frame_of(EXIT_START + EXIT_SECONDS)
    for key, (Vk, faces, radius) in others.items():
        mesh = bpy.data.meshes.new(KIT.name(key))
        mesh.from_pydata([tuple(v) for v in Vk], [], faces)
        bl_utils.set_triangle_uvs(mesh, uvs)
        mesh.materials.append(tinted(f"mat_{key}", texture, OTHERS[key][1]))
        mesh.update()
        obj = KIT.new_object(key, mesh)
        obj.visible_shadow = False
        loc = locations[key]
        obj.location = loc
        obj.rotation_mode = 'QUATERNION'
        spin_axis = Vector(tuple(rng.normal(size=3))).normalized()
        bl_anim.key_value(obj, "rotation_quaternion",
                          spin_keys(spin_axis, OTHER_SECONDS_PER_TURN, FRAME_START, f_exit1),
                          interpolation='LINEAR')
        bl_anim.key_value(obj, "scale", appear_keys(appear[key]))
        # l'uscita: un'accelerazione secca (u^2), una chiave per fotogramma
        direction, distance = exit_distance(layout, loc, radius)
        bl_anim.key_value(obj, "location",
                          [(f, tuple(loc + direction * distance * ((f - f_exit0) / (f_exit1 - f_exit0)) ** 2))
                           for f in range(f_exit0, f_exit1 + 1)], interpolation='LINEAR')
        bl_anim.key_visibility(obj, [(FRAME_START, True), (f_exit1 + 1, False)])

    scene.frame_set(FRAME_START)
    print(f"[scene_3] comparse: " + ", ".join(f"{k} {appear[k]:.2f}" for k in order))
    print(f"[scene_3] " + ", ".join(f"{k} ({len(others[k][1])} facce) y {locations[k].y:.1f}"
                                    for k in OTHERS))
    n_slow = sum(1 for t, _ in times if t < FAST_START)
    fast_gap = times[-1][0] - times[-2][0] if len(times) - n_slow > 1 else 0.0
    n_up = sum(1 for _, up in sequence if up)
    print(f"[scene_3] {len(sequence)} tetraedri nuovi ({n_up} in alto, {len(sequence) - n_up} in "
          f"basso; {n_slow} lenti, "
          f"{len(times) - n_slow} ogni {fast_gap:.3f} s); l'ultimo finisce a "
          f"{times[-1][0] + times[-1][1]:.2f} s; frame {FRAME_START}-{frame_end}")
    print(f"[scene_3] scala finale {zoom[-1]:.3f}; la torre ne esce alta {FILL_END:.2f} "
          f"volte l'immagine")
    print(f"[scene_3] spigolo {EDGE}, bordo {fraction:.2f} dell'inraggio; baricentro del "
          f"composto a {np.linalg.norm(on_axis):.3f} dall'asse")


build()
