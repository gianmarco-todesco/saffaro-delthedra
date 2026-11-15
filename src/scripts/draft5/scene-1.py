"""
draft5/scene-1.py -- M esce dal quadro, l'icosaedro e le sue 20 facce attorno a
M, e i 240 triangoli di M che migrano uno dopo l'altro nella griglia. Parte da
v4/scene-1; cambiano il movimento del quadro, i tempi e il bagliore.

--------------------------------------------------------------------------
LA SCALETTA (secondi, a 24 fps; m:ff = m secondi e ff fotogrammi)
--------------------------------------------------------------------------
   0 - 10:04  il quadro all'inizio riempie l'altezza dell'inquadratura, e
              fin dal primo fotogramma si allontana in linea retta, partendo
              da fermo e accelerando piano (ease-in): in 10 secondi fa tutto
              il tratto rettilineo. M c'e' gia', coi colori del quadro,
              subito dietro il quadro
  10:04 - 12:04  senza fermarsi il centro del quadro passa su un arco di cerchio
              raccordato con la retta (stessa direzione e stessa velocita'):
              continuando ad arretrare il quadro gira e va verso destra,
              sempre perpendicolare alla sua velocita'. Si ferma con un
              ease-out; poi non si muove piu'
  12:04 - 15:20  solo ora M si muove: buca il quadro e ne esce
              perpendicolare, con ease-in/ease-out, lentissimo (3,7 s); il
              contorno della sezione brilla d'oro. Finisce mezzo secondo
              dopo "giriamogli intorno"
  15:20       M e' al centro dell'immagine e comincia a girare su se stesso
              (ease-in); il quadro svanisce (15:20 - 17:08)
  16:20 - 23:22  M cresce molto lentamente (ease-in/ease-out) fino a
              GROW_FACTOR volte, e intanto scende al centro dell'immagine
  24:02       compaiono gli spigoli dell'icosaedro che contiene M (in un secondo)
  27:18       M e gli spigoli svaniscono, crescono le 20 facce (in un secondo)
  30:23       le facce svaniscono e M ricompare (in un secondo)
  35:03       i 240 triangoli cominciano a staccarsi e volano nella griglia:
              l'ultimo arriva a 39:15, quando la voce finisce
  40:15       fine: un secondo di pausa sulla griglia

I tempi seguono la voce del 2026-11-15 delle 13:21 (39,97 s): "Proviamo a
capire com'e' fatto!" finisce a 10,33; "Il quadro ce lo mostra da un solo
punto di vista:" 10,92 - 13,61; "giriamogli intorno." 13,94 - 15,30; "La sua
forma..." 15,74 - 20,09; "Con uno sguardo attento... dell'icosaedro," 20,52 -
25,62; "il solido platonico... equilateri." 25,92 - 29,51; "Anche M..."
31,23 - 39,63.

--------------------------------------------------------------------------
IL MOVIMENTO DEL QUADRO (PaintingPath)
--------------------------------------------------------------------------
* La camera non si muove: e' quella finale di v4/scene-1 (story.ExitView,
  eye1), da cui v4/scene-2 e v5/scene-2 ripartono. In v4 era la camera ad
  arretrare; qui arretra il quadro.
* Il percorso del centro del quadro: una retta lungo l'asse della camera,
  cosi' il quadro resta perfettamente centrato nell'inquadratura mentre si
  allontana (al primo fotogramma ne riempie esattamente l'altezza), poi un
  arco di cerchio orizzontale tangente alla retta, che gira di
  PAINT_TILT gradi verso destra. Il quadro e' sempre perpendicolare alla
  tangente. La legge oraria e' sulla strada fatta lungo tutto il percorso
  (retta + arco), in due tempi (PaintingPath.distance): da DRIFT_FROM a
  PAINT_MOVE il quadro parte da fermo e accelera piano, in modo uniforme,
  facendo DRIFT_PART della retta; da PAINT_MOVE a PAINT_STOP un raccordo
  cubico lo porta alla fine dell'arco, dove si ferma. La velocita' e'
  continua dappertutto, anche dove la retta diventa arco.
* M sta attaccato al quadro esattamente dietro il poliedro dipinto: il suo
  centro e' sulla perpendicolare al quadro che passa per il centro del
  disegno (lo scarto u = m_start - painting_centre di ExitView). Ne esce
  lungo quella perpendicolare.
* La posa finale del quadro e' determinata da M: M ne esce lungo la
  perpendicolare di exit_distance e deve finire al centro dell'immagine in
  orizzontale, alla profondita' di m_end (m_target). In verticale non si
  puo' scegliere: il quadro gira attorno alla verticale, quindi M finisce
  alto quanto il disegno sta sopra il centro del quadro (lift). Lo si
  riporta in m_end mentre cresce (GROW), insieme alla scala, cosi' lo
  spostamento non si vede; da li' in poi la scena e' quella di prima.
  Allontanando M di
  piu' dal quadro (PAINT_EXTRA), il quadro finisce piu' a destra e piu'
  lontano. PAINT_EXTRA = None: lo script cerca il minimo per cui, alla fine,
  la sagoma di M (il cilindro verticale che lo contiene, per il giro su se
  stesso) e quella del quadro, viste dalla camera, sono staccate di
  PAINT_CLEAR della larghezza dell'immagine (calibrate_extra). Il raggio
  dell'arco e il punto in cui comincia vengono di conseguenza.
* Con 60 gradi, come in v4, servirebbe un arco cosi' grande che dovrebbe
  cominciare piu' vicino alla camera del punto da cui il quadro parte:
  niente tratto rettilineo. Per questo l'angolo lo sceglie lo script
  (PAINT_TILT = None): il minimo che lascia PAINT_MIN_STRAIGHT di retta.
  Il quadro parte alla distanza a cui lo vedeva la camera iniziale di v4.
* La crescita di M (GROW, GROW_FACTOR) e' la scala del perno `mover`:
  crescono con lui l'icosaedro e le sue facce. I triangoli partono per la
  griglia da M cresciuto; la griglia e' quella di sempre, quindi il raccordo
  con la scena 2 non cambia.

--------------------------------------------------------------------------
LE SCELTE (da v4/scene-1, dove valgono ancora)
--------------------------------------------------------------------------
* M esiste solo davanti al quadro: nel materiale, la parte che sta dietro il
  piano del quadro (nelle coordinate del quadro, y > 0) e' trasparente.
  Visto da davanti non cambia niente, e M non spunta dai bordi del quadro:
  ne esce dalla superficie. La linea della sezione si
  calcola a ogni fotogramma nel riferimento del quadro
  (deltahedra.plane_section) ed e' un tubicino sottile (LINE_RADIUS) di luce
  dorata. L'emissione resta debole (LINE_STRENGTH), perche' un'emissione
  forte satura anche i pixel coperti in parte e la linea si vede a gradini;
  il bagliore lo fa il compositor da un passaggio AOV che scrive solo il
  materiale della linea (m_scene.setup_aov_glow): un alone stretto e forte
  (GLOW_SOFTEN) che sfuma il bordo della linea, piu' un bloom largo.
* M resta coi colori del quadro (Look 0) per tutta la scena.
* M, gli spigoli e le facce sono figli dello stesso perno (mover -> orient,
  come in v2/scene-1): girano insieme, fermi l'uno rispetto all'altro. Le
  facce scalano attorno al loro baricentro.
* I 240 triangoli: dal momento in cui sostituiscono M fino alla partenza
  seguono M fotogramma per fotogramma, poi volano: si staccano lungo la loro
  normale e, con una curva senza spigoli, vanno alla loro cella
  (POP_DISTANCE, ARRIVAL_PULL come in v2/scene-1). Partono prima i piu'
  vicini alla camera e i piu' frontali (la faccia perpendicolare alla linea
  di vista), con la posa di M all'inizio di MIGRATE: si veda
  departure_order. Il k-esimo parte a MIGRATE[0] + D sqrt(k/240): il numero
  di quelli partiti cresce come il quadrato del tempo, pochi all'inizio e
  sempre di piu'; D e' tale che l'ultimo arrivi alla fine di MIGRATE.
* La griglia: story.GRID (20 gruppi, uno per faccia estesa di M, da 4 x 3),
  su un piano perpendicolare all'asse della camera, story.EXIT_GRID_BEHIND
  piu' lontano del centro di M, larga GRID_FILL dell'inquadratura. Il
  materiale dei triangoli e' quello di M senza il taglio.
* Il motore e' Cycles, a 256 campioni (m_scene.use_cycles).

Una sola scena, tutto in keyframe (nessun handler), script idempotente, nomi
col prefisso S1D5_.
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
        txt = bpy.data.texts.get("scene-1.py")
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
import geometry, bl_utils, extended_face, pieces, bl_anim, m_scene, story, deltahedra
for _mod in (geometry, bl_utils, extended_face, pieces, bl_anim, m_scene, story, deltahedra):
    importlib.reload(_mod)

from mathutils import Vector, Matrix
from bl_anim import Key


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

PREFIX          = "S1D5"
COLLECTION_NAME = "scene-1_draft5"

# saffaro/assets, accanto al repository: src/libs -> src -> saffaro-delthedra -> saffaro
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(_LIBS))), "assets")

FPS         = story.FPS
RESOLUTION  = story.RESOLUTION
FRAME_START = 1

def tc(seconds, frames=0):
    """Un tempo scritto come nel montaggio: secondi e fotogrammi."""
    return seconds + frames / story.FPS


# --- la scaletta, in secondi ---
DRIFT_FROM    = tc(0, 0)         # il quadro comincia ad allontanarsi, piano (ease-in)...
DRIFT_PART    = 1.0              # ... e prima di PAINT_MOVE fa tanta parte della retta
PAINT_MOVE    = tc(10, 4)        # il quadro accelera e gira...
PAINT_STOP    = tc(12, 4)        # ... e si ferma (ease-out)
EXIT_AT       = PAINT_STOP       # solo allora M comincia a uscire (ease-in/ease-out)...
EXIT_END      = tc(15, 20)       # ... ed e' al centro dell'immagine: mezzo secondo dopo "giriamogli intorno"
SPIN_AT       = EXIT_END         # M comincia a girare...
SPIN_RAMP     = 1.5              # ... arrivando alla sua velocita' in tanto (ease-in)
SPIN_SECONDS_PER_TURN = 20.0
PAINT_FADE    = (EXIT_END, EXIT_END + 1.5)   # il quadro svanisce
GROW          = (tc(16, 20), tc(23, 22))     # M cresce, molto lentamente (ease-in/ease-out)...
GROW_FACTOR   = 1.25                         # ... fino a tante volte (1 = non cresce)
SKELETON_IN   = (tc(24, 2), tc(25, 2))       # gli spigoli dell'icosaedro compaiono
FACES_IN      = (tc(27, 18), tc(28, 18))     # M e gli spigoli svaniscono, le facce crescono
FACES_OUT     = (tc(30, 23), tc(31, 23))     # le facce svaniscono, M ricompare
MIGRATE       = (tc(35, 3), tc(39, 15))      # i triangoli migrano: l'ultimo arriva quando la voce finisce
FLY_SECONDS   = 1.2              # quanto dura il volo di un triangolo
END           = tc(39, 15)                   # un secondo dopo la fine della voce

# --- il movimento del quadro (si veda PaintingPath) ---
PAINT_TILT    = None             # gradi: di quanto gira il quadro sull'arco; None = il minimo
                                 # (da 60, a passi di un grado) che lascia PAINT_MIN_STRAIGHT di retta
PAINT_MIN_STRAIGHT = 0.6         # il tratto rettilineo e' almeno tanto lungo
PAINT_EXTRA   = None             # di quanto M si allontana dal quadro piu' che in v4; None = il minimo
PAINT_CLEAR   = 0.02             # ... perche' le due sagome restino tanto staccate (frazione della larghezza)

# --- il contorno della sezione ---
GLOW_COLOR      = (1.0, 0.78, 0.35)
LINE_RADIUS     = 0.004          # il tubicino della linea: sottile (v4: 0.01, circa 4 pixel)
LINE_STRENGTH   = 1.0            # l'emissione (v4: 0.3); la luce la fa soprattutto il compositor
GLOW_AOV        = "glow"         # il passaggio da cui il compositor fa il bagliore
GLOW_GAIN       = 100.0          # quanto la linea scrive nel passaggio (v4: 14)
GLARE_STRENGTH  = 2.0            # il bloom largo (v4: 0.4)
GLARE_SIZE      = 0.8
GLOW_SOFTEN     = 3.0            # pixel: l'alone stretto attorno alla linea (v4: 8).
GLOW_SOFTEN_WEIGHT = 0.3         # ... e quanto conta (v4: 0.2)

# --- l'icosaedro (in unita' di M) ---
SKELETON_HUE      = 100.0        # gli spigoli: giallo pastello
SKELETON_RADIUS   = 0.04         # cilindretti e sferette degli spigoli
FACE_HUE          = 35.0         # le facce: corallo pastello
FACE_SCALE        = 0.85         # attorno al baricentro: fra le facce restano spazi ben visibili
FACE_OPACITY      = 0.35         # i triangoli delle facce
FACE_TUBE_RADIUS  = 0.025        # i lati e i vertici delle facce

# --- la migrazione ---
POP_DISTANCE    = 1.0            # quanto si allontana lungo la normale, prima di girare
ARRIVAL_PULL    = 0.4            # quanto l'arrivo tiene della direzione di partenza
FRONTAL_WEIGHT  = 0.5            # quanto conta, nell'ordine di partenza, essere frontali


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


def smootherstep(x, x0, x1):
    return smoother(ramp(x, x0, x1))


def spin_angles(frames):
    """{frame: angolo}: da SPIN_AT la velocita' sale da zero con un raccordo
    dolce in SPIN_RAMP secondi, poi resta costante; integrata fotogramma per
    fotogramma."""
    omega = 2.0 * math.pi / SPIN_SECONDS_PER_TURN
    out, a = {}, 0.0
    for f in frames:
        out[f] = a
        a += omega * smootherstep(time_of(f) + 0.5 / FPS, SPIN_AT, SPIN_AT + SPIN_RAMP) / FPS
    return out


def grow_at(t):
    """Di quanto M e' cresciuto all'istante t (1 prima di GROW, GROW_FACTOR
    dopo)."""
    return 1.0 + (GROW_FACTOR - 1.0) * smootherstep(t, GROW[0], GROW[1])


def departure_order(centres, normals, eye):
    """L'ordine di partenza: prima i triangoli vicini alla camera e frontali.
    Il punteggio e' la distanza dalla camera, riportata fra 0 (il piu' vicino)
    e 1 (il piu' lontano), piu' FRONTAL_WEIGHT volte (1 - c), con c il coseno
    fra la normale e la direzione verso la camera: 1 se la faccia la guarda
    in pieno, -1 se le volta le spalle. A pari punteggio decide l'indice."""
    d = np.array([np.linalg.norm(c - eye) for c in centres])
    d = (d - d.min()) / (d.max() - d.min())
    facing = np.array([float(n @ ((eye - c) / np.linalg.norm(eye - c))) for c, n in zip(centres, normals)])
    score = d + FRONTAL_WEIGHT * (1.0 - facing)
    return sorted(range(len(centres)), key=lambda i: (round(float(score[i]), 9), i))


def departure_times(order):
    """Il k-esimo dell'ordine parte a MIGRATE[0] + D sqrt(k / (n - 1)), con D
    tale che l'ultimo arrivi alla fine di MIGRATE. Restituisce i tempi per
    indice."""
    n = len(order)
    D = (MIGRATE[1] - MIGRATE[0]) - FLY_SECONDS
    times = np.empty(n)
    for k, i in enumerate(order):
        times[i] = MIGRATE[0] + D * math.sqrt(k / (n - 1))
    return times


def bezier(p0, p1, p2, p3, u):
    v = 1.0 - u
    return p0 * v ** 3 + p1 * (3 * v * v * u) + p2 * (3 * v * u * u) + p3 * u ** 3


# =============================================================================
# IL CONTORNO DELLA SEZIONE
# =============================================================================

KIT = m_scene.Kit(PREFIX, COLLECTION_NAME, ASSETS_DIR)


def add_section_cut(mat, painting):
    """Rende trasparente, nel materiale, tutto quello che sta dietro il
    quadro: nelle coordinate dell'oggetto `painting` (il quadro sta nel suo
    piano y = 0, e la camera dalla parte delle y negative), y > 0. Segue il
    quadro mentre gira e arretra."""
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    out = next(n for n in nodes if n.type == 'OUTPUT_MATERIAL')
    surface = out.inputs["Surface"].links[0].from_socket
    coords = nodes.new("ShaderNodeTexCoord")
    coords.object = painting
    sep = nodes.new("ShaderNodeSeparateXYZ")
    links.new(coords.outputs["Object"], sep.inputs[0])
    behind = nodes.new("ShaderNodeMath")
    behind.operation = 'GREATER_THAN'
    links.new(sep.outputs["Y"], behind.inputs[0])
    behind.inputs[1].default_value = 0.0
    clear = nodes.new("ShaderNodeBsdfTransparent")
    cut = nodes.new("ShaderNodeMixShader")
    links.new(behind.outputs[0], cut.inputs["Fac"])
    links.new(surface, cut.inputs[1])
    links.new(clear.outputs["BSDF"], cut.inputs[2])
    links.new(cut.outputs["Shader"], out.inputs["Surface"])


def line_material():
    mat, nodes, links = KIT.new_material("section")
    out = nodes.new("ShaderNodeOutputMaterial")
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = tuple(GLOW_COLOR) + (1.0,)
    emit.inputs["Strength"].default_value = LINE_STRENGTH
    links.new(emit.outputs["Emission"], out.inputs["Surface"])
    aov = nodes.new("ShaderNodeOutputAOV")
    aov.aov_name = GLOW_AOV
    aov.inputs["Color"].default_value = tuple(c * GLOW_GAIN for c in GLOW_COLOR) + (1.0,)
    mat.diffuse_color = tuple(GLOW_COLOR) + (1.0,)
    return mat


def build_section_lines(md, m_world, painting_world, frames):
    """Le linee della sezione: per ogni fotogramma in cui il piano del quadro
    taglia M, un oggetto curva coi tubicini delle curve chiuse, visibile solo
    in quel fotogramma. La sezione si calcola nel riferimento del quadro (il
    suo piano e' y = 0) e si riporta nel mondo. m_world(f) e painting_world(f)
    sono le matrici mondo di M e del quadro. Restituisce i fotogrammi che ne
    hanno una."""
    mat = line_material()
    V = np.asarray(md.vertices, dtype=float)
    Vh = np.c_[V, np.ones(len(V))]
    out = []
    for f in frames:
        Mp = painting_world(f)
        local = (np.asarray(Mp.inverted() @ m_world(f)) @ Vh.T).T[:, :3]
        loops = deltahedra.plane_section(local, md.faces, axis=1, value=0.0)
        if not loops:
            continue
        name = f"section_{f:04d}"
        curve = bpy.data.curves.new(KIT.name(name), 'CURVE')
        curve.dimensions = '3D'
        curve.bevel_depth = LINE_RADIUS
        curve.bevel_resolution = 2
        curve.fill_mode = 'FULL'
        for loop in loops:
            spline = curve.splines.new('POLY')
            spline.points.add(len(loop) - 1)
            for point, q in zip(spline.points, loop):
                w = Mp @ Vector(q)
                point.co = (w.x, w.y, w.z, 1.0)
            spline.use_cyclic_u = True
        curve.materials.append(mat)
        obj = KIT.new_object(name, curve)
        m_scene.hide_from_light(obj)
        bl_anim.key_visibility(obj, [(FRAME_START, False), (f, True), (f + 1, False)])
        out.append(f)
    return out


# =============================================================================
# L'ICOSAEDRO: GLI SPIGOLI E LE 20 FACCE
# =============================================================================

def fade(mat, keys):
    """Keyframe del nodo 'Fade' del materiale: (secondi, valore)."""
    bl_anim.key_value(mat.node_tree, m_scene.FADE_PATH, [(frame_of(t), v) for t, v in keys])


def visible_between(obj, t0, t1):
    bl_anim.key_visibility(obj, [(FRAME_START, False), (frame_of(t0), True), (frame_of(t1) + 1, False)])


def build_icosahedron(orient, md):
    """Gli spigoli e le 20 facce dell'icosaedro-gabbia di M, figli di orient:
    girano con M. Ogni faccia e' un triangolo semitrasparente (l'oggetto, che
    scala attorno al suo baricentro) con un figlio: i tubicini dei lati e le
    sferette dei vertici."""
    ico = geometry.Polyhedron.ico
    scale = geometry.enclosing_scale(md.vertices, ico) * story.ICO_MARGIN
    V = [np.asarray(v.tup()) * scale for v in ico.vertices]
    edges = sorted({tuple(sorted((f[k], f[(k + 1) % 3]))) for f in ico.faces for k in range(3)})

    yellow = m_scene.fading_material(KIT, "skeleton", story.pastel(SKELETON_HUE), roughness=0.4)
    skeleton = KIT.new_object("skeleton", m_scene.skeleton_mesh(KIT, "skeleton", V, edges,
                                                                SKELETON_RADIUS, yellow), parent=orient)
    skeleton.visible_shadow = False
    fade(yellow, [(SKELETON_IN[0], 0.0), (SKELETON_IN[1], 1.0), (FACES_IN[0], 1.0), (FACES_IN[1], 0.0)])
    visible_between(skeleton, SKELETON_IN[0], FACES_IN[1])

    coral = story.pastel(FACE_HUE)
    glass = m_scene.fading_material(KIT, "ico_faces", coral, roughness=0.4)
    fade(glass, [(FACES_IN[0], FACE_OPACITY), (FACES_OUT[0], FACE_OPACITY), (FACES_OUT[1], 0.0)])
    rims = m_scene.fading_material(KIT, "ico_rims", coral, roughness=0.35)
    fade(rims, [(FACES_IN[0], 1.0), (FACES_OUT[0], 1.0), (FACES_OUT[1], 0.0)])
    for n, f in enumerate(ico.faces):
        c = sum(V[i] for i in f) / 3.0
        local = [tuple(V[i] - c) for i in f]
        mesh = bpy.data.meshes.new(KIT.name(f"ico_face_{n:02d}"))
        mesh.from_pydata(local, [], [(0, 1, 2)])
        mesh.materials.append(glass)
        obj = KIT.new_object(f"ico_face_{n:02d}", mesh, parent=orient)
        obj.location = tuple(c)
        obj.visible_shadow = False
        rim = KIT.new_object(f"ico_face_{n:02d}_rim",
                             m_scene.skeleton_mesh(KIT, f"ico_face_{n:02d}_rim", local,
                                                   [(0, 1), (1, 2), (0, 2)], FACE_TUBE_RADIUS, rims),
                             parent=obj)
        rim.visible_shadow = False
        bl_anim.key_value(obj, "scale", [(frame_of(FACES_IN[0]), (0.0,) * 3),
                                         (frame_of(FACES_IN[1]), (FACE_SCALE,) * 3)])
        visible_between(obj, FACES_IN[0], FACES_OUT[1])
    return scale


# =============================================================================
# LA MIGRAZIONE
# =============================================================================

def migration_keys(tri, world_of, normal_of, depart, target, frames):
    """Le chiavi del triangolo, una per fotogramma da MIGRATE[0]: prima segue
    M (world_of(f) e' la sua matrice mondo), poi vola alla cella. Il volo e'
    una Bezier cubica: parte lungo la normale, arriva sulla cella tenendo un
    po' della direzione di partenza; rotazione e scala seguono lo stesso
    parametro, con un raccordo dolce."""
    loc_t, quat_t, scale_t = target
    f_dep = frame_of(depart)
    local = Matrix.Translation(tri.loc) @ tri.quat.to_matrix().to_4x4()
    p0, q0, s0 = (world_of(f_dep) @ local).decompose()
    p1 = p0 + normal_of(f_dep) * POP_DISTANCE
    p3 = Vector(loc_t)
    p2 = p3 + (p1 - p3) * ARRIVAL_PULL
    keys = []
    for f in frames:
        if f <= f_dep:
            loc, quat, sc = (world_of(f) @ local).decompose()
            keys.append(Key(f, loc, quat, sc.x))
        else:
            u = smoother(ramp(time_of(f), depart, depart + FLY_SECONDS))
            keys.append(Key(f, bezier(p0, p1, p2, p3, u), q0.slerp(quat_t, u), s0.x + (scale_t - s0.x) * u))
    return keys


# =============================================================================
# IL MOVIMENTO DEL QUADRO
# =============================================================================

def _rz(angle):
    """Rotazione attorno a z, come matrice 3x3 numpy (angolo positivo =
    antiorario visto dall'alto)."""
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def hermite(t, t0, t1, s0, s1, v0, v1):
    """Il raccordo cubico fra (t0, s0) con velocita' v0 e (t1, s1) con
    velocita' v1."""
    h = t1 - t0
    u = (t - t0) / h
    return (s0 * (2 * u ** 3 - 3 * u ** 2 + 1) + h * v0 * (u ** 3 - 2 * u ** 2 + u)
            + s1 * (-2 * u ** 3 + 3 * u ** 2) + h * v1 * (u ** 3 - u ** 2))


class PaintingPath:
    """Il quadro che arretra in linea retta e poi, sull'arco, gira verso
    destra; e M, che gli sta attaccato e ne esce perpendicolare.

    Il centro del quadro sta sempre nel piano orizzontale dell'asse della
    camera, e sulla retta e' sull'asse stesso. Tutto il resto e' determinato
    dalla fine: M deve finire in m_target (al centro dell'immagine in
    orizzontale, alla profondita' di m_end), dopo essere uscito di d =
    exit_distance + extra lungo la perpendicolare del quadro girato di
    `tilt`. Da li' viene la posa finale del quadro; il raggio dell'arco e'
    quello per cui l'arco, tangente all'asse della camera, ci arriva girando
    di `tilt`."""

    def __init__(self, ev, tilt_deg, extra):
        self.ev = ev
        self.a = a = math.radians(tilt_deg)
        self.extra = extra
        c = np.asarray(ev.painting_centre, dtype=float)
        eye = np.asarray(ev.eye1, dtype=float)
        # M rispetto al quadro: dietro il centro del disegno, che non e' il
        # centro del quadro
        self.u = u = np.asarray(ev.m_start, dtype=float) - c
        self.d = d = ev.exit_distance + extra
        # dove M finisce di uscire: al centro dell'immagine in orizzontale,
        # alla profondita' di m_end; in verticale dove lo porta il quadro.
        # lift e' quanto lo si abbassa poi, mentre cresce, per portarlo in m_end
        m_end = np.asarray(ev.m_end, dtype=float)
        self.m_target = np.array([eye[0], m_end[1], eye[2] + u[2]])
        self.lift = self.m_target - m_end
        R = _rz(-a)                                              # in senso orario
        self.end = end = self.m_target - R @ (u + np.array([0.0, -d, 0.0]))
        self.r = r = (end[0] - eye[0]) / (1.0 - math.cos(a))
        self.arc_start = np.array([eye[0], end[1] - r * math.sin(a), eye[2]])
        self.pivot = self.arc_start + np.array([r, 0.0, 0.0])
        # all'inizio il quadro sta sull'asse della camera, alla distanza a cui
        # lo vedeva la camera iniziale di v4 (eye0): ne riempie l'altezza
        depth0 = float(c[1] - ev.eye0[1])
        self.start = np.array([eye[0], eye[1] + depth0, eye[2]])
        self.straight = float(self.arc_start[1] - self.start[1])
        self.arc = r * a
        # la legge oraria (si veda distance): quanta strada ha fatto a
        # PAINT_MOVE, e a che velocita' ci arriva
        self.drift = DRIFT_PART * self.straight
        self.drift_speed = 2.0 * self.drift / (PAINT_MOVE - DRIFT_FROM)
        # il raccordo cubico che segue non torna indietro se la velocita' di
        # partenza non supera tre volte quella media
        mean = (self.straight + self.arc - self.drift) / (PAINT_STOP - PAINT_MOVE)
        if self.drift_speed > 3.0 * mean:
            raise ValueError("il quadro arriva a PAINT_MOVE troppo veloce: ridurre DRIFT_PART")

    def distance(self, t):
        """La strada fatta dal quadro all'istante t: fino a PAINT_MOVE parte
        da fermo e accelera in modo uniforme (la strada cresce col quadrato
        del tempo), poi un raccordo cubico con la stessa velocita' lo porta
        alla fine del percorso, dove si ferma."""
        if t <= PAINT_MOVE:
            u = ramp(t, DRIFT_FROM, PAINT_MOVE)
            return self.drift * u * u
        return hermite(min(t, PAINT_STOP), PAINT_MOVE, PAINT_STOP,
                       self.drift, self.straight + self.arc, self.drift_speed, 0.0)

    def pose(self, t):
        """(centro, angolo) del quadro: l'angolo e' quanto ha girato, in senso
        orario visto dall'alto (0 = di fronte alla camera)."""
        s = self.distance(t)
        if s <= self.straight:
            return self.start + np.array([0.0, s, 0.0]), 0.0
        theta = (s - self.straight) / self.r
        return self.pivot + _rz(-theta) @ (self.arc_start - self.pivot), theta

    def painting_matrix(self, t):
        centre, theta = self.pose(t)
        return Matrix.Translation(Vector(tuple(centre))) @ Matrix.Rotation(-theta, 4, 'Z')

    def exit_fraction(self, t):
        """Quanto M e' uscito (0 = all'inizio, 1 = in m_target): ease-in/ease-out
        fra EXIT_AT (il quadro e' gia' fermo) ed EXIT_END."""
        return smootherstep(t, EXIT_AT, EXIT_END)

    def emerged_time(self):
        """Quando M e' tutto fuori dal quadro."""
        e, t = self.emerged_fraction(), EXIT_AT
        while self.exit_fraction(t) < e:
            t += 1.0 / FPS
        return t

    def emerged_fraction(self):
        """La frazione di uscita a cui il punto di M piu' indietro (nel
        riferimento del quadro, la y piu' grande) passa il piano del quadro."""
        back = float(self.u[1] + self.ev.s0 * np.asarray(self.ev.P)[:, 1].max())
        return back / self.d

    def m_matrix(self, t):
        """La matrice mondo del centro di M (senza scala e senza il suo giro)."""
        local = self.u + np.array([0.0, -self.d * self.exit_fraction(t), 0.0])
        return self.painting_matrix(t) @ Matrix.Translation(Vector(tuple(local)))


def _hull(points):
    """L'inviluppo convesso di punti 2D (catena monotona)."""
    pts = sorted(set((round(float(x), 9), round(float(y), 9)) for x, y in points))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _gap(a, b):
    """La distanza fra due poligoni convessi (assi separatori): positiva se
    sono staccati, negativa se si sovrappongono."""
    best = -math.inf
    for poly in (a, b):
        for p, q in zip(poly, poly[1:] + poly[:1]):
            n = np.array([q[1] - p[1], p[0] - q[0]])
            n = n / np.linalg.norm(n)
            pa = [float(np.dot(n, v)) for v in a]
            pb = [float(np.dot(n, v)) for v in b]
            best = max(best, min(pb) - max(pa), min(pa) - max(pb))
    return best


def silhouette_gap(ev, path):
    """Quanto sono staccate, alla fine, la sagoma di M (il cilindro verticale
    che lo contiene, comunque giri) e quella del quadro, viste dalla camera:
    in frazione della larghezza dell'immagine."""
    eye = np.asarray(ev.eye1, dtype=float)

    def project(p):
        v = np.asarray(p, dtype=float) - eye
        return (v[0] / v[1], v[2] / v[1])

    P = np.asarray(ev.P) * ev.s0
    radius = float(np.linalg.norm(P[:, :2], axis=1).max())
    zs = (float(P[:, 2].min()), float(P[:, 2].max()))
    c = path.m_target
    m = _hull([project(c + np.array([radius * math.cos(a), radius * math.sin(a), z]))
               for a in np.linspace(0.0, 2.0 * math.pi, 72, endpoint=False) for z in zs])
    M = path.painting_matrix(PAINT_STOP)
    w, h = ev.layout.painting_width / 2.0, ev.layout.painting_height / 2.0
    q = _hull([project(M @ Vector((x, 0.0, z))) for x in (-w, w) for z in (-h, h)])
    return _gap(m, q) / ev.layout.rig.frame_width(ev.lens_m, 1.0)


def calibrate_tilt(ev):
    """Il minimo PAINT_TILT (da 60 gradi, a passi di uno) per cui, con
    PAINT_EXTRA calibrato, resta almeno PAINT_MIN_STRAIGHT di retta.
    Restituisce (tilt, extra)."""
    for tilt in range(60, 90):
        extra = calibrate_extra(ev, tilt) if PAINT_EXTRA is None else PAINT_EXTRA
        if PaintingPath(ev, tilt, extra).straight >= PAINT_MIN_STRAIGHT:
            return float(tilt), extra
    raise ValueError("nessun angolo sotto 90 gradi lascia abbastanza retta")


def calibrate_extra(ev, tilt):
    """Il minimo PAINT_EXTRA per cui le sagome sono staccate di PAINT_CLEAR."""
    def gap(extra):
        return silhouette_gap(ev, PaintingPath(ev, tilt, extra))
    lo, hi = 0.0, 0.5
    if gap(lo) >= PAINT_CLEAR:
        return lo
    while gap(hi) < PAINT_CLEAR:
        hi *= 2.0
        if hi > 100.0:
            raise ValueError("le sagome non si staccano: aumentare PAINT_TILT")
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if gap(mid) < PAINT_CLEAR:
            lo = mid
        else:
            hi = mid
    return hi


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
    scene.cycles.transparent_max_bounces = 32       # dissolvenze e facce semitrasparenti
    KIT.new_collection(scene)
    frames = list(range(FRAME_START, FRAME_END + 1))

    md = extended_face.make_M()
    painting_img = KIT.load_image(story.PAINTING_FILE)
    ev = story.ExitView(md, painting_img.size)
    layout = ev.layout
    cam = story.build_camera_and_world(KIT, layout, clip_end=story.CAMERA_DISTANCE + story.GRID_DEPTH + 40.0)
    m_scene.setup_aov_glow(KIT, scene, GLOW_AOV, GLARE_STRENGTH, GLARE_SIZE, GLOW_SOFTEN, GLOW_SOFTEN_WEIGHT)

    # --- la camera e' ferma (eye1); e' il quadro che arretra ---
    if PAINT_TILT is None:
        tilt, extra = calibrate_tilt(ev)
    else:
        tilt = PAINT_TILT
        extra = calibrate_extra(ev, tilt) if PAINT_EXTRA is None else PAINT_EXTRA
    path = PaintingPath(ev, tilt, extra)
    if path.straight <= 0.0:
        raise ValueError(f"l'arco comincerebbe {-path.straight:.2f} prima della partenza del quadro: "
                         f"aumentare PAINT_TILT")

    # --- il quadro: gira, si sposta e svanisce ---
    painting, p_mat = story.build_painting(KIT, painting_img, layout)
    fade(p_mat, [(PAINT_FADE[0], 1.0), (PAINT_FADE[1], 0.0)])
    bl_anim.key_visibility(painting, [(FRAME_START, True), (frame_of(PAINT_FADE[1]) + 1, False)])

    def painting_world(f):
        return path.painting_matrix(time_of(f))

    poses = [(f, painting_world(f).decompose()) for f in frames]
    painting.rotation_mode = 'QUATERNION'
    bl_anim.key_value(painting, "location", [(f, tuple(loc)) for f, (loc, _, _) in poses],
                      interpolation='LINEAR')
    bl_anim.key_value(painting, "rotation_quaternion", [(f, tuple(q)) for f, (_, q, _) in poses],
                      interpolation='LINEAR')

    # --- M: mover (posizione, scala, giro) -> orient (la posa del quadro) -> M ---
    face_img = KIT.load_image(m_scene.FACE_TEXTURE_FILE)
    uvs = m_scene.face_uvs(face_img, m_scene.FACE_TEXTURE_UV_PX, m_scene.FACE_TEXTURE_UV_INSET)
    m_mat = story.face_material(KIT, face_img, uvs)          # Look 0: i colori del quadro
    fade(m_mat, [(FACES_IN[0], 1.0), (FACES_IN[1], 0.0), (FACES_OUT[0], 0.0), (FACES_OUT[1], 1.0)])
    add_section_cut(m_mat, painting)
    mover = KIT.new_object("mover")
    mover.empty_display_size = 0.5
    mover.scale = (ev.s0,) * 3
    orient = KIT.new_object("orient", parent=mover)
    orient.rotation_euler = [math.radians(a) for a in story.ORIENT_EULER_DEG]
    m_obj = KIT.new_object("M", m_scene.merged_mesh(KIT, md, m_mat, uvs), parent=orient)
    bl_utils.merge_by_distance(m_obj)
    m_obj.visible_shadow = False
    bl_anim.key_visibility(m_obj, [(FRAME_START, True), (frame_of(MIGRATE[0]), False)])
    spin = spin_angles(frames)

    def frame_of_m(f):
        """Il centro di M e la sua rotazione attorno alla verticale: quella
        che gli da' il quadro, piu' il suo giro."""
        loc, q, _ = path.m_matrix(time_of(f)).decompose()
        loc = loc - Vector(tuple(path.lift)) * smootherstep(time_of(f), *GROW)
        return loc, q.to_euler().z + spin[f]

    m_poses = {f: frame_of_m(f) for f in frames}
    bl_anim.key_value(mover, "location", [(f, tuple(m_poses[f][0])) for f in frames],
                      interpolation='LINEAR')
    bl_anim.key_value(mover, "rotation_euler", [(f, (0.0, 0.0, m_poses[f][1])) for f in frames],
                      interpolation='LINEAR')
    scales = {f: ev.s0 * grow_at(time_of(f)) for f in frames}
    bl_anim.key_value(mover, "scale", [(f, (scales[f],) * 3) for f in frames], interpolation='LINEAR')
    O = story.orient_matrix()

    def world_of(f):
        loc, angle = m_poses[f]
        return Matrix.Translation(loc) @ Matrix.Rotation(angle, 4, 'Z') @ Matrix.Scale(scales[f], 4) @ O

    lit = build_section_lines(md, world_of, painting_world, frames)

    # --- l'icosaedro ---
    build_icosahedron(orient, md)

    # --- i 240 triangoli: seguono M, poi migrano nella griglia ---
    tri_mat = story.face_material(KIT, face_img, uvs)        # come M, senza il taglio
    mesh = m_scene.triangle_mesh(KIT, tri_mat, uvs)
    tris = [m_scene.Tri(p) for p in pieces.m_pieces(md)]

    def normal_of_tri(tri):
        n = Vector(tri.piece.normal)
        return lambda f: (Matrix.Rotation(m_poses[f][1], 3, 'Z') @ O.to_3x3() @ n).normalized()

    f_mig = frame_of(MIGRATE[0])
    centres = [np.asarray(world_of(f_mig) @ tri.loc) for tri in tris]
    normals = [np.asarray(normal_of_tri(tri)(f_mig)) for tri in tris]
    order = departure_order(centres, normals, ev.eye1)
    departs = departure_times(order)
    targets = ev.grid_poses(tris)
    mig_frames = [f for f in frames if f >= f_mig]
    for tri, target, t_dep in zip(tris, targets, departs):
        obj = KIT.new_object(f"tri_{tri.piece.index:03d}", mesh)
        obj.visible_shadow = False
        bl_anim.apply_keys(obj, migration_keys(tri, world_of, normal_of_tri(tri), t_dep, target, mig_frames))
        bl_anim.set_interpolation(obj, 'LINEAR', bl_anim.POSE_PATHS)
        bl_anim.key_visibility(obj, [(FRAME_START, False), (f_mig, True)])

    scene.frame_set(FRAME_START)
    print(f"[scene-1 draft5] frame {FRAME_START}-{FRAME_END} a {FPS} fps ({END:.3f} s)")
    print(f"[scene-1 draft5] il quadro arretra di {path.straight:.2f} in linea retta (da y = "
          f"{path.start[1]:.2f}), poi gira di {tilt:.0f} gradi su un arco di raggio {path.r:.2f} "
          f"(lungo {path.arc:.2f}); fa {path.drift:.2f} da {DRIFT_FROM:.2f} a {PAINT_MOVE:.2f} s, il resto "
          f"fino a {PAINT_STOP:.2f} s")
    eye = np.asarray(ev.eye1, dtype=float)
    depth_start = float(path.start[1] - eye[1])
    depth_move = float(path.pose(PAINT_MOVE)[0][1] - eye[1])
    half_h = layout.rig.frame_width(ev.lens_m, 1.0) / layout.rig.aspect / 2.0
    ico_r = float(np.linalg.norm(np.asarray(geometry.Polyhedron.ico.vertices[0].tup()))) \
        * geometry.enclosing_scale(md.vertices, geometry.Polyhedron.ico) * story.ICO_MARGIN
    dist = float(np.linalg.norm(np.asarray(ev.m_end, dtype=float) - eye))

    def fill(radius):
        return radius / math.sqrt(dist * dist - radius * radius) / half_h

    m_r = float(np.linalg.norm(np.asarray(ev.P), axis=1).max())
    print(f"[scene-1 draft5] uscito, M e' al centro in orizzontale e {path.lift[2]:+.3f} in verticale "
          f"({path.lift[2] / dist / (2.0 * half_h):+.1%} dell'altezza dell'immagine): ci torna mentre cresce")
    print(f"[scene-1 draft5] il quadro, alto quanto l'immagine all'inizio, a {PAINT_MOVE:.0f} s ne occupa il "
          f"{depth_start / depth_move:.0%}")
    print(f"[scene-1 draft5] M cresce di {GROW_FACTOR} volte da {GROW[0]:.2f} a {GROW[1]:.2f} s: la sua sfera "
          f"passa dal {fill(ev.s0 * m_r):.0%} al {fill(ev.s0 * GROW_FACTOR * m_r):.0%} dell'altezza "
          f"dell'immagine, quella dell'icosaedro arriva al {fill(ev.s0 * GROW_FACTOR * ico_r):.0%}")
    print(f"[scene-1 draft5] M esce di {path.d:.2f} ({extra:.2f} piu' che in v4), fino a "
          f"{np.round(ev.m_end, 2)}; esce da {EXIT_AT:.2f} a {EXIT_END:.2f} s, tutto fuori a {path.emerged_time():.2f} s; sagome di M e del quadro, alla fine, "
          f"staccate del {silhouette_gap(ev, path):.1%} della larghezza; la linea della sezione da "
          f"{time_of(lit[0]):.2f} a {time_of(lit[-1]):.2f} s")
    print(f"[scene-1 draft5] griglia a {ev.grid_distance():.2f} dalla camera, triangoli scalati a "
          f"{targets[0][2]:.3f}; partenze da {departs.min():.2f} a {departs.max():.2f} s, in volo "
          f"{FLY_SECONDS} s")


build()
