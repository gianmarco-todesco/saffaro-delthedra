"""
explode_M.py -- il poliedro M come 240 oggetti distinti, piu' l'animazione che
li porta dal poliedro a una griglia piana.

Differenza rispetto a create_M.py: li' M e' *una* mesh di 240 facce, qui e' *un*
triangolo equilatero (un solo datablock di mesh, 3 vertici) istanziato in 240
oggetti, ognuno con la propria roto-traslazione. I 240 triangoli di M sono
infatti tutti congruenti: la matrice che porta il triangolo canonico su ciascuno
di essi e' una rotazione pura (nessuna riflessione, nessuna scala), quindi si
decompone esattamente in location + rotation_quaternion -- cioe' proprio i due
canali su cui si mettono i keyframe.

Animazione di default: per HOLD_SECONDS il poliedro resta intero e gira su se'
stesso (e' l'empty padre che ruota, i triangoli sono fermi nel suo riferimento);
poi si divide e i 240 triangoli volano in una griglia sul piano XZ, disposti in
20 gruppi da 12 -- un gruppo per faccia estesa -- cosi' che si possano contare a
colpo d'occhio.

--------------------------------------------------------------------------
DOVE SI METTONO LE MANI  (si veda la sezione "TRAIETTORIE" piu' sotto)
--------------------------------------------------------------------------
* grid_pose(tri)    -> dove e come atterra il triangolo tri. Cambiando questa
                       funzione si cambia la formazione finale.
* make_keys(tri)    -> la lista completa dei keyframe di tri. E' il punto di
                       intervento principale: si possono aggiungere waypoint
                       intermedi, ritardi, archi, sovra-elongazioni...
* TRAJECTORIES      -> dizionario indice-triangolo -> funzione, per dare a un
                       singolo triangolo (o a pochi) una traiettoria tutta sua
                       senza toccare quella di default.
* pivot_keys()      -> la rotazione del poliedro intero, prima della divisione.

Ogni triangolo e' descritto da un oggetto Tri che porta con se' tutto quello che
serve per decidere il suo movimento: index (0..239), fan (0..19, quale faccia
estesa), slot (0..11, quale triangolo dentro il ventaglio), la posa di partenza
(loc/quat) e il suo centro/normale in M.

Lo script e' idempotente: rilanciandolo cancella gli oggetti della corsa
precedente e ricrea tutto, animazione compresa.
"""

import bpy
import mathutils

import os, sys
import math
import importlib

# rendi possibile importare i moduli da src/libs
# (nota bene: __file__ non funziona dallo script editor di Blender,
#  quindi si ricava il path del file dal datablock di testo attivo)
def _find_libs_dir():
    txt = getattr(getattr(bpy.context, "space_data", None), "text", None)
    if txt is None:  # lo script non gira dal Text Editor: cerco il datablock per nome
        txt = bpy.data.texts.get("explode_M.py")
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
import geometry, bl_utils, extended_face, pieces, bl_anim
for _mod in (geometry, bl_utils, extended_face, pieces, bl_anim):
    importlib.reload(_mod)

from bl_anim import Key


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

COLLECTION_NAME = "M_exploded"   # collection che contiene i 240 triangoli
PIVOT_NAME      = "M_pivot"      # empty padre: ruotalo per girare tutto l'insieme
MESH_NAME       = "triangle"     # l'unico datablock di mesh, condiviso dai 240
OBJ_PREFIX      = "tri"          # gli oggetti si chiamano tri_000 ... tri_239
MATERIAL_NAME   = "material"

FPS = 24                          # imposta anche scene.render.fps

FRAME_START    = 1                # primo frame: M e' intero e comincia a girare
HOLD_SECONDS   = 3.0              # quanto dura la rotazione, prima della divisione
MOVE_SECONDS   = 4.0              # durata del volo di un singolo triangolo
TAIL_SECONDS   = 2.0              # coda a griglia ferma, dopo l'ultimo arrivo

_HOLD_FRAMES = int(round(HOLD_SECONDS * FPS))
_MOVE_FRAMES = int(round(MOVE_SECONDS * FPS))
FRAME_MOVE_START = FRAME_START + _HOLD_FRAMES   # quando parte il primo triangolo

# --- la rotazione del poliedro intero, prima della divisione ---
SPIN_TURNS = 1.0                  # giri completi; 0 = niente rotazione
SPIN_AXIS  = 'Z'                  # 'X', 'Y' o 'Z'
SPIN_END_FRAME = FRAME_MOVE_START # fin quando gira (metti piu' avanti per far
                                  # continuare la rotazione durante il volo)

# --- la griglia finale: 20 gruppi da 12, per poterli contare ---
#
# Un gruppo per faccia estesa: 12 triangoli disposti 4 x 3, dove ogni riga da 4
# e' uno dei tre lati del triangolo di base del ventaglio (gli slot 0-3, 4-7,
# 8-11). I 20 gruppi stanno a loro volta in un rettangolo 4 x 5.
# In totale sono sempre 16 x 15 = 240 celle, ma separate da GROUP_GAP.
GROUP_COLS      = 4               # gruppi per riga        (4 x 5 = 20 gruppi)
GROUP_ROWS      = 5
COLS_PER_GROUP  = 4               # triangoli per riga     (4 x 3 = 12 triangoli)
ROWS_PER_GROUP  = 3
GRID_SPACING    = 1.20            # passo fra triangoli, in lati di triangolo
GROUP_GAP       = 0.60            # spazio vuoto fra un gruppo e l'altro
GRID_CENTER     = (0.0, 0.0, 0.0)

GRID_COLS = GROUP_COLS * COLS_PER_GROUP   # 16
GRID_ROWS = GROUP_ROWS * ROWS_PER_GROUP   # 15


# Il triangolo canonico (lato 1, sul piano XZ, normale -Y, vertice 0 in alto)
# sta in pieces.CANONICAL_TRIANGLE. Il piano XZ e la normale -Y non sono una
# scelta estetica, sono *la definizione* della posa finale: un triangolo con
# rotazione identita' e' gia' coricato nella griglia, quindi in grid_pose la
# rotazione da restituire e' semplicemente l'identita' (o una rotazione attorno
# a Y, che non lo solleva dal piano).
#
# La normale -Y vuol dire che, siccome in M le 240 facce sono orientate verso
# l'esterno e la trasformazione e' una rotazione, nella griglia si vedono tutte
# dalla stessa parte, quella della vista Fronte (tastierino 1).

GRID = pieces.Grid(GROUP_COLS, GROUP_ROWS, COLS_PER_GROUP, ROWS_PER_GROUP,
                   spacing=GRID_SPACING, group_gap=GROUP_GAP)


# =============================================================================
# I 240 TRIANGOLI DI M
# =============================================================================

class Tri:
    """Un triangolo di M e tutto cio' che serve per animarlo.

    Attributi
    ---------
    index : int          0..239, ordine di costruzione (= fan * 12 + slot)
    fan   : int          0..19, quale delle 20 facce estese
    slot  : int          0..11, quale triangolo dentro il ventaglio
                         (slot 0..3 stanno sul primo lato del triangolo di
                         base, 4..7 sul secondo, 8..11 sul terzo)
    loc   : mathutils.Vector      posizione di partenza (baricentro in M)
    quat  : mathutils.Quaternion  rotazione di partenza
    center: mathutils.Vector      baricentro del triangolo in M (= loc)
    normal: mathutils.Vector      normale uscente in M, versore
    obj   : bpy.types.Object      l'oggetto Blender (assegnato alla creazione)
    """

    __slots__ = ("index", "fan", "slot", "loc", "quat", "center", "normal", "obj")

    def __init__(self, index, fan, slot, loc, quat, center, normal):
        self.index = index
        self.fan = fan
        self.slot = slot
        self.loc = loc
        self.quat = quat
        self.center = center
        self.normal = normal
        self.obj = None

    def __repr__(self):
        return f"<Tri {self.index:03d} fan={self.fan} slot={self.slot}>"


def build_triangles():
    """I 240 triangoli di M come lista di Tri.

    La geometria -- la matrice rigida che porta il triangolo canonico su ogni
    faccia di M, e il controllo che sia davvero rigida -- e' in
    pieces.m_pieces; qui la si traduce nella coppia (location, quaternione),
    che sono i due canali su cui si mettono i keyframe.
    """
    triangles = []
    for piece in pieces.m_pieces():
        loc, quat = bl_anim.pose_from_matrix(piece.matrix)
        triangles.append(Tri(
            index=piece.index,
            fan=piece.fan,
            slot=piece.slot,
            loc=loc,
            quat=quat,
            center=mathutils.Vector(piece.center),
            normal=mathutils.Vector(piece.normal),
        ))
    return triangles


# =============================================================================
# TRAIETTORIE  --  e' qui che si mettono le mani
# =============================================================================

def grid_pose(tri):
    """Posa finale del triangolo tri: dove atterra nella griglia.

    Restituisce (location, rotation). La rotazione identita' lascia il triangolo
    coricato sul piano XZ, che e' come e' definito il triangolo canonico.

    La formazione e' rettangolare ma raggruppata, per rendere i 240 contabili a
    occhio: un gruppo (4 x 3) per ogni faccia estesa, 20 gruppi disposti 4 x 5.
    Il raggruppamento non e' arbitrario, ricalca la struttura di M: il gruppo e'
    `tri.fan` e dentro al gruppo ogni riga da 4 e' uno dei tre lati del triangolo
    di base del ventaglio (`tri.slot` 0-3, 4-7, 8-11).

    Varianti utili:

        group, cell = tri.index // 12, tri.index % 12   # stesso disegno, ma
                                                        # numerato per indice

        # triangoli alternati su/giu', per una tassellatura compatta
        # (con GRID_SPACING dimezzato sulle colonne)
        rotation = mathutils.Quaternion((0, 1, 0), math.pi) \
                   if (col + row) % 2 else mathutils.Quaternion()
    """
    x, z = GRID.cell(tri.fan, tri.slot)        # riga 0 in alto, centrata
    location = mathutils.Vector((
        GRID_CENTER[0] + x,
        GRID_CENTER[1],
        GRID_CENTER[2] + z,
    ))
    rotation = mathutils.Quaternion()          # identita': gia' sul piano XZ
    return location, rotation


def start_delay(tri):
    """Ritardo (in frame) con cui questo triangolo parte, rispetto agli altri.

    Zero = partono tutti insieme. Qualche alternativa gia' pronta:

        return tri.fan * 2                  # un ventaglio alla volta
        return tri.index * 0.25             # onda continua sui 240
        return 20 * (1 - tri.normal.z)      # prima la calotta in alto
        return abs(tri.center.z) * 8        # dall'equatore verso i poli
    """
    return 0


def make_keys(tri):
    """I keyframe del triangolo tri: e' LA funzione da modificare.

    Default: fermo in M fino a FRAME_MOVE_START (piu' l'eventuale ritardo), poi
    volo diretto verso la cella della griglia in MOVE_SECONDS. L'interpolazione
    e' Bezier con maniglie automatiche, quindi partenza e arrivo sono gia'
    morbidi senza bisogno di waypoint aggiuntivi.

    Per un'esplosione con rinculo -- il triangolo prima si stacca verso l'esterno
    lungo la propria normale, poi va a posto -- basta infilare un waypoint:

        keys.insert(2, Key(t1 + 0.30 * _MOVE_FRAMES,
                           tri.loc + tri.normal * 2.0,
                           tri.quat))

    Per farlo anche girare su se' stesso durante il volo, aggiungi un waypoint
    con una rotazione intermedia: il quaternione viene interpolato dal frame
    precedente al successivo, e Blender prende sempre la strada piu' corta,
    quindi un giro completo va spezzato in almeno tre passi.

    Key (in bl_anim) e' frame + posa; la rotazione e' un mathutils.Quaternion:
        mathutils.Quaternion()                              # identita'
        mathutils.Quaternion((0, 0, 1), math.radians(90))   # asse, angolo
        tri.quat                                            # la posa in M
    """
    end_loc, end_rot = grid_pose(tri)

    t0 = FRAME_START
    t1 = FRAME_MOVE_START + start_delay(tri)   # fine della pausa
    t2 = t1 + _MOVE_FRAMES                     # arrivo nella griglia

    return [
        Key(t0, tri.loc, tri.quat),            # posa in M (rende leggibile la timeline)
        Key(t1, tri.loc, tri.quat),            # ultimo frame fermo
        Key(t2, end_loc, end_rot),             # a posto nella griglia
    ]


# Traiettorie su misura per singoli triangoli: indice -> funzione(tri) -> [Key].
# Quello che sta qui dentro sostituisce make_keys solo per quell'indice.
#
#   def _tri_7(tri):
#       keys = make_keys(tri)               # parti dal default...
#       keys[-1].frame += 48                # ...e arriva buon ultimo
#       return keys
#   TRAJECTORIES[7] = _tri_7
#
TRAJECTORIES = {}


def keys_for(tri):
    """Keyframe del triangolo: la traiettoria su misura se c'e', altrimenti
    quella di default."""
    return TRAJECTORIES.get(tri.index, make_keys)(tri)


def pivot_keys():
    """Rotazione dell'empty padre: il poliedro che gira su se' stesso prima di
    dividersi. Restituisce una lista di (frame, angoli di Eulero).

    I triangoli sono figli del pivot, quindi la loro animazione e' espressa nel
    riferimento che ruota: finche' M e' intero lo si vede girare tutto insieme, e
    la divisione parte esattamente da dove la rotazione lascia i pezzi.

    Perche' Eulero e non quaternioni (che invece usano i triangoli): un
    quaternione non sa rappresentare piu' di mezzo giro per segmento, quindi con
    la rotazione a quaternioni SPIN_TURNS > 0.5 non si potrebbe fare. Gli angoli
    di Eulero sono numeri che crescono, e 2 pi greco e' un giro.

    Con l'interpolazione Bezier la rotazione parte da ferma, accelera e si
    riferma: il poliedro si "carica" e si arresta proprio quando esplode. Per
    farlo girare a velocita' costante basta mettere LINEAR sulle sue fcurve.

    ATTENZIONE: SPIN_TURNS non intero lascia il pivot ruotato a fine rotazione, e
    la griglia finale non e' piu' sul piano XZ (viene ruotata insieme a lui).
    Se serve fermarsi a meta' giro, o si accetta la griglia storta, oppure si
    riporta il pivot a 0 con un terzo keyframe durante il volo.
    """
    if SPIN_TURNS == 0.0:
        return []

    axis = "XYZ".index(SPIN_AXIS)
    start = [0.0, 0.0, 0.0]
    end = [0.0, 0.0, 0.0]
    end[axis] = 2.0 * math.pi * SPIN_TURNS
    return [(FRAME_START, start), (SPIN_END_FRAME, end)]


# =============================================================================
# COSTRUZIONE DELLA SCENA
# =============================================================================

def make_triangle_mesh(name):
    """Crea (sostituendolo, se esiste) il datablock di mesh del triangolo
    canonico. E' l'unica mesh della scena: i 240 oggetti la condividono, quindi
    modificandola si modificano tutti i triangoli insieme."""
    if name in bpy.data.meshes:
        bpy.data.meshes.remove(bpy.data.meshes[name])
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([v.tup() for v in pieces.CANONICAL_TRIANGLE], [], [(0, 1, 2)])
    mesh.update()
    mesh.materials.append(bl_utils.get_or_create_material(MATERIAL_NAME))
    return mesh


def clear_previous_run():
    """Cancella oggetti, collection e mesh della corsa precedente, cosi' lo
    script si puo' rilanciare senza accumulare duplicati ("tri_000.001").
    L'oggetto pivot invece si tiene (e' solo un empty); la sua animazione viene
    riscritta da bl_anim.apply_euler_keys."""
    collection = bpy.data.collections.get(COLLECTION_NAME)
    if collection is not None:
        for obj in list(collection.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(collection)
    # eventuali avanzi fuori dalla collection (rinominati, spostati a mano...)
    for obj in list(bpy.data.objects):
        if obj.name.startswith(OBJ_PREFIX + "_"):
            bpy.data.objects.remove(obj, do_unlink=True)


def build_scene():
    """Crea i 240 oggetti, li anima e sistema l'intervallo dei frame della scena."""
    clear_previous_run()

    scene = bpy.context.scene
    scene.render.fps = FPS

    mesh = make_triangle_mesh(MESH_NAME)
    collection = bpy.data.collections.new(COLLECTION_NAME)
    scene.collection.children.link(collection)

    # l'empty padre: ruotando lui ruota tutto l'insieme, e i keyframe dei
    # triangoli restano espressi nel suo sistema di riferimento. E' lui che fa
    # girare il poliedro prima che si divida.
    pivot = bl_utils.get_or_create_empty(PIVOT_NAME)
    spin = pivot_keys()
    bl_anim.apply_euler_keys(pivot, spin)

    triangles = build_triangles()
    last_frame = max([FRAME_START] + [f for f, _ in spin])
    for tri in triangles:
        obj = bpy.data.objects.new(f"{OBJ_PREFIX}_{tri.index:03d}", mesh)
        collection.objects.link(obj)
        obj.parent = pivot
        # matrix_parent_inverse deve restare l'identita': le pose sono gia'
        # calcolate nel riferimento del pivot, ed e' proprio questo che fa
        # ruotare i triangoli insieme a lui. Qui NON si usa bl_utils.set_parent,
        # che ci metterebbe l'inversa della matrice del pivot: con un pivot
        # ruotato quella compensazione annullerebbe la rotazione.
        obj.matrix_parent_inverse = mathutils.Matrix.Identity(4)
        tri.obj = obj

        keys = keys_for(tri)
        bl_anim.apply_keys(obj, keys)
        last_frame = max(last_frame, max(k.frame for k in keys))

    scene.frame_start = FRAME_START
    scene.frame_end = last_frame + int(round(TAIL_SECONDS * FPS))
    scene.frame_set(FRAME_START)

    print(f"[explode_M] {len(triangles)} triangoli in '{COLLECTION_NAME}', "
          f"mesh condivisa '{mesh.name}' ({len(mesh.vertices)} vertici), "
          f"frame {scene.frame_start}-{scene.frame_end} a {FPS} fps")
    print(f"[explode_M] rotazione: {SPIN_TURNS} giri su {SPIN_AXIS} "
          f"fino al frame {SPIN_END_FRAME}; griglia "
          f"{GROUP_COLS}x{GROUP_ROWS} gruppi da {COLS_PER_GROUP}x{ROWS_PER_GROUP}")
    if SPIN_TURNS != round(SPIN_TURNS):
        print(f"[explode_M] ATTENZIONE: SPIN_TURNS = {SPIN_TURNS} non e' intero, "
              f"il pivot resta ruotato e la griglia finale non e' sul piano XZ")
    return triangles


TRIANGLES = build_scene()
