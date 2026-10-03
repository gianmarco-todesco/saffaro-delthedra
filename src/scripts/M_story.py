"""
M_story.py -- l'animazione completa: l'icosaedro gira e si apre, una faccia si
dispiega nel ventaglio di 12 triangoli, il grado di liberta' fa il suo viaggio, e
alla fine le 20 facce si ricompongono nel poliedro M.

--------------------------------------------------------------------------
PERCHE' QUESTO SCRIPT NON USA UN HANDLER DI FOTOGRAMMA
--------------------------------------------------------------------------
`single_fan.py`, `two_fans.py` e `20-fans.py` ricostruiscono la mesh dentro un
handler `frame_change_pre`/`post`. Scrivere su `bpy.data` da li' non e'
supportato durante il rendering: l'handler scatta dentro la valutazione del
depsgraph, mentre il renderer sta tenendo puntatori a quei dati. Da qui il crash
casuale ma riproducibile, e il ripiego del ciclo manuale di `playground.py`.

Qui Python gira **una volta sola**, quando lanci lo script, e il risultato
finisce nei dati di animazione di Blender:

* la forma      -> shape key (una per forma distinta), valori keyframati;
* il bordo      -> una seconda mesh di cilindri e sferette, anch'essa in shape
                   key: i raggi che suddividono la faccia crescono da P0, e i
                   vertici intermedi restano nascosti dentro i cilindri degli
                   spigoli finche' il loro raggio non li raggiunge;
* la posa       -> keyframe su location/rotation del pivot, degli empty e dei
                   ventagli;
* comparire e sparire -> keyframe sulla scala: ha un tempo, e i figli la
                   ereditano (la visibilita' no).

A render time non gira una riga di Python. Quindi Render Animation, la coda di
render, `blender -b -a`, lo scrubbing e i movimenti di camera funzionano tutti.
Il prezzo e' che per cambiare t1 o la forma bisogna rilanciare lo script. I
canali di movimento -- rotazione del pivot, z, rotazione e scala delle facce --
restano invece keyframe normali, ritoccabili a mano nel Graph Editor.

--------------------------------------------------------------------------
LA GEOMETRIA: TRE PARAMETRI, GIA' TUTTI IN LIBRERIA
--------------------------------------------------------------------------
t1  la forma del ventaglio. E' |P1-P5| diviso il lato dei triangoli, cioe'
    esattamente `extended_face.edge_span(phi)`; `phi_from_edge_span` lo inverte.
    Dominio (0, sqrt(3)); il valore che chiude M e' T1_M, sotto.

t2  porta i 12 triangoli sui 6 triangoli equilateri che condividono P0. I tre
    vertici Q -- a distanza 1 da P0 e dai due angoli adiacenti -- e i punti medi
    sono esattamente quello che calcola `flatten1_extended_face`. Q esiste per
    ogni t1 del dominio: il circoraggio di (P0,P1,P5) e' 1/sqrt(4-t1^2), che
    raggiunge 1 solo a t1 = sqrt(3), cioe' al bordo.

t3  porta il ventaglio sul triangolo equilatero piatto P1,P5,P9: P0 al
    baricentro, gli altri a 1/4, 2/4, 3/4 dei lati. E'
    `flatten2_extended_face`.

t2 e t3 sono comandati da un solo parametro s: per s in [0, 0.5] vale t2 = 2s e
t3 = 0; per s in [0.5, 1] vale t2 = 1 e t3 = 2s-1. Quindi s=0 e' il ventaglio di
M, s=0.5 il ventaglio di 6 triangoli, s=1 il triangolo piatto.

Nota utile: t2 e t3 lasciano fermi P1, P5, P9. La posa di una faccia dipende
percio' solo da t1, e la stessa posa vale sia per i triangoli piatti (che
formano l'icosaedro) sia per i ventagli aperti (che formano M).

--------------------------------------------------------------------------
LE CINQUE FASI
--------------------------------------------------------------------------
La faccia si apre una cosa alla volta: prima compaiono gli spigoli, poi la
faccia si piega lungo quegli spigoli. Per questo la crescita dei raggi ha due
canali propri (G1_TRACK, G2_TRACK) e non e' una funzione di s.

  1  (fine via_le_altre)     si vede solo il triangolo
  2  fase2   s=1   g1:0->1     arrivano i 6 raggi verso P1,P3,P5,P7,P9,P11
  3  fase3   s:1->0.5          i 6 triangoli complanari si piegano
  4  fase4   s=0.5 g2:0->1     arrivano i 6 raggi verso P2,P4,...,P12
  5  fase5   s:0.5->0          i 12 triangoli, complanari a due a due, si piegano

Sei raggi per gruppo, non tre: con tre soli raggi il triangolo si dividerebbe in
tre aquiloni e non in sei triangoli, e in tutto ne servono dodici. Chi volesse
un'altra suddivisione cambia SPOKE_GROUP_1 e SPOKE_GROUP_2.

--------------------------------------------------------------------------
DOVE SI METTONO LE MANI
--------------------------------------------------------------------------
* BEATS         -> la scaletta: nomi e durate in secondi. Cambiando una durata
                   tutto il resto si sposta da solo.
* PIVOT_TURNS   -> i giri del poliedro su se stesso, e quando.
* T1_TRACK      -> il viaggio del grado di liberta'.
* S_TRACK       -> quando la faccia si piega.
* G1_TRACK, G2_TRACK, SPOKE_GROUP_1/2 -> quando arrivano i raggi del bordo,
                   e quali.
* SPIN_TRACK    -> la rotazione di ogni faccia sul proprio asse.
* z_keys()      -> l'allontanamento dal centro, uguale per tutte.
* scale_keys()  -> quando una faccia compare e sparisce; enter_order() decide
                   in che ordine rientrano le 18 finali.

--------------------------------------------------------------------------
IL MOVIMENTO D'INSIEME
--------------------------------------------------------------------------
Tutto e' appeso a un empty centrale (PIVOT_NAME): il poliedro gira facendo
girare lui, in tre riprese da un giro, ognuna con ease in/out.

  giro1          l'icosaedro gira; a meta' le facce si staccano un po'
  via_le_altre   restano la prima faccia, le altre si scalano a zero
  fase2..fase5   la faccia si apre (si veda sotto), girando due volte di 120
                 gradi sul proprio asse -- che e' una simmetria del ventaglio,
                 quindi resta al suo posto
  t1_su, t1_giu  il grado di liberta': al massimo e poi al minimo, un viaggio solo
  entra_B        compare la seconda faccia, gia' trasformata come la prima
  avvicina       le due tornano al loro posto e si toccano sui triangoli di base
  t1_giusto      t1 torna a T1_M: e' qui che i bordi combaciano
  separa         si riallontanano
  entrano_tutte  compaiono le altre 18, sfalsate, dalle vicine alle lontane
  giro2          il poliedro gira con le facce ancora separate
  chiusura+giro3 le facce rientrano mentre il poliedro fa l'ultimo giro
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
        txt = bpy.data.texts.get("M_story.py")
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
import geometry, bl_utils, extended_face
for _mod in (geometry, bl_utils, extended_face):
    importlib.reload(_mod)

from geometry import Vector, MeshData


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

COLLECTION_NAME = "M_story"
MESH_NAME       = "fan"          # l'unico datablock di mesh: 13 vertici
FAN_PREFIX      = "fan"          # fan_00 ... fan_19
SEAT_PREFIX     = "seat"         # seat_00 ... seat_19: gli empty che tengono il
                                 # posto delle 20 facce sull'icosaedro
MATERIAL_NAME   = "fan_surface"
FAN_COLOR       = (0.85, 0.45, 0.15, 1.0)

# --- il bordo: cilindri sugli spigoli, sferette sui vertici ---
WIRE_MESH_NAME  = "fan_wire"     # la seconda mesh condivisa
WIRE_PREFIX     = "wire"         # wire_00 ... wire_19
EDGE_MATERIAL   = "fan_edge"     # la spezzata esterna, e le sue sferette
SPOKE_MATERIAL  = "fan_spoke"    # i raggi che passano per P0, e il mozzo
EDGE_COLOR      = (0.06, 0.07, 0.10, 1.0)
SPOKE_COLOR     = (0.95, 0.72, 0.15, 1.0)

TUBE_RADIUS     = 0.011          # in lati di triangolo (il lato vale 1)
TUBE_SIDES      = 8
SPOKE_RAMP      = 0.12           # in quanta parte della crescita un raggio
                                 # passa da punta a tubo pieno
VERTEX_RADIUS   = 0.026          # le sferette sui vertici, quando contano
VERTEX_RADIUS_HIDDEN = 0.008     # < TUBE_RADIUS: la sferetta di un vertice che
                                 # non ha ancora il suo raggio sparisce dentro
                                 # il cilindro degli spigoli
SPHERE_SEGMENTS = 8
SPHERE_RINGS    = 6

FPS         = 24
FRAME_START = 1

# il valore di t1 per cui M si chiude, e i due estremi della sua escursione
# (il dominio e' 0 < t1 < sqrt(3), ma agli estremi la faccia degenera)
T1_M   = extended_face.edge_span(extended_face.PHI_CLOSING)   # 0.910757094
T1_MAX = 1.20
T1_MIN = 0.60

PIVOT_NAME = "M_pivot"           # l'empty centrale: ruotandolo gira tutto
Z_OUT = 0.45                     # di quanto le facce si staccano dal loro posto

# le due facce protagoniste: 0 e 1 dell'icosaedro condividono uno spigolo
FACE_A = 0
FACE_B = 1


# =============================================================================
# LA REGIA
# =============================================================================

BEATS = [
    ("giro1",         4.0),   # l'icosaedro fa un giro su se stesso; a meta' le
                              # facce si allontanano un po' dal centro
    ("via_le_altre",  1.2),   # tutte tranne la prima si rimpiccioliscono a zero
    ("fase2",         1.5),   # arrivano i primi 6 raggi
    ("fase3",         2.0),   # diventa 6 triangoli, girando di 120 gradi
    ("fase4",         1.5),   # arrivano gli altri 6 raggi
    ("fase5",         2.0),   # diventa 12 triangoli, altri 120 gradi
    ("t1_su",         2.0),   # il grado di liberta': t1 sale al massimo
    ("t1_giu",        2.5),   # ... e scende al minimo
    ("entra_B",       1.5),   # compare la seconda faccia, gia' trasformata
    ("avvicina",      1.5),   # le due facce si toccano sui triangoli di base
    ("t1_giusto",     2.5),   # t1 torna al valore giusto: i bordi combaciano
    ("separa",        1.5),   # tornano alla distanza di prima
    ("entrano_tutte", 3.0),   # compaiono le altre 18, una dopo l'altra
    ("giro2",         3.0),   # il poliedro gira con le facce ancora separate
    ("chiusura",      2.0),   # le facce tornano alla distanza giusta...
    ("giro3",         3.0),   # ... mentre il poliedro fa l'ultimo giro
]

# I giri del pivot centrale: (prima battuta, ultima battuta, giri).
# Sono cumulativi, con interpolazione Bezier: ognuno parte da fermo e si ferma,
# che e' l'ease in/out. L'ultimo copre due battute perche' la chiusura delle
# facce e il giro finale devono succedere insieme.
PIVOT_TURNS = [
    ("giro1", "giro1", 1.0),
    ("giro2", "giro2", 1.0),
    ("chiusura", "giro3", 1.0),
]

ENTER_RAMP_SECONDS = 0.6      # quanto ci mette una faccia a comparire


def _build_marks():
    """Da BEATS ai fotogrammi: {nome: (primo frame, ultimo frame)}."""
    marks, f = {}, FRAME_START
    for name, seconds in BEATS:
        end = f + int(round(seconds * FPS))
        marks[name] = (f, end)
        f = end
    return marks


MARKS = _build_marks()
FRAME_END = MARKS[BEATS[-1][0]][1]


def beat(name):
    """(primo, ultimo) fotogramma della battuta."""
    return MARKS[name]


def smoothstep(x, x0, x1):
    """Raccordo morbido da 0 a 1 fra x0 e x1, piatto agli estremi."""
    if x1 == x0:
        return 0.0 if x < x0 else 1.0
    u = min(1.0, max(0.0, (x - x0) / (x1 - x0)))
    return u * u * (3.0 - 2.0 * u)


class Track:
    """Canale scalare: coppie (frame, valore) raccordate con smoothstep, e
    costante prima della prima chiave e dopo l'ultima."""

    def __init__(self, keys):
        self.keys = sorted(keys)

    def __call__(self, frame):
        keys = self.keys
        if frame <= keys[0][0]:
            return keys[0][1]
        if frame >= keys[-1][0]:
            return keys[-1][1]
        for (fa, va), (fb, vb) in zip(keys, keys[1:]):
            if fa <= frame <= fb:
                return va + (vb - va) * smoothstep(frame, fa, fb)
        return keys[-1][1]


# il canale s: 1 = triangolo piatto, 0.5 = sei triangoli, 0 = il ventaglio di M.
# Si muove solo nelle fasi 3 e 5: le fasi 2 e 4 fanno arrivare gli spigoli a
# forma ferma.
S_TRACK = Track([
    (beat("fase3")[0], 1.0),
    (beat("fase3")[1], 0.5),
    (beat("fase5")[0], 0.5),
    (beat("fase5")[1], 0.0),
])

# I due canali di crescita dei raggi. Sono canali propri e non funzioni di s:
# e' proprio questo che separa "arrivano gli spigoli" da "la faccia si piega".
G1_TRACK = Track([(beat("fase2")[0], 0.0), (beat("fase2")[1], 1.0)])
G2_TRACK = Track([(beat("fase4")[0], 0.0), (beat("fase4")[1], 1.0)])

# Quali raggi appartengono a quale gruppo, per indice di libreria (il vertice k
# e' il P(k+1) dell'utente).
#
#   gruppo 1 -> P1, P3, P5, P7, P9, P11     gruppo 2 -> P2, P4, ..., P12
#
# Sono sei e sei. Con tre soli raggi in fase 2 il triangolo non diventa sei
# triangoli ma tre aquiloni, e in fase 4 i sei nuovi porterebbero il totale a
# nove invece dei dodici che servono al ventaglio completo. Se vuoi comunque far
# entrare per primi solo P3, P7, P11, basta spostare 0, 4, 8 nel gruppo 2.
SPOKE_GROUP_1 = (0, 2, 4, 6, 8, 10)
SPOKE_GROUP_2 = (1, 3, 5, 7, 9, 11)


# Il canale t1: un solo viaggio, niente oscillazioni. Dal valore giusto al
# massimo, poi al minimo; resta li' mentre entra la seconda faccia e le due si
# avvicinano, e infine torna a T1_M, che e' il momento in cui i bordi combaciano.
T1_TRACK = Track([
    (beat("t1_su")[0],     T1_M),
    (beat("t1_su")[1],     T1_MAX),
    (beat("t1_giu")[1],    T1_MIN),
    (beat("t1_giusto")[0], T1_MIN),
    (beat("t1_giusto")[1], T1_M),
])

# La rotazione di ogni faccia sul proprio asse: 120 gradi mentre diventa 6
# triangoli, altri 120 mentre diventa 12. Funziona perche' il ventaglio ha
# simmetria ternaria: dopo 120 gradi e' indistinguibile da prima, quindi la
# faccia resta al suo posto sull'icosaedro e la si puo' applicare a tutte e 20
# senza preoccuparsi di quelle che in quel momento non si vedono.
SPIN_TRACK = Track([
    (beat("fase3")[0], 0.0),
    (beat("fase3")[1], 2.0 * math.pi / 3.0),
    (beat("fase5")[0], 2.0 * math.pi / 3.0),
    (beat("fase5")[1], 4.0 * math.pi / 3.0),
])


PARAM_DECIMALS = 7      # a quante cifre si arrotondano i parametri


def params_at(frame):
    """(t1, s, g1, g2) del fotogramma. E' l'unica fonte dei quattro parametri.

    L'arrotondamento serve a far coincidere i fotogrammi che hanno la stessa
    forma, cosi' che condividano una sola shape key: senza, due valori che
    dovrebbero essere uguali differiscono negli ultimi bit e generano due chiavi.
    Ma allora la forma e' quella dei parametri arrotondati, e anche la posa degli
    empty deve usare gli stessi: se la posa seguisse t1 esatto e la forma t1
    arrotondato, le facce non combacerebbero esattamente. Meglio una verita'
    sola, e passa tutta da qui.
    """
    return (round(T1_TRACK(frame), PARAM_DECIMALS),
            round(S_TRACK(frame), PARAM_DECIMALS),
            round(G1_TRACK(frame), PARAM_DECIMALS),
            round(G2_TRACK(frame), PARAM_DECIMALS))


def fan_params_at(frame):
    """I parametri da cui dipende il ventaglio: solo (t1, s)."""
    return params_at(frame)[:2]


def z_keys():
    """I keyframe (frame, z) dell'allontanamento dal centro. Uno solo per tutte
    le facce: nei momenti in cui A e B si muovono da sole, le altre non si
    vedono, quindi non serve distinguerle.

    z = 0 vuol dire "al suo posto": qualunque sia t1, le 20 facce hanno i
    triangoli di base che formano l'icosaedro di lato t1 e quindi si toccano
    sugli spigoli. Con t1 = T1_M e s = 0 e' esattamente il poliedro M.

    Finiscono in Blender come keyframe veri sul solo canale Z, quindi si possono
    ritoccare a mano nel Graph Editor senza rilanciare lo script.
    """
    g0, g1 = beat("giro1")
    return [
        (g0, 0.0),
        ((g0 + g1) // 2, 0.0),          # "a meta' della rotazione"
        (g1, Z_OUT),
        (beat("avvicina")[0], Z_OUT),
        (beat("avvicina")[1], 0.0),     # A e B si toccano sui triangoli di base
        (beat("separa")[0], 0.0),
        (beat("separa")[1], Z_OUT),
        (beat("chiusura")[0], Z_OUT),
        (beat("chiusura")[1], 0.0),     # il poliedro si chiude
    ]


def enter_order():
    """L'ordine in cui compaiono le 18 facce che non sono A e B.

    Dalle vicine di A verso le lontane: si vede il poliedro ricomporsi a partire
    dalla faccia che si stava guardando, invece che a caso."""
    normal_a = SEATS[FACE_A][1]
    others = [i for i in range(len(SEATS)) if i not in (FACE_A, FACE_B)]
    return sorted(others, key=lambda i: (-float(SEATS[i][1] @ normal_a), i))


def scale_keys(face):
    """I keyframe (frame, scala) della faccia: 1 = c'e', 0 = non c'e'.

    Comparire e sparire e' una scalatura e non un interruttore di visibilita':
    cosi' ha un tempo e un'accelerazione, e le 18 facce finali possono entrare
    sfalsate una dopo l'altra."""
    if face == FACE_A:
        return [(FRAME_START, 1.0)]

    via0, via1 = beat("via_le_altre")
    keys = [(via0, 1.0), (via1, 0.0)]

    if face == FACE_B:
        f0, f1 = beat("entra_B")
        return keys + [(f0, 0.0), (f1, 1.0)]

    order = enter_order()
    rank = order.index(face)
    f0, f1 = beat("entrano_tutte")
    ramp = max(1, int(round(ENTER_RAMP_SECONDS * FPS)))
    step = (f1 - f0 - ramp) / max(1, len(order) - 1)
    start = f0 + int(round(rank * step))
    return keys + [(start, 0.0), (start + ramp, 1.0)]


def pivot_keys():
    """I keyframe (frame, angolo) della rotazione del pivot centrale."""
    keys, angle = [(FRAME_START, 0.0)], 0.0
    for first, last, turns in PIVOT_TURNS:
        keys.append((beat(first)[0], angle))
        angle += 2.0 * math.pi * turns
        keys.append((beat(last)[1], angle))
    keys.append((FRAME_END, angle))
    return keys


# =============================================================================
# GEOMETRIA
# =============================================================================

def fan_shape(t1, s):
    """La faccia estesa per i parametri (t1, s), come MeshData di 13 vertici.

    `flatten2_extended_face` si applica direttamente alla faccia estesa e non al
    risultato di flatten1: usa solo P1, P5, P9, che flatten1 lascia fermi, e il
    risultato e' identico (verificato).
    """
    md = extended_face.make_extended_face(extended_face.phi_from_edge_span(t1))
    flat1 = extended_face.flatten1_extended_face(md)
    if s <= 0.5:
        return extended_face.morph(md, flat1, 2.0 * s)
    flat2 = extended_face.flatten2_extended_face(md)
    return extended_face.morph(flat1, flat2, 2.0 * s - 1.0)


# -----------------------------------------------------------------------------
# IL BORDO: CILINDRI SUGLI SPIGOLI, SFERETTE SUI VERTICI
# -----------------------------------------------------------------------------
#
# Tutto questo e' una seconda mesh, con la stessa struttura della prima: numero
# di vertici fisso, e le posizioni bakerate in shape key. Nessun oggetto per
# ogni cilindro (sarebbero 24 x 20 = 480), nessun modificatore, nessun Python a
# render time.
#
# Gli spigoli sono di tre famiglie:
#   * la spezzata esterna P1-P2-...-P12-P1, 12 segmenti, sempre presenti;
#   * i 6 raggi verso P1, P3, P5, P7, P9, P11, che dividono il triangolo nei 6
#     triangoli: compaiono mentre t3 scende da 1 a 0;
#   * i 6 raggi verso P2, P4, ..., P12, che portano da 6 a 12 triangoli:
#     compaiono mentre t2 scende da 1 a 0.
#
# "Comparire" e' letteralmente crescere da P0: un raggio non ancora nato e' un
# cilindro di lunghezza zero, e la sua estremita' va da P0 al vertice. Non serve
# animare trasparenze ne' visibilita', e l'effetto e' quello che volevi --
# l'estensione da P0 fino al contatto con la spezzata esterna.
#
# Indici: nella libreria il vertice k (0..11) e' il P(k+1) dell'utente, e il 12
# e' l'apice P0. Quindi il primo gruppo di raggi e' quello degli indici pari.

_TUBE_REF = np.array([0.0, 0.0, 1.0])


def _ring_basis(axis):
    """Due versori perpendicolari ad `axis` (versore), scelti in modo continuo.

    La continuita' non e' un dettaglio: i vertici del tubo vengono interpolati
    fra shape key vicine, e se la base dell'anello cambiasse di scatto da un
    fotogramma all'altro il cilindro si torcerebbe. Si proietta percio' un
    riferimento fisso. L'assert protegge l'unico caso in cui la scelta diventa
    instabile, cioe' un asse quasi parallelo al riferimento: sulla famiglia
    percorsa dall'animazione il margine misurato e' 17 gradi.
    """
    e1 = _TUBE_REF - axis * float(_TUBE_REF @ axis)
    norm = float(np.linalg.norm(e1))
    assert norm > 0.15, \
        f"asse quasi parallelo al riferimento (sin = {norm:.3f}): l'anello del tubo si torce"
    e1 = e1 / norm
    return e1, np.cross(axis, e1)


def _tube(p, q, radius, caps):
    """Cilindro da p a q, come MeshData. Con `caps` aggiunge i due tappi.

    **Sul bordo i tappi non vanno messi.** Due cilindri consecutivi della
    spezzata si toccano di testa: coi tappi si ritrovano due dischi esattamente
    coincidenti, che litigano sullo z-buffer, e per giunta l'anello e' condiviso
    fra tappo e fianco, quindi lo smooth shading vi media una normale assurda --
    e da li' l'aspetto "a sezioni" invece di un cilindro unico. Senza tappi gli
    anelli coincidono, le normali sono entrambe radiali e identiche, e la
    superficie risulta continua da sola. Dove la spezzata si piega ci pensa la
    sferetta del vertice, che li' e' grande.

    I raggi invece i tappi li vogliono: la punta resta scoperta mentre cresce. E
    un raggio non ancora nato arriva qui con p = q **e** raggio 0 (si veda
    `spoke_radius`), quindi collassa in un punto, tappi compresi.
    """
    p = np.asarray(p, dtype=float)
    q = np.asarray(q, dtype=float)
    axis = q - p
    length = float(np.linalg.norm(axis))

    count = 2 * TUBE_SIDES + (2 if caps else 0)
    md = MeshData()
    if length < 1e-12 or radius < 1e-12:
        md.vertices = [tuple(p)] * count
    else:
        e1, e2 = _ring_basis(axis / length)
        ring = [radius * (math.cos(a) * e1 + math.sin(a) * e2)
                for a in (2.0 * math.pi * j / TUBE_SIDES for j in range(TUBE_SIDES))]
        md.vertices = [tuple(p + r) for r in ring] + [tuple(q + r) for r in ring]
        if caps:
            md.vertices += [tuple(p), tuple(q)]

    md.faces = [[j, (j + 1) % TUBE_SIDES,
                 TUBE_SIDES + (j + 1) % TUBE_SIDES, TUBE_SIDES + j]
                for j in range(TUBE_SIDES)]
    if caps:
        lo, hi = 2 * TUBE_SIDES, 2 * TUBE_SIDES + 1    # i due centri dei tappi
        md.faces += [[lo, (j + 1) % TUBE_SIDES, j] for j in range(TUBE_SIDES)]
        md.faces += [[hi, TUBE_SIDES + j, TUBE_SIDES + (j + 1) % TUBE_SIDES]
                     for j in range(TUBE_SIDES)]
    return md


def _sphere(center, radius):
    """Sferetta UV centrata in `center`. Raggio 0 la riduce a un punto, che e'
    come il mozzo P0 resta invisibile finche' i raggi non cominciano a nascere."""
    center = np.asarray(center, dtype=float)
    verts = [tuple(center + np.array([0.0, 0.0, radius]))]
    for i in range(1, SPHERE_RINGS):
        theta = math.pi * i / SPHERE_RINGS
        z, rho = math.cos(theta) * radius, math.sin(theta) * radius
        for j in range(SPHERE_SEGMENTS):
            a = 2.0 * math.pi * j / SPHERE_SEGMENTS
            verts.append(tuple(center + np.array(
                [rho * math.cos(a), rho * math.sin(a), z])))
    verts.append(tuple(center + np.array([0.0, 0.0, -radius])))
    south = len(verts) - 1

    def idx(i, j):
        return 1 + (i - 1) * SPHERE_SEGMENTS + (j % SPHERE_SEGMENTS)

    faces = [[0, idx(1, j), idx(1, j + 1)] for j in range(SPHERE_SEGMENTS)]
    for i in range(1, SPHERE_RINGS - 1):
        faces += [[idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)]
                  for j in range(SPHERE_SEGMENTS)]
    faces += [[south, idx(SPHERE_RINGS - 1, j + 1), idx(SPHERE_RINGS - 1, j)]
              for j in range(SPHERE_SEGMENTS)]

    md = MeshData()
    md.vertices = verts
    md.faces = faces
    return md


def spoke_radius(g):
    """Raggio del cilindro di un raggio cresciuto di `g`.

    Non e' costante: sale da 0 al valore pieno nel primo SPOKE_RAMP della
    crescita. Cosi' il raggio esce da P0 come una punta e non come un tubo gia'
    grosso che spunta, e soprattutto a g = 0 anche i tappi hanno raggio nullo."""
    return TUBE_RADIUS * smoothstep(g, 0.0, SPOKE_RAMP)


def vertex_radius(k, g1, g2):
    """Raggio della sferetta sul vertice di indice k (il P(k+1) dell'utente).

    Gli angoli del triangolo -- P1, P5, P9, cioe' k multiplo di SEG_PER_EDGE --
    sono vertici veri fin dall'inizio e hanno sempre il raggio pieno.

    Gli altri sono punti che dividono i lati e non vogliono ancora dire niente:
    finche' non arriva il loro raggio da P0 restano piu' sottili del cilindro
    degli spigoli, quindi ci spariscono dentro. E ci spariscono davvero, non
    solo "quasi": finche' la faccia non si piega, ogni punto intermedio sta
    esattamente sul segmento che unisce i suoi due vicini, percio' i due
    cilindri che vi si incontrano sono allineati e la sferetta e' del tutto
    coperta."""
    if k % extended_face.SEG_PER_EDGE == 0:
        return VERTEX_RADIUS
    g = g1 if k in SPOKE_GROUP_1 else g2
    return VERTEX_RADIUS_HIDDEN + (VERTEX_RADIUS - VERTEX_RADIUS_HIDDEN) * g


def wire_shape(t1, s, g1, g2):
    """Il bordo del ventaglio: 24 cilindri e 13 sferette in un solo MeshData,
    con numero di vertici e facce sempre uguale.

    g1 e g2 sono indipendenti da s: e' questo che permette di far arrivare gli
    spigoli a forma ferma e poi piegare la faccia a spigoli fermi."""
    P = np.asarray(fan_shape(t1, s).vertices, dtype=float)
    apex = P[extended_face.N_TRIANGLES]
    n = extended_face.N_TRIANGLES

    out = MeshData()
    for k in range(n):                                  # la spezzata esterna
        out.append(_tube(P[k], P[(k + 1) % n], TUBE_RADIUS, caps=False))
    for k in range(n):                                  # i raggi, che crescono da P0
        g = g1 if k in SPOKE_GROUP_1 else g2
        out.append(_tube(apex, apex + g * (P[k] - apex), spoke_radius(g), caps=True))
    for k in range(n):                                  # i vertici della spezzata
        out.append(_sphere(P[k], vertex_radius(k, g1, g2)))
    out.append(_sphere(apex, VERTEX_RADIUS * g1))       # il mozzo, appare coi raggi
    return out


def wire_face_attributes():
    """(use_smooth, material_index) per ogni faccia del bordo, nell'ordine in cui
    `wire_shape` le costruisce.

    Lo smooth va su tutto tranne i tappi dei raggi: se un tappo e' smooth, la
    sua normale si media con quella del fianco sull'anello condiviso e l'orlo
    del cilindro si sfoca. Piatto, l'orlo resta netto e il fianco conserva la
    normale radiale.

    Il materiale distingue gli spigoli della spezzata (e le loro sferette) dai
    raggi che passano per P0 (e dal mozzo)."""
    n = extended_face.N_TRIANGLES
    smooth, material = [], []

    for _ in range(n):                                  # spezzata: senza tappi
        smooth += [True] * TUBE_SIDES
        material += [0] * TUBE_SIDES
    for _ in range(n):                                  # raggi: fianco + 2 tappi
        smooth += [True] * TUBE_SIDES + [False] * (2 * TUBE_SIDES)
        material += [1] * (3 * TUBE_SIDES)
    faces_per_sphere = SPHERE_SEGMENTS * SPHERE_RINGS
    for k in range(n + 1):                              # sferette, mozzo per ultimo
        smooth += [True] * faces_per_sphere
        material += [0 if k < n else 1] * faces_per_sphere
    return smooth, material


def _icosahedron_seats():
    """Per ogni faccia dell'icosaedro: (quaternione, versore normale uscente).

    La posa che porta il triangolo di base del ventaglio sulla faccia i e' una
    rototraslazione pura, e la sua **rotazione non dipende da t1**: scalare
    l'icosaedro non lo gira. Cambia solo la traslazione, che vale
    inraggio(t1) * normale. Qui la rotazione si calcola una volta sola, e lo si
    verifica su un secondo valore di t1 invece di darlo per buono.

    I due controlli si fanno sulla matrice numpy, **prima** di passarla a
    mathutils: mathutils tiene i numeri in singola precisione (32 bit), quindi
    su una posa perfettamente rigida `decompose()` restituisce una scala tipo
    0.99999994. Una soglia da doppia precisione scatterebbe li' a vuoto, e
    l'affermazione da verificare e' geometrica, non sul modo in cui Blender
    memorizza i numeri. Stessa ragione per cui la normale si ricava dalla
    matrice e non dal `loc` di decompose().
    """
    ico = geometry.Polyhedron.ico
    side = (ico.vertices[ico.faces[0][0]] - ico.vertices[ico.faces[0][1]]).length()

    def placement(face, t1):
        """La 4x4 (numpy, doppia precisione) che posa il ventaglio sulla faccia."""
        md = extended_face.make_extended_face(extended_face.phi_from_edge_span(t1))
        corners = [Vector(md.vertices[extended_face.SEG_PER_EDGE * i])
                   for i in range(extended_face.N_EDGES)]
        targets = [ico.vertices[face[j]] * (t1 / side) for j in range(3)]
        return geometry.matrix_from_triples(corners, targets)

    seats = []
    for face in ico.faces:
        m = placement(face, T1_M)
        scale = np.linalg.norm(m[:3, :3], axis=0)
        assert np.abs(scale - 1.0).max() < 1e-9, \
            f"la posa non e' rigida: scala {scale}"
        other = placement(face, T1_M * 0.6)
        assert np.abs(other[:3, :3] - m[:3, :3]).max() < 1e-9, \
            "la rotazione della posa dipende da t1: l'impianto qui sotto non regge"

        _, quat, _ = mathutils.Matrix(
            [[float(x) for x in row] for row in m]).decompose()
        normal = m[:3, 3] / np.linalg.norm(m[:3, 3])
        seats.append((quat, normal))
    return seats


def _inradius_per_edge():
    """Distanza centro-faccia di un icosaedro di lato 1 (vale 0.755761...)."""
    ico = geometry.Polyhedron.ico
    side = (ico.vertices[ico.faces[0][0]] - ico.vertices[ico.faces[0][1]]).length()
    centroid = np.mean([(ico.vertices[i] / side).tup() for i in ico.faces[0]], axis=0)
    return float(np.linalg.norm(centroid))


SEATS = _icosahedron_seats()
INRADIUS_PER_EDGE = _inradius_per_edge()


def seat_location(face, t1):
    """Dove sta l'empty della faccia: sul suo posto nell'icosaedro di lato t1."""
    return tuple(float(c) for c in SEATS[face][1] * (INRADIUS_PER_EDGE * t1))


# =============================================================================
# COSTRUZIONE DELLA SCENA
# =============================================================================

def clear_previous_run():
    """Cancella oggetti, collection e mesh della corsa precedente."""
    collection = bpy.data.collections.get(COLLECTION_NAME)
    if collection is not None:
        for obj in list(collection.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(collection)
    prefixes = tuple(p + "_" for p in (FAN_PREFIX, SEAT_PREFIX, WIRE_PREFIX))
    for obj in list(bpy.data.objects):
        if obj.name.startswith(prefixes) or obj.name == PIVOT_NAME:
            bpy.data.objects.remove(obj, do_unlink=True)
    for name in (MESH_NAME, WIRE_MESH_NAME):
        if name in bpy.data.meshes:
            bpy.data.meshes.remove(bpy.data.meshes[name])


def _action_fcurves(datablock):
    """Le fcurve dell'azione di un datablock (oggetto, o il Key delle shape key).

    Da Blender 4.4 le fcurve stanno nei channelbag degli slot dell'azione e
    `action.fcurves` e' un accesso "legacy" che puo' risultare vuoto; qui si
    prova prima la via vecchia e poi si scende nei layer."""
    anim = getattr(datablock, "animation_data", None)
    if anim is None or anim.action is None:
        return []
    action = anim.action
    fcurves = list(getattr(action, "fcurves", []))
    if fcurves:
        return fcurves
    for layer in getattr(action, "layers", []):
        for strip in layer.strips:
            for bag in getattr(strip, "channelbags", []):
                fcurves.extend(bag.fcurves)
    return fcurves


def _set_interpolation(datablock, mode, data_path=None):
    """Forza il tipo di interpolazione dei keyframe.

    Non e' cosmesi: il tipo dei keyframe nuovi dipende dalle preferenze
    dell'utente (Edit > Preferences > Animation > Default Interpolation), quindi
    senza questo lo stesso script darebbe animazioni diverse su macchine diverse.
    E per la visibilita' CONSTANT e' obbligatorio: un booleano interpolato
    passerebbe da 0.5, cioe' scatterebbe a meta' strada."""
    for fcurve in _action_fcurves(datablock):
        if data_path is not None and data_path not in fcurve.data_path:
            continue
        for point in fcurve.keyframe_points:
            point.interpolation = mode
            if mode == 'BEZIER':
                point.handle_left_type = 'AUTO_CLAMPED'
                point.handle_right_type = 'AUTO_CLAMPED'
        fcurve.update()


def create_pivot(collection):
    """L'empty centrale: tutto il resto gli e' appeso sotto, quindi ruotandolo
    gira il poliedro intero. E' anche il posto giusto da cui riprendere in mano
    il movimento d'insieme, se vuoi cambiarlo a mano."""
    obj = bpy.data.objects.new(PIVOT_NAME, None)
    obj.empty_display_type = 'SPHERE'
    obj.empty_display_size = 0.4
    collection.objects.link(obj)
    obj.rotation_mode = 'XYZ'
    # angoli di Eulero e non quaternione: un quaternione non sa rappresentare
    # piu' di mezzo giro per segmento, e qui i giri sono interi.
    for frame, angle in pivot_keys():
        obj.rotation_euler = (0.0, 0.0, angle)
        obj.keyframe_insert("rotation_euler", index=2, frame=frame)
    _set_interpolation(obj, 'BEZIER', "rotation_euler")
    return obj


def create_seats(collection, pivot, frames):
    """I 20 empty: rotazione costante, posizione che segue l'icosaedro di lato t1.

    Si mette un keyframe solo dove t1 cambia davvero: nelle battute ferme
    bastano due chiavi."""
    changing = [f for f in frames
                if f in (frames[0], frames[-1])
                or params_at(f)[0] != params_at(f - 1)[0]]

    seats = []
    for face in range(len(SEATS)):
        obj = bpy.data.objects.new(f"{SEAT_PREFIX}_{face:02d}", None)
        obj.empty_display_type = 'PLAIN_AXES'
        obj.empty_display_size = 0.3
        collection.objects.link(obj)
        obj.parent = pivot
        obj.matrix_parent_inverse = mathutils.Matrix.Identity(4)
        obj.rotation_mode = 'QUATERNION'
        obj.rotation_quaternion = SEATS[face][0]

        for f in changing:
            obj.location = seat_location(face, params_at(f)[0])
            obj.keyframe_insert("location", frame=f)
        _set_interpolation(obj, 'LINEAR', "location")
        seats.append(obj)
    return seats, changing


def create_fans(collection, seats, mesh):
    """I 20 ventagli: stessa mesh, ognuno figlio del proprio empty.

    Tre canali animati, tutti ritoccabili a mano nel Graph Editor:
      * la Z locale, cioe' l'allontanamento dal posto (uguale per tutti);
      * la rotazione sul proprio asse, 120 gradi per volta (uguale per tutti);
      * la scala, che e' il modo in cui una faccia compare e sparisce (sua).
    """
    z = z_keys()
    fans = []
    for face, seat in enumerate(seats):
        obj = bpy.data.objects.new(f"{FAN_PREFIX}_{face:02d}", mesh)
        collection.objects.link(obj)
        obj.parent = seat
        # matrix_parent_inverse identita': la posa e' gia' espressa nel
        # riferimento dell'empty, ed e' cosi' che la faccia lo segue quando
        # l'icosaedro cresce. bl_utils.set_parent ci metterebbe l'inversa della
        # matrice dell'empty, che annullerebbe proprio quel movimento.
        obj.matrix_parent_inverse = mathutils.Matrix.Identity(4)
        obj.rotation_mode = 'XYZ'

        obj.location = (0.0, 0.0, 0.0)
        for frame, value in z:
            obj.location = (0.0, 0.0, value)
            obj.keyframe_insert("location", index=2, frame=frame)

        for frame in (beat("fase3")[0], beat("fase3")[1],
                      beat("fase5")[0], beat("fase5")[1]):
            obj.rotation_euler = (0.0, 0.0, SPIN_TRACK(frame))
            obj.keyframe_insert("rotation_euler", index=2, frame=frame)

        for frame, value in scale_keys(face):
            obj.scale = (value, value, value)
            obj.keyframe_insert("scale", frame=frame)

        obj.scale = (1.0, 1.0, 1.0)
        _set_interpolation(obj, 'BEZIER')
        fans.append(obj)
    return fans


def create_wires(collection, fans, mesh):
    """Un oggetto-bordo per ogni ventaglio, **figlio del ventaglio stesso**.

    Cosi' eredita tutto -- la posa dell'empty, l'allontanamento, la rotazione
    sul proprio asse e anche la scalatura con cui la faccia compare e sparisce
    -- senza un solo keyframe proprio. E' il vantaggio di far comparire le facce
    scalandole invece che nascondendole: la visibilita' non si eredita, la
    trasformazione si.
    """
    wires = []
    for face, fan in enumerate(fans):
        obj = bpy.data.objects.new(f"{WIRE_PREFIX}_{face:02d}", mesh)
        collection.objects.link(obj)
        obj.parent = fan
        obj.matrix_parent_inverse = mathutils.Matrix.Identity(4)
        wires.append(obj)
    return wires


def _write_shape(block, vertices):
    """Scrive le coordinate in una shape key.

    `foreach_set` e non un ciclo Python: la mesh del bordo ha ~900 vertici e le
    forme distinte sono ~170, quindi un ciclo costerebbe secondi di attesa a
    ogni lancio dello script."""
    block.data.foreach_set("co", [float(c) for v in vertices for c in v])


def bake_shapes(obj, frames, key_fn, shape_fn):
    """Registra la forma di ogni fotogramma come shape key, e ne keyframa i valori.

    Due forme uguali (le battute in cui ne' t1 ne' s si muovono) condividono la
    stessa shape key, percio' il numero di chiavi e' molto minore del numero di
    fotogrammi.

    Ogni chiave vale 1 sui fotogrammi che le appartengono e 0 su quelli
    immediatamente prima e dopo, con interpolazione LINEAR. Cosi' a ogni
    fotogramma intero esattamente una chiave vale 1 e la forma e' esatta (le
    shape key sono relative alla Basis, e con somma dei valori pari a 1 il
    risultato e' la forma stessa); fra un fotogramma e l'altro si ha una
    dissolvenza fra due forme vicine, che e' quello che serve.
    """
    shapes, index, per_frame = [], {}, {}
    for f in frames:
        key = key_fn(f)
        if key not in index:
            index[key] = len(shapes)
            shapes.append(shape_fn(*key))
        per_frame[f] = index[key]

    obj.shape_key_add(name="Basis", from_mix=False)
    blocks = []
    for i, md in enumerate(shapes):
        block = obj.shape_key_add(name=f"shape_{i:04d}", from_mix=False)
        _write_shape(block, md.vertices)
        block.value = 0.0
        blocks.append(block)

    # per ogni chiave, i tratti di fotogrammi consecutivi in cui e' attiva
    runs = {}
    for f in frames:
        i = per_frame[f]
        if i in runs and runs[i][-1][1] == f - 1:
            runs[i][-1][1] = f
        else:
            runs.setdefault(i, []).append([f, f])

    for i, block in enumerate(blocks):
        for first, last in runs.get(i, []):
            marks = [(first, 1.0), (last, 1.0)]
            if first > frames[0]:
                marks.insert(0, (first - 1, 0.0))
            if last < frames[-1]:
                marks.append((last + 1, 0.0))
            for frame, value in marks:
                block.value = value
                block.keyframe_insert("value", frame=frame)
        block.value = 1.0 if i == per_frame[frames[0]] else 0.0

    _set_interpolation(obj.data.shape_keys, 'LINEAR')
    return blocks


def _check_reproduces_M():
    """Con s = 0, t1 = T1_M e z = 0 le 20 facce devono ricostruire make_M().

    E' l'affermazione su cui poggia tutta la regia -- che la stessa posa vada
    bene per i triangoli piatti e per i ventagli aperti -- quindi si misura
    invece di raccontarla."""
    md = fan_shape(T1_M, 0.0)
    P = np.asarray(md.vertices, dtype=float)
    target = np.asarray(extended_face.make_M().vertices, dtype=float)
    worst = 0.0
    for face in range(len(SEATS)):
        quat, _ = SEATS[face]
        R = np.asarray(quat.to_matrix())
        placed = (R @ P.T).T + np.asarray(seat_location(face, T1_M))
        block = target[face * 13:(face + 1) * 13]
        worst = max(worst, float(np.abs(placed - block).max()))
    return worst


def _material(name, color):
    """Materiale col colore dato. Il colore va anche in `diffuse_color`, che e'
    quello che mostra la vista Solid: cosi' i pezzi si distinguono senza dover
    passare a Material Preview."""
    mat = bl_utils.get_or_create_material(name)
    mat.diffuse_color = color
    if mat.use_nodes:
        node = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if node is not None:
            node.inputs["Base Color"].default_value = color
    return mat


def _make_mesh(name, md, materials, smooth=None, material_index=None):
    """Crea la mesh dal MeshData, con i suoi slot di materiale.

    `smooth` e `material_index` sono liste lunghe quanto le facce; se mancano,
    tutte le facce sono piatte e sul primo slot."""
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(md.vertices, [], md.faces)
    mesh.update()
    for mat in materials:
        mesh.materials.append(mat)
    if smooth is not None:
        assert len(smooth) == len(mesh.polygons), \
            f"{name}: {len(smooth)} valori di smooth per {len(mesh.polygons)} facce"
        mesh.polygons.foreach_set("use_smooth", smooth)
    if material_index is not None:
        assert len(material_index) == len(mesh.polygons)
        mesh.polygons.foreach_set("material_index", material_index)
    return mesh


def build():
    clear_previous_run()

    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start = FRAME_START
    scene.frame_end = FRAME_END
    frames = list(range(FRAME_START, FRAME_END + 1))

    collection = bpy.data.collections.new(COLLECTION_NAME)
    scene.collection.children.link(collection)

    mesh = _make_mesh(MESH_NAME, fan_shape(*fan_params_at(FRAME_START)),
                      [_material(MATERIAL_NAME, FAN_COLOR)])
    wire_smooth, wire_material = wire_face_attributes()
    wire_mesh = _make_mesh(WIRE_MESH_NAME, wire_shape(*params_at(FRAME_START)),
                           [_material(EDGE_MATERIAL, EDGE_COLOR),
                            _material(SPOKE_MATERIAL, SPOKE_COLOR)],
                           smooth=wire_smooth, material_index=wire_material)

    pivot = create_pivot(collection)
    seats, changing = create_seats(collection, pivot, frames)
    fans = create_fans(collection, seats, mesh)
    wires = create_wires(collection, fans, wire_mesh)
    blocks = bake_shapes(fans[0], frames, fan_params_at, fan_shape)
    wblocks = bake_shapes(wires[0], frames, params_at, wire_shape)

    scene.frame_set(FRAME_START)

    print(f"[M_story] {len(fans)} ventagli su una sola mesh di {len(mesh.vertices)} "
          f"vertici, {len(seats)} empty; frame {FRAME_START}-{FRAME_END} a {FPS} fps "
          f"({(FRAME_END - FRAME_START + 1) / FPS:.1f} s)")
    print(f"[M_story] bordo: {len(wires)} oggetti su una mesh di "
          f"{len(wire_mesh.vertices)} vertici (spezzata senza tappi, raggi coi "
          f"tappi, {extended_face.N_TRIANGLES + 1} sferette), raggio {TUBE_RADIUS}")
    print(f"[M_story] shape key: {len(blocks)} forme del ventaglio e "
          f"{len(wblocks)} del bordo, su {len(frames)} fotogrammi; keyframe di "
          f"posizione degli empty su {len(changing)} fotogrammi")
    print(f"[M_story] t1: {T1_M:.6f} (M) -> {T1_MAX} -> {T1_MIN} -> {T1_M:.6f}; "
          f"pivot: {sum(t for _, _, t in PIVOT_TURNS):.0f} giri in "
          f"{len(PIVOT_TURNS)} riprese")
    print(f"[M_story] con s=0, t1=T1_M, z=0 le 20 facce ricostruiscono M: "
          f"scarto {_check_reproduces_M():.2e}")
    print("[M_story] nessun handler registrato: a render time non gira Python")
    return pivot, fans, seats, wires, blocks, wblocks


PIVOT, FANS, SEATS_OBJ, WIRES, BLOCKS, WBLOCKS = build()
