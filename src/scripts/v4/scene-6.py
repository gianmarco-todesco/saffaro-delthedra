"""
v4/scene-6.py -- v2/scene-6.py con i gradi di liberta' del ventaglio
mostrati uno per uno: l'icosaedro gira e si apre, una faccia si dispiega nel
ventaglio di 12 triangoli, il ventaglio si flette, tre piani trasparenti
mostrano i vincoli che restano, l'ultimo grado di liberta' fa il suo viaggio,
e alla fine le 20 facce si ricompongono nel poliedro M.

--------------------------------------------------------------------------
CHE COSA CAMBIA RISPETTO A v2/scene-6.py
--------------------------------------------------------------------------
* I colori: le facce sono di un azzurro poco saturo, uniforme (niente
  texture); i raggi del ventaglio, le pieghe, sono azzurro scuro; la spezzata
  esterna e' ancora piu' scura e appena piu' spessa (FACE_SRGB, SPOKE_SRGB,
  EDGE_SRGB, TUBE_RADIUS, SPOKE_RADIUS).
* I tempi (BEATS), 43 s in tutto:
     0-3   l'icosaedro compare girando; nell'ultimo secondo crescono gli
           spigoli
     3-4   le altre facce spariscono, A si stacca, la camera va su A
     4-10  la faccia diventa il ventaglio di 12 (fasi 2-5)
    10-13  la flessione libera (FLEX_*): P0 e gli angoli P1, P5, P9 restano
           fermi; P3, P7, P11 salgono, scendono e tornano al loro posto,
           ognuno sull'arco di cerchio che lo tiene a distanza 1 da P0, uno
           dopo l'altro a FLEX_STAGGER secondi. I vertici in mezzo (P2, P4,
           ...) vanno dove devono, a distanza 1 da P0 e dai due vicini. Il
           ventaglio da solo ha piu' gradi di liberta' di quanti ne usi M.
           Da qui fino a 25 il ventaglio gira lentamente sul proprio asse
           (FAN_SPIN_TURNS, un giro intero)
    13-18  la camera resta ferma e il modello s'inclina attorno a P0 di A
           (tilt_matrix, BELOW_TRACK), finche' la camera vede il ventaglio a
           75 gradi dall'asse invece di 42 (CAMERA_BELOW_DEG); resta
           inclinato fino a quando tutte le facce sono unite (32 s). Da 14.5
           a 16.5 compaiono insieme, come finestrini che si chiudono
           dall'alto in basso, i tre piani (PLANE_*), esattamente i
           pentagoni P1..P5, P5..P9, P9..P1; il bordo inferiore del vetro e'
           un segmento arancio sottilissimo, che nasce in P3 e si allarga
           scendendo fino a diventare il lato P1-P5 (P5-P9, P9-P1):
           reveal_height, chord_shape
    19-25  il grado di liberta' che resta, t1: al massimo, al minimo, al
           massimo; i piani lo seguono restando piani
    25-26  la camera si allarga, compare B col suo triangolo arancio, i piani
           svaniscono (il triangolo arancio di A resta); compaiono i due assi
           di simmetria di A e B (AXIS_*), dal punto in cui si incontrano a
           un po' oltre P0, e l'angolo fra i due come settore (SECTOR_*)
    26-29  A e B si avvicinano con la fessura (si accendono i lati in
           comune), t1 va oltre e torna: i bordi combaciano
    29-31  compaiono le altre 18, gia' staccate, con un ritardo
           proporzionale alla distanza da A (enter_start), e ognuna si
           avvicina al suo posto; triangoli arancio e assi svaniscono; il
           poliedro comincia a girare con ease-in e non si ferma piu'
           (pivot_angle)
    35-36  le facce si staccano un pochino (Z_APART), 36-37 restano cosi',
           37-39 si riuniscono; a 39 si accendono tutti i lati (glow_keys)
    39-43  M gira; gli spigoli restano fino alla fine
* La flessione non e' simmetrica: salendo P3 si allontana da P1 e da P5, e
  poco sopra i 15 gradi P2 e P4 non esistono piu' (dovrebbero stare a
  distanza 1 da tre punti troppo lontani). Scendendo non c'e' limite vicino.
  FLEX_UP_DEG e FLEX_DOWN_DEG sono scelti perche' i due spostamenti si vedano
  simili.
* Il pavimento di v4/scene-2 e v4/scene-5 (FLOOR_*), orizzontale sotto il
  poliedro, col fondo sfumato lontano (BACKGROUND_DEPTH) e il sole largo
  (SUN_SIZE_DEG). Il modello torna dritto fra 32 e 35 s.
* Il bordo e' piu' spesso che in v2 (TUBE_RADIUS 0.011); raggi e spezzata
  sono opachi, senza riflessi (WIRE_SPECULAR, WIRE_ROUGHNESS), cosi' sembrano
  linee e non tubi lucidi.
* Gli assi di A e B passano per il centro del poliedro qualunque siano t1 e
  gli allontanamenti (ogni faccia si muove lungo il proprio asse): il punto
  in cui si incontrano e l'angolo fra loro restano fermi nel modello. Lo
  script li calcola comunque dalla geometria di ogni fotogramma
  (axes_meeting).
* Il motore e' Cycles, a 256 campioni (m_scene.use_cycles).
* I nomi: prefisso S6V4 e collezione scene-6_v4, cosi' la scena puo' stare
  nello stesso file delle altre.

Quello che segue e' la descrizione di v2, che vale ancora salvo dove detto
sopra (il giro del ventaglio di 120 gradi non c'e' piu', la texture nemmeno,
i giri del poliedro sono in pivot_angle e non in PIVOT_TURNS, e z_keys e'
per faccia).

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
* pivot_angle() -> i giri del poliedro su se stesso (POLY_*).
* T1_TRACK      -> il viaggio del grado di liberta'.
* S_TRACK       -> quando la faccia si piega.
* G1_TRACK, G2_TRACK, SPOKE_GROUP_1/2 -> quando arrivano i raggi del bordo,
                   e quali.
* spin_keys()   -> la rotazione del ventaglio A sul proprio asse.
* WIRE_TRACK    -> quando compaiono gli spigoli.
* z_keys(face)  -> l'allontanamento dal centro, faccia per faccia.
* scale_keys()  -> quando una faccia compare e sparisce; enter_start() decide
                   quando rientrano le 18 finali (ENTER_*, APPEAR_*, JOIN_*).
* FOLLOW_TRACK, PAIR_TRACK, DISTANCE_TRACK, LOWER_TRACK -> che cosa
                   inquadra la camera, da quanto lontano e da dove.
* BELOW_TRACK, tilt_matrix() -> l'inclinazione del modello.
* reveal_height(), plane_alpha_keys(), chord_fade_keys(),
  axes_fade_keys() -> piani, triangoli arancio, assi.
* glow_keys()   -> quando si accendono i lati.

--------------------------------------------------------------------------
IL MOVIMENTO D'INSIEME
--------------------------------------------------------------------------
Tutto e' appeso a un empty centrale (PIVOT_NAME): il poliedro compare
scalandolo, e gira facendo girare lui (pivot_angle). Sopra il pivot c'e' un
secondo empty (TILT_NAME) che inclina tutto il modello mentre si guardano i
piani (tilt_matrix): un keyframe per fotogramma. Le battute sono quelle
di BEATS, descritte in testa; i tempi sono scritti accanto a ciascuna.

Fessura o sovrapposizione: si veda piu' sotto. Il ventaglio A gira sul suo
asse un numero intero di giri, cosi' quando entra B e' di nuovo nella posa di
partenza e il lato che si accende e' quello che tocca B.

La camera tiene al centro il vertice centrale P0 della faccia A, e non il
centro del rettangolo che la faccia occupa: P0 sta sull'asse del ventaglio, quindi
non si muove quando la faccia gira, mentre il rettangolo cambia, e la camera che
lo rincorreva oscillava. Intanto si abbassa un po' (CAMERA_LOWER_DEG), per
mostrare la parte bassa del ventaglio.

Fessura o sovrapposizione: con t1 sopra T1_M le due spezzate in comune restano
staccate, sotto si incrociano (misurato: a t1 = 1.2 la fessura e' 0.38, a 0.6 la
sovrapposizione e' 0.47). Per questo il viaggio di t1 finisce al massimo prima
che entri B.

--------------------------------------------------------------------------
IL VIDEO: CAMERA, FONDO, MATERIALI
--------------------------------------------------------------------------
Lo script crea anche la camera (S6V2_camera), la luce, il mondo e il fondo, come
M_video2: i nomi nuovi hanno il prefisso S6V2_.

* la camera guarda sempre dalla stessa direzione (CAMERA_DIRECTION) e si sposta
  soltanto: inquadra il poliedro intero, poi segue la faccia A mentre e' sola
  tenendola al centro, poi la coppia A+B, e infine torna al poliedro. Il centro
  da seguire si calcola dalla geometria vera di ogni fotogramma (forma, posto,
  allontanamento, rotazione), letta dalle stesse fcurve che Blender usa;
* il fondo e' quello di M_video2: un piano figlio della camera, sfumato fra i
  quattro angoli (m_scene.build_background);
* le facce hanno la texture di M (FACE_SHADING): i 12 triangoli del ventaglio
  sono equilateri come quelli di M, quindi prendono la stessa UV. La luce
  viene da un cielo fisico col sole basso (WORLD); in alternativa, il
  materiale "dipinto" di M_video2 e il suo mondo;
* i fili: la spezzata esterna in oro, i raggi che passano per P0 in un colore
  diverso (SPOKE_COLOR). I tre lati della spezzata hanno ciascuno il suo
  materiale, che si accende leggendo la proprieta' glow0/glow1/glow2
  dell'oggetto-filo: i keyframe stanno in glow_keys(), e il bagliore lo fa il
  compositor (m_scene.setup_glare), che sostituisce quello della scena.
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
        txt = bpy.data.texts.get("scene-6.py")
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
import geometry, bl_utils, extended_face
import bl_anim, m_scene
for _mod in (geometry, bl_utils, extended_face, bl_anim, m_scene):
    importlib.reload(_mod)

from geometry import Vector, MeshData


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

COLLECTION_NAME = "scene-6_v4"
MESH_NAME       = "S6V4_fan"      # l'unico datablock di mesh: 13 vertici
FAN_PREFIX      = "S6V4_fan"      # S6V4_fan_00 ... S6V4_fan_19
SEAT_PREFIX     = "S6V4_seat"     # S6V4_seat_00 ... S6V4_seat_19: gli empty che tengono
                                 # il posto delle 20 facce sull'icosaedro
PLANE_NAME      = "S6V4_planes"   # i tre piani trasparenti, sulla faccia A
# --- il video: camera, luce, fondo, materiali (nomi S6V4_...) ---
PREFIX     = "S6V4"
# saffaro/assets, accanto al repository: src/libs -> src -> saffaro-delthedra -> saffaro
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(_LIBS))), "assets")
RESOLUTION = (1920, 1080)
USE_STANDARD_VIEW = True         # i colori escono come sono scritti (con AgX no)

# il fondo e la luce d'ambiente: come M_video2
BACKGROUND_CORNERS_SRGB = {
    "top_left":     (34, 46, 70),
    "top_right":    (16, 22, 38),
    "bottom_left":  (20, 28, 46),
    "bottom_right": (6, 8, 16),
}
BACKGROUND_BLEED = 1.02
AMBIENT          = 0.5           # tocca solo i fili: le facce sono emissive

# La luce, nel riferimento della camera (X a destra, Y in alto, Z verso chi
# guarda): verso cui va. Da sinistra e un po' dall'alto, perpendicolare alla
# direzione di vista: e' cosi' che i toni delle facce visibili tornano con quelli
# del quadro (si veda m_scene.PAINTING_PALETTE). La camera non ruota mai, quindi
# e' anche una direzione fissa nel mondo.
LIGHT_IN_CAMERA = (0.866, -0.5, 0.0)
LIGHT_STRENGTH  = 3.0            # con WORLD = 'FLAT': il sole illumina solo i fili

# Le facce: un azzurro poco saturo, uniforme, su un Principled (l'ombreggiatura
# la fa la luce). sRGB 0..255.
FACE_SRGB      = (118, 148, 178)
FACE_ROUGHNESS = 0.75

# Se facce e fili proiettano ombra. No, come nel quadro, dove ogni faccia ha
# una tinta sola: il ventaglio e' concavo, e col sole basso un triangolo fa
# ombra sui vicini con un bordo netto (il disco del sole e' piccolo) che parte
# dall'apice -- perche' a proiettarlo e' un raggio -- e taglia la faccia in
# due colori. I fili, con le loro ombre sottili, righerebbero le facce.
CAST_SHADOWS = False

# Il mondo:
#   'SKY'  -> cielo fisico (Sky Texture) col sole basso, che illumina tutto; il
#             sole sta dalla parte da cui arriva LIGHT_IN_CAMERA, cioe' a
#             sinistra della camera. Niente lampada: il sole e' quello del cielo
#   'FLAT' -> fondo uniforme poco luminoso piu' una lampada Sun (come M_video2)
# In tutti e due i casi quello che si vede dietro e' il fondo sfumato.
WORLD               = 'SKY'
SKY_SUN_ELEVATION   = 15.0       # gradi sopra l'orizzonte
SKY_STRENGTH        = 0.1        # il cielo e' in unita' fisiche: va tarato sui render

# --- la camera ---
# Guarda sempre dalla direzione CAMERA_DIRECTION (dal punto inquadrato verso la
# camera: e' quella della camera fatta a mano in M_story.blend) e si sposta
# soltanto, senza ruotare.
CAMERA_DIRECTION = (9.216, 1.316, 7.532)
CAMERA_LENS      = 50.0          # mm, sensore da 36
CAMERA_ICO       = 8.0           # distanza all'inizio, sull'icosaedro (piccolo)
CAMERA_LOWER_DEG = 12.0          # di quanto la camera si abbassa, dall'inizio al ventaglio di 12
CAMERA_FAR       = 16.0          # distanza quando inquadra il poliedro intero
CAMERA_NEAR      = 7.0           # ... la faccia A da sola
CAMERA_PAIR      = 11.5          # ... le facce A e B
BACKGROUND_DEPTH = 300.0         # di quanto il fondo sta davanti alla camera: lontano,
                                 # dietro l'orizzonte del pavimento (come v4/scene-2)

# --- il pavimento: quello di v4/scene-2 e v4/scene-5 ---
# Orizzontale, FLOOR_BELOW sotto il centro del poliedro (M ha circonraggio
# 2.27, e le facce staccate arrivano a 2.7). Le facce non fanno ombra
# (CAST_SHADOWS), come nelle altre scene.
FLOOR_SRGB      = (30, 38, 56)
FLOOR_ROUGHNESS = 0.85
FLOOR_SPECULAR  = 0.05
FLOOR_SIZE      = 400.0
FLOOR_BELOW     = 3.2
SUN_SIZE_DEG    = 8.0            # il disco del sole, largo come nelle altre scene

# --- il bordo: cilindri sugli spigoli, sferette sui vertici ---
WIRE_MESH_NAME  = "S6V4_fan_wire" # la seconda mesh condivisa
WIRE_PREFIX     = "S6V4_wire"     # S6V4_wire_00 ... S6V4_wire_19
EDGE_SRGB       = (16, 34, 62)    # la spezzata esterna: piu' scura dei raggi
SPOKE_SRGB      = (36, 70, 118)   # i raggi che passano per P0, le pieghe: azzurro scuro

# I lati che si accendono: la spezzata esterna e' fatta di tre lati di 4
# segmenti, e ognuno ha il suo materiale con la sua proprieta' (glow0, glow1,
# glow2 sull'oggetto-filo). Il bagliore lo fa il compositor: GLARE_THRESHOLD
# sopra 1 perche' brillino solo i fili accesi.
GLOW_COLOR        = (1.0, 0.85, 0.45)
GLOW_STRENGTH     = 6.0
GLOW_RAMP_SECONDS = 0.4          # quanto ci mette un lato ad accendersi o spegnersi
GLARE_THRESHOLD   = 1.5
GLARE_STRENGTH    = 1.0
GLARE_SIZE        = 0.5

TUBE_RADIUS     = 0.011          # la spezzata esterna, in lati di triangolo (il lato vale 1)
SPOKE_RADIUS    = 0.006          # i raggi da P0, fra un triangolo e il vicino: appena piu' sottili
TUBE_SIDES      = 8
SPOKE_RAMP      = 0.12           # in quanta parte della crescita un raggio
                                 # passa da punta a tubo pieno
VERTEX_RADIUS   = TUBE_RADIUS    # le sferette sui vertici: grandi come i cilindri
VERTEX_RADIUS_HIDDEN = 0.0055    # < TUBE_RADIUS: la sferetta di un vertice che
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
# Dove arriva t1 quando oltrepassa il valore giusto: sotto T1_M, quindi le due
# facce si sovrappongono (di 0.10 a t1 = 0.85), prima di tornare a T1_M.
T1_OVERSHOOT = 0.85

PIVOT_NAME = "S6V4_pivot"           # l'empty centrale: ruotandolo gira tutto
Z_OUT = 0.45                     # di quanto le facce si staccano dal loro posto

# le due facce protagoniste: 0 e 1 dell'icosaedro condividono uno spigolo
FACE_A = 0
FACE_B = 1

# --- la flessione ---
# P0, P1, P5, P9 fermi. P3, P7, P11 (indici di libreria 2, 6, 10) restano a
# distanza 1 da P0 e cambiano solo l'angolo con l'asse del ventaglio (z
# locale, verso l'apice): un arco di cerchio in un piano verticale. Ognuno fa
# un'oscillazione a(u) = sin(2 pi smoothstep(u)) -- al suo posto, su, giu', al
# suo posto, fermo agli estremi -- in FLEX_SECONDS, partendo FLEX_STAGGER dopo
# il precedente. Su di FLEX_UP_DEG * a, giu' di FLEX_DOWN_DEG * |a|.
FLEX_UP_DEG   = 11.0             # il limite e' poco sopra i 15 gradi (si veda sopra)
FLEX_DOWN_DEG = 14.0
FLEX_STAGGER  = 0.4              # secondi fra un vertice e il successivo
FLEX_MIN_H2   = 0.05             # margine sotto cui un vertice pari e' quasi impossibile
FLEX_VERTICES = (2, 6, 10)       # P3, P7, P11

# --- i piani ---
# Tre facce trasparenti, esattamente i pentagoni P1..P5, P5..P9, P9..P1, e il
# loro quinto lato -- P1-P5, che non e' uno spigolo del ventaglio -- in arancio.
PLANE_SRGB    = (255, 244, 214)
PLANE_ALPHA   = 0.35             # quanto sono opachi, a pieno
PLANE_GLOW    = 0.8              # la forza dell'emissione: sotto 1, non brillano
# I piani compaiono tutti e tre insieme, come finestrini che si chiudono: il
# vetro scende dall'alto (P3) verso il basso; il lato arancio e' il suo bordo
# inferiore, cioe' il segmento che manca alla parte di piano che si vede, e
# diventa il lato P1-P5 quando il vetro e' arrivato giu'.
PLANE_WIPE_START   = 1.5         # secondi dall'inizio di verso_basso
PLANE_WIPE_SECONDS = 2.0
PLANE_WIPE_BAND    = 0.02        # il bordo sfumato del vetro, in lati di triangolo
CHORD_SRGB    = (255, 128, 16)   # il lato P1-P5: arancio
CHORD_RADIUS  = 0.0035           # sottilissimo: una linea, piu' sottile dei raggi
CHORD_NAME    = "S6V4_chords"    # il triangolo arancio, sul ventaglio A e sul B

# --- i fili senza riflessi ---
# I raggi e la spezzata devono sembrare linee e non tubi lucidi: niente
# componente speculare, ruvidita' piena.
WIRE_SPECULAR = 0.0
WIRE_ROUGHNESS = 1.0

# --- i due assi di simmetria, quando entra B ---
# Le rette per P0 lungo l'asse del ventaglio A e del ventaglio B, dal punto in
# cui si incontrano fino a un po' oltre P0, e l'angolo fra le due come un
# piccolo settore circolare.
AXES_NAME     = "S6V4_axes"
AXIS_SRGB     = (255, 250, 222)  # giallo chiarissimo, quasi bianco
AXIS_GLOW     = 1.0
AXIS_RADIUS   = 0.006
AXIS_BEYOND   = 1.3              # di quanto l'asse va oltre P0, punta compresa:
                                 # P3, P7, P11 stanno 0.58 sopra P0, quindi sporge
                                 # di circa 0.7 oltre il ventaglio
ARROW_LENGTH  = 0.16             # la punta: un cono affilato, dello stesso materiale
ARROW_RADIUS  = 0.032
SECTOR_RADIUS = 0.35
SECTOR_ALPHA  = 0.55
SECTOR_SEGMENTS = 16

# --- mentre si guardano i piani, il modello s'inclina ---
# Il ventaglio di M e' una corona: gli angoli P1, P5, P9 e i lati arancio
# stanno in basso (z = 0 locale), P0 a 0.85 e P3, P7, P11 a 1.43. Per vederli
# la camera resta ferma e il modello gira attorno a P0 della faccia A, finche'
# la camera vede il ventaglio a CAMERA_BELOW_DEG gradi dal suo asse
# (all'inizio della battuta e' a 42). L'asse di rotazione (tilt_frame) e'
# perpendicolare all'asse del ventaglio e alla direzione della camera: quasi
# l'orizzontale dell'immagine. Il risultato e' lo stesso della camera che
# scende, ma il pavimento e l'orizzonte restano dove sono.
CAMERA_BELOW_DEG = 75.0
CAMERA_BELOW     = 7.5           # la distanza da P0, mentre si guardano i piani
TILT_NAME        = "S6V4_tilt"   # l'empty che inclina il modello: padre del pivot

# --- le rotazioni ---
# Il ventaglio A gira sul proprio asse (z locale, una simmetria di ordine 3)
# da quando e' formato a quando entra B. I giri devono essere interi: con un
# terzo di giro la forma tornerebbe la stessa, ma i lati della mesh no, e il
# lato che si accende non sarebbe piu' quello che tocca B.
FAN_SPIN_TURNS = 1
# Il poliedro: un giro con ease in/out mentre compare, poi fermo; dall'arrivo
# delle altre facce riparte con ease-in (POLY_SPIN_UP secondi per arrivare a
# regime) e gira fino alla fine, un giro ogni POLY_TURN_SECONDS.
POLY_TURN_SECONDS = 12.0
POLY_SPIN_UP      = 3.0

# --- le altre 18 facce ---
# Compaiono gia' staccate (a Z_OUT) con un ritardo proporzionale alla
# distanza dal centro della faccia A (al piu' ENTER_WINDOW secondi), in
# APPEAR_SECONDS; JOIN_DELAY dopo l'inizio della comparsa cominciano ad
# avvicinarsi, e in JOIN_SECONDS sono al loro posto.
ENTER_WINDOW   = 1.5
APPEAR_SECONDS = 0.5
JOIN_DELAY     = 0.3
JOIN_SECONDS   = 1.0
Z_APART        = 0.25            # di quanto si staccano verso la fine ("un pochino")


# =============================================================================
# LA REGIA
# =============================================================================

BEATS = [
    ("comparsa",      3.0),  # l'icosaedro cresce da niente girando; nell'ultimo
                             # secondo crescono gli spigoli (0-3)
    ("via_le_altre",  1.0),  # le altre si rimpiccioliscono, A si stacca, la camera
                             # va sulla faccia, finisce il giro (4)
    ("fase2",         1.2),  # arrivano i primi 6 raggi
    ("fase3",         1.8),  # diventa 6 triangoli (7)
    ("fase4",         1.2),  # arrivano gli altri 6 raggi
    ("fase5",         1.8),  # diventa 12 triangoli (10)
    ("flessione",     3.0),  # il movimento libero; il ventaglio comincia a girare (13)
    ("verso_basso",   5.0),  # la camera scende sotto il ventaglio, compaiono i
                             # tre piani e i lati arancio (18)
    ("sosta",         1.0),  # (19)
    ("t1_flex",       6.0),  # il grado di liberta' che resta, t1: i piani restano
                             # piani; finisce al massimo (25)
    ("entra_B",       1.0),  # la camera torna e si allarga, compare B (26)
    ("avvicina",      1.0),  # A e B si toccano sui triangoli di base, con la
                             # fessura; si accendono i lati in comune (27)
    ("t1_oltre",      1.0),  # t1 oltre il valore giusto: sovrapposizione (28)
    ("t1_giusto",     1.0),  # t1 al valore giusto: i bordi combaciano (29)
    ("entrano_tutte", 2.0),  # compaiono le altre 18, staccate, e si avvicinano;
                             # il poliedro comincia a girare (31)
    ("unione",        4.0),  # M si chiude e gira (35)
    ("stacca",        1.0),  # le facce si allontanano un pochino (36)
    ("pausa",         1.0),  # ... restano cosi' (37)
    ("risalda",       2.0),  # ... e si riuniscono; bagliore su tutti i lati (39)
    ("finale",        4.0),  # M gira (43)
]

WIRE_GROW_SECONDS  = 1.0      # gli spigoli crescono nell'ultimo secondo della comparsa


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


def at(name, seconds):
    """Il fotogramma `seconds` secondi dopo l'inizio della battuta."""
    return beat(name)[0] + int(round(seconds * FPS))


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


# Il canale t1. In t1_flex: dal valore giusto al massimo, al minimo, e di nuovo
# al massimo (i piani lo seguono restando piani); resta li' mentre entra B e le
# due si avvicinano -- sopra T1_M, quindi con la fessura -- poi scende oltre
# T1_M fino alla sovrapposizione, e torna a T1_M, che e' il momento in cui i
# bordi combaciano. Nei punti di inversione la velocita' e' zero.
T1_TRACK = Track([
    (beat("t1_flex")[0],   T1_M),
    (at("t1_flex", 1.5),   T1_MAX),
    (at("t1_flex", 4.0),   T1_MIN),
    (beat("t1_flex")[1],   T1_MAX),
    (beat("t1_oltre")[0],  T1_MAX),
    (beat("t1_oltre")[1],  T1_OVERSHOOT),
    (beat("t1_giusto")[1], T1_M),
])

def flex_at(frame):
    """Le ampiezze della flessione di P3, P7, P11, ognuna in [-1, 1] (> 0 su).
    Ogni vertice fa un'oscillazione sola nella sua finestra; le finestre
    riempiono la battuta, sfalsate di FLEX_STAGGER."""
    f0, f1 = beat("flessione")
    lag = FLEX_STAGGER * FPS
    span = (f1 - f0) - lag * (len(FLEX_VERTICES) - 1)
    out = []
    for j in range(len(FLEX_VERTICES)):
        u = (frame - f0 - j * lag) / span
        out.append(math.sin(2.0 * math.pi * smoothstep(u, 0.0, 1.0)) if 0.0 < u < 1.0 else 0.0)
    return tuple(out)


def plane_wipe_span():
    """(primo, ultimo) fotogramma in cui i tre vetri scendono, insieme,
    mentre il modello s'inclina."""
    start = at("verso_basso", PLANE_WIPE_START)
    return start, start + int(round(PLANE_WIPE_SECONDS * FPS))


_PLANE_TOP = None


def reveal_height(frame):
    """La quota (z locale del ventaglio) sopra cui i piani si vedono: scende
    con ease in/out da sopra P3 a sotto il lato P1-P5. Prima della tendina
    i piani non si vedono, dopo si vedono interi."""
    global _PLANE_TOP
    if _PLANE_TOP is None:
        _PLANE_TOP = plane_top()
    top, bottom = _PLANE_TOP + PLANE_WIPE_BAND, -PLANE_WIPE_BAND
    return top + (bottom - top) * smoothstep(frame, *plane_wipe_span())


def chord_height(frame):
    """La quota del lato arancio: a meta' del bordo sfumato del vetro. Alla
    fine sta sotto zero, cioe' il lato arancio e' P1-P5 intero."""
    return round(reveal_height(frame) + 0.5 * PLANE_WIPE_BAND, PARAM_DECIMALS)


def plane_reveal_keys():
    """I keyframe (frame, quota) della tendina, uno per fotogramma mentre
    scende (da interpolare LINEAR): cosi' la quota nel materiale e' la stessa
    che usa il lato arancio, fotogramma per fotogramma."""
    w0, w1 = plane_wipe_span()
    return [(FRAME_START, reveal_height(FRAME_START))] + [
        (f, reveal_height(f)) for f in range(w0, w1 + 1)]


def plane_alpha_keys():
    """L'opacita' dei piani: piena finche' non entra B, poi svaniscono
    mentre B compare."""
    b0, b1 = beat("entra_B")
    return [(FRAME_START, PLANE_ALPHA), (b0, PLANE_ALPHA), (b1, 0.0)]


def chord_fade_keys(face, side):
    """I keyframe (frame, opacita') del lato arancio `side` sul ventaglio
    `face`. Su A c'e' da quando i vetri cominciano a scendere (all'inizio e'
    lungo zero, in cima: si allarga scendendo, si veda chord_shape); su B da
    quando B compare (cresce con lui). Restano tutti finche' non entrano le
    altre, e svaniscono nel primo secondo."""
    v0 = beat("entrano_tutte")[0]
    tail = [(v0, 1.0), (v0 + FPS, 0.0)]
    if face == FACE_A:
        w0 = plane_wipe_span()[0]
        return [(FRAME_START, 0.0), (w0 - 1, 0.0), (w0, 1.0)] + tail
    b0 = beat("entra_B")[0]
    return [(FRAME_START, 0.0), (b0 - 1, 0.0), (b0, 1.0)] + tail


def axes_fade_keys(peak):
    """I due assi e il settore: compaiono con B, svaniscono quando entrano
    le altre."""
    b0, b1 = beat("entra_B")
    v0 = beat("entrano_tutte")[0]
    return [(FRAME_START, 0.0), (b0, 0.0), (b1, peak), (v0, peak), (v0 + FPS, 0.0)]

# Gli spigoli: 0 = invisibili (cilindri e sferette di raggio zero), 1 = pieni.
# Crescono nell'ultimo secondo della comparsa e restano fino alla fine.
WIRE_TRACK = Track([
    (beat("comparsa")[1] - int(round(WIRE_GROW_SECONDS * FPS)), 0.0),
    (beat("comparsa")[1], 1.0),
])

# Quanto la camera si e' abbassata: 0 = CAMERA_DIRECTION, 1 = CAMERA_LOWER_DEG
# piu' in basso. Comincia subito e finisce quando il ventaglio di 12 e' formato.
LOWER_TRACK = Track([
    (FRAME_START, 0.0),
    (beat("fase5")[1], 1.0),
])

# L'inclinazione del modello (1 = la camera vede il ventaglio A a
# CAMERA_BELOW_DEG dal suo asse): cresce per tutta verso_basso e resta mentre
# entra B, mentre le due combaciano e finche' le altre 18 non si sono unite
# (l'ultima a 31.8 s); torna a zero nei tre secondi dopo, mentre M gira.
BELOW_TRACK = Track([
    (beat("verso_basso")[0], 0.0),
    (beat("verso_basso")[1], 1.0),
    (at("unione", 1.0), 1.0),
    (beat("unione")[1], 0.0),
])


# Che cosa inquadra la camera. FOLLOW: 0 = il centro del poliedro, 1 = la
# faccia (o la coppia); PAIR: 0 = la faccia A, 1 = le facce A e B insieme.
# DISTANCE: quanto la camera sta lontana da quello che inquadra.
FOLLOW_TRACK = Track([
    (beat("via_le_altre")[0], 0.0),
    (beat("via_le_altre")[1], 1.0),
    (beat("entrano_tutte")[0], 1.0),
    (at("entrano_tutte", 2.5), 0.0),
])
PAIR_TRACK = Track([
    (beat("entra_B")[0], 0.0),
    (beat("entra_B")[1], 1.0),
])
DISTANCE_TRACK = Track([
    (beat("via_le_altre")[0], CAMERA_ICO),
    (beat("via_le_altre")[1], CAMERA_NEAR),
    (beat("verso_basso")[0], CAMERA_NEAR),
    (beat("verso_basso")[1], CAMERA_BELOW),
    (beat("entra_B")[0], CAMERA_BELOW),
    (beat("entra_B")[1], CAMERA_PAIR),
    (beat("entrano_tutte")[0], CAMERA_PAIR),
    (at("entrano_tutte", 2.5), CAMERA_FAR),
])


PARAM_DECIMALS = 7      # a quante cifre si arrotondano i parametri


def params_at(frame):
    """(t1, s, a, g1, g2, w) del fotogramma. E' l'unica fonte dei parametri.

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
            tuple(round(x, PARAM_DECIMALS) for x in flex_at(frame)),
            round(G1_TRACK(frame), PARAM_DECIMALS),
            round(G2_TRACK(frame), PARAM_DECIMALS),
            round(WIRE_TRACK(frame), PARAM_DECIMALS))


def fan_params_at(frame):
    """I parametri da cui dipende il ventaglio: solo (t1, s, a)."""
    return params_at(frame)[:3]


def enter_distance(face):
    """Distanza fra il centro della faccia e quello della faccia A, sulla
    sfera unitaria delle normali (0 per A, 2 per la faccia opposta)."""
    return float(np.linalg.norm(SEATS[face][1] - SEATS[FACE_A][1]))


def enter_start(face):
    """Il fotogramma in cui una delle 18 facce comincia a comparire: un
    ritardo proporzionale alla distanza da A, al piu' ENTER_WINDOW secondi.
    Le facce alla stessa distanza entrano insieme, ad anelli."""
    d_max = max(enter_distance(i) for i in range(len(SEATS)))
    return at("entrano_tutte", ENTER_WINDOW * enter_distance(face) / d_max)


def z_keys(face):
    """I keyframe (frame, z) dell'allontanamento dal centro della faccia.

    z = 0 vuol dire "al suo posto": qualunque sia t1, le 20 facce hanno i
    triangoli di base che formano l'icosaedro di lato t1 e quindi si toccano
    sugli spigoli. Con t1 = T1_M e s = 0 e' esattamente il poliedro M.

    Tutte si staccano mentre spariscono (via_le_altre). A e B tornano al
    loro posto in avvicina; le altre 18, dopo essere ricomparse staccate, si
    avvicinano ognuna col suo ritardo (enter_start). Alla fine tutte si
    staccano un pochino (Z_APART) e si riuniscono.

    Finiscono in Blender come keyframe veri sul solo canale Z, quindi si possono
    ritoccare a mano nel Graph Editor senza rilanciare lo script.
    """
    v0, v1 = beat("via_le_altre")
    keys = [(v0, 0.0), (v1, Z_OUT)]
    if face in (FACE_A, FACE_B):
        keys += [(beat("avvicina")[0], Z_OUT), (beat("avvicina")[1], 0.0)]
    else:
        j0 = enter_start(face) + int(round(JOIN_DELAY * FPS))
        keys += [(j0, Z_OUT), (j0 + int(round(JOIN_SECONDS * FPS)), 0.0)]
    keys += [
        (beat("stacca")[0], 0.0),
        (beat("stacca")[1], Z_APART),     # M si apre un pochino...
        (beat("risalda")[0], Z_APART),
        (beat("risalda")[1], 0.0),        # ... e si richiude
    ]
    return keys


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

    start = enter_start(face)
    return keys + [(start, 0.0), (start + int(round(APPEAR_SECONDS * FPS)), 1.0)]


def spin_keys(face):
    """I keyframe (frame, angolo) della rotazione del ventaglio sul proprio
    asse: solo A, da quando il ventaglio e' formato a quando entra B."""
    assert float(FAN_SPIN_TURNS).is_integer(), "FAN_SPIN_TURNS dev'essere intero"
    if face != FACE_A:
        return [(FRAME_START, 0.0)]
    return [(beat("flessione")[0], 0.0),
            (beat("t1_flex")[1], 2.0 * math.pi * FAN_SPIN_TURNS)]


def shared_side(face, other):
    """Il lato della spezzata di `face` (0, 1 o 2) che sta sullo spigolo in
    comune con `other`. Il lato i va dall'angolo i all'angolo i+1, e l'angolo
    i del ventaglio e' posato sul vertice ico.faces[face][i]
    (_icosahedron_seats): quindi il lato e' quello i cui due vertici sono i
    due che le facce hanno in comune."""
    ico = geometry.Polyhedron.ico
    common = set(ico.faces[face]) & set(ico.faces[other])
    for i in range(extended_face.N_EDGES):
        corners = {ico.faces[face][i], ico.faces[face][(i + 1) % extended_face.N_EDGES]}
        if corners == common:
            return i
    raise ValueError(f"le facce {face} e {other} non hanno uno spigolo in comune")


def glow_keys():
    """I keyframe dei lati accesi: {(faccia, lato della mesh): [(frame, valore)]},
    con valore 0 = spento e 1 = acceso.

    Due momenti:
      * i lati in comune di A e B, su tutte e due, da quando le due facce si
        avvicinano fino a quando entrano le altre;
      * tutti i lati di tutte le facce, quando M si riunisce alla fine
        (pieni alla fine di risalda, poi si spengono)."""
    ramp = GLOW_RAMP_SECONDS * FPS
    first, last = beat("avvicina")[0], beat("entrano_tutte")[0]
    contact = [(first, 0.0), (first + ramp, 1.0), (last, 1.0), (last + ramp, 0.0)]
    peak = beat("risalda")[1]
    flash = [(peak - 2 * ramp, 0.0), (peak, 1.0), (peak + 0.5 * FPS, 1.0),
             (peak + 0.5 * FPS + 2 * ramp, 0.0)]
    keys = {(face, side): [(FRAME_START, 0.0)] + flash
            for face in range(len(SEATS)) for side in range(extended_face.N_EDGES)}
    for face, other in ((FACE_A, FACE_B), (FACE_B, FACE_A)):
        keys[(face, shared_side(face, other))] = sorted(contact + flash)
    return keys


def pivot_angle(frame):
    """La rotazione del pivot centrale: un giro con ease in/out durante la
    comparsa (fino alla fine di via_le_altre), poi ferma; da entrano_tutte
    riparte con ease-in -- la velocita' sale linearmente per POLY_SPIN_UP
    secondi -- e gira a velocita' costante fino alla fine."""
    angle = 2.0 * math.pi * smoothstep(frame, FRAME_START, beat("via_le_altre")[1])
    t = (frame - beat("entrano_tutte")[0]) / FPS
    if t > 0.0:
        omega = 2.0 * math.pi / POLY_TURN_SECONDS
        if t < POLY_SPIN_UP:
            angle += omega * t * t / (2.0 * POLY_SPIN_UP)
        else:
            angle += omega * (t - 0.5 * POLY_SPIN_UP)
    return angle


# =============================================================================
# GEOMETRIA
# =============================================================================

def fan_shape(t1, s, a=(0.0, 0.0, 0.0)):
    """La faccia estesa per i parametri (t1, s, a), come MeshData di 13 vertici.

    `flatten2_extended_face` si applica direttamente alla faccia estesa e non al
    risultato di flatten1: usa solo P1, P5, P9, che flatten1 lascia fermi, e il
    risultato e' identico (verificato).
    """
    md = extended_face.make_extended_face(extended_face.phi_from_edge_span(t1))
    if any(a):
        if s != 0.0:
            raise ValueError("la flessione vale solo per il ventaglio di 12 (s = 0)")
        return flexed(md, a)
    flat1 = extended_face.flatten1_extended_face(md)
    if s <= 0.5:
        return extended_face.morph(md, flat1, 2.0 * s)
    flat2 = extended_face.flatten2_extended_face(md)
    return extended_face.morph(flat1, flat2, 2.0 * s - 1.0)


def _equidistant(p0, p, q, reference):
    """Il punto a distanza 1 da p0, p e q, dalla parte di `reference`; e il
    quadrato della sua distanza dal piano dei tre (che dice quanto si e'
    lontani dal caso impossibile, in cui vale zero)."""
    u, v = p - p0, q - p0
    n = np.cross(u, v)
    centre = p0 + np.linalg.solve(np.array([u, v, n]), [0.5 * (u @ u), 0.5 * (v @ v), 0.0])
    h2 = 1.0 - float((centre - p0) @ (centre - p0))
    if h2 <= 0.0:
        raise ValueError(f"flessione impossibile: nessun punto a distanza 1 (h2 = {h2:.3f})")
    offset = n / np.linalg.norm(n) * math.sqrt(h2)
    if (reference - centre) @ offset < 0.0:
        offset = -offset
    return centre + offset, h2


def flexed(md, a):
    """Il ventaglio `md` (s = 0) flesso di `a` = (a3, a7, a11): si veda
    FLEX_UP_DEG.

    P3, P7, P11 girano attorno a P0 nel piano che contiene l'asse del
    ventaglio (z locale), cioe' cambiano solo l'angolo con l'asse; P0 e gli
    angoli restano fermi; i pari sono l'unico punto a distanza 1 da P0 e dai
    due vicini dalla stessa parte di prima. I 12 triangoli restano equilateri
    di lato 1."""
    n = extended_face.N_TRIANGLES
    P = np.asarray(md.vertices, dtype=float)
    Q = P.copy()
    apex = P[n]
    for k, ak in zip(FLEX_VERTICES, a):
        up = math.radians(FLEX_UP_DEG if ak > 0.0 else FLEX_DOWN_DEG) * ak
        v = P[k] - apex
        theta = math.acos(max(-1.0, min(1.0, v[2]))) - up       # l'angolo dall'asse
        azimuth = math.atan2(v[1], v[0])
        Q[k] = apex + np.array([math.sin(theta) * math.cos(azimuth),
                                math.sin(theta) * math.sin(azimuth), math.cos(theta)])
    for k in range(1, n, 2):
        Q[k], h2 = _equidistant(apex, Q[k - 1], Q[(k + 1) % n], P[k])
        assert h2 > FLEX_MIN_H2, f"flessione al limite: h2 = {h2:.3f} (a = {a})"
    out = MeshData()
    out.vertices = [tuple(float(c) for c in v) for v in Q]
    out.faces = md.faces
    return out


def plane_shape(t1):
    """I tre piani trasparenti: per ogni lato del ventaglio di M con questo
    t1, il pentagono P(4i+1)..P(4i+5) in un ventaglio di 5 triangoli dal
    baricentro (e' convesso: i cinque punti stanno su un arco di cerchio)."""
    P = np.asarray(fan_shape(t1, 0.0).vertices, dtype=float)
    n = extended_face.N_TRIANGLES
    out = MeshData()
    out.vertices, out.faces = [], []
    for side in range(extended_face.N_EDGES):
        idx = [(extended_face.SEG_PER_EDGE * side + i) % n
               for i in range(extended_face.SEG_PER_EDGE + 1)]
        pts = P[idx]
        base = len(out.vertices)
        out.vertices.append(tuple(float(c) for c in pts.mean(axis=0)))
        out.vertices += [tuple(float(c) for c in p) for p in pts]
        m = len(pts)
        out.faces += [[base, base + 1 + i, base + 1 + (i + 1) % m] for i in range(m)]
    return out


def plane_top():
    """La quota (z locale) piu' alta dei piani mentre i vetri scendono (P3,
    P7, P11): da li' parte la tendina."""
    t1 = params_at(plane_wipe_span()[0])[0]
    return max(v[2] for v in plane_shape(t1).vertices)


def _chain_at(chain, h):
    """Il punto della spezzata `chain` (dal basso verso l'alto, z crescente)
    che sta a quota h; fuori dall'intervallo, l'estremo piu' vicino."""
    if h <= chain[0][2]:
        return chain[0]
    for p, q in zip(chain, chain[1:]):
        if h <= q[2]:
            return p + (q - p) * ((h - p[2]) / (q[2] - p[2]))
    return chain[-1]


def chord_shape(t1, h=-1.0):
    """Il triangolo arancio, coi tappi; il lato i e' il cilindro i.

    Il lato i e' il bordo inferiore della parte del piano i che sta sopra la
    quota h: il segmento orizzontale (nel riferimento del ventaglio) fra il
    punto a quota h su P(4i+1)..P(4i+3) e quello su P(4i+5)..P(4i+3). Sopra
    P3 e' lungo zero; sotto zero e' il lato P(4i+1)-P(4i+5) intero."""
    P = np.asarray(fan_shape(t1, 0.0).vertices, dtype=float)
    k = extended_face.SEG_PER_EDGE
    n = extended_face.N_TRIANGLES
    out = MeshData()
    for side in range(extended_face.N_EDGES):
        pts = P[[(k * side + i) % n for i in range(k + 1)]]
        half = k // 2
        left, right = pts[:half + 1], pts[half:][::-1]
        assert all(np.diff(left[:, 2]) > 0) and all(np.diff(right[:, 2]) > 0), \
            "il piano non sale in modo monotono fino al vertice di mezzo"
        out.append(_tube(_chain_at(left, h), _chain_at(right, h), CHORD_RADIUS, caps=True))
    return out


def _sector(center, u, v, radius):
    """Il settore circolare di centro `center` fra le direzioni u e v
    (versori): un ventaglio di SECTOR_SEGMENTS triangoli."""
    angle = math.acos(max(-1.0, min(1.0, float(u @ v))))
    w = v - u * float(u @ v)
    w = w / max(float(np.linalg.norm(w)), 1e-12)
    md = MeshData()
    md.vertices = [tuple(center)] + [
        tuple(center + radius * (math.cos(a) * u + math.sin(a) * w))
        for a in (angle * j / SECTOR_SEGMENTS for j in range(SECTOR_SEGMENTS + 1))]
    md.faces = [[0, j + 1, j + 2] for j in range(SECTOR_SEGMENTS)]
    return md


def _apex_in_model(face, t1, z):
    """P0 della faccia, nel riferimento del modello (il pivot), e l'asse
    del ventaglio (la normale della faccia). La rotazione del ventaglio sul
    proprio asse non sposta P0."""
    apex = np.asarray(fan_shape(t1, 0.0).vertices[extended_face.N_TRIANGLES], dtype=float)
    R = np.asarray(SEATS[face][0].to_matrix())
    p = np.asarray(seat_location(face, t1)) + R @ (apex + np.array([0.0, 0.0, z]))
    return p, np.asarray(SEATS[face][1], dtype=float)


def axes_meeting(pa, na, pb, nb):
    """Il punto in cui si incontrano le rette pa + s na e pb + t nb (il
    punto medio del segmento di minima distanza, se fossero sghembe)."""
    w = pa - pb
    b = float(na @ nb)
    d, e = float(na @ w), float(nb @ w)
    den = 1.0 - b * b
    s = (b * e - d) / den
    t = (e - b * d) / den
    return 0.5 * ((pa + s * na) + (pb + t * nb))


def _cone(base, tip, radius):
    """Cono da `base` (cerchio di raggio `radius`) a `tip`, col fondo chiuso:
    la punta di una freccia."""
    base = np.asarray(base, dtype=float)
    tip = np.asarray(tip, dtype=float)
    axis = tip - base
    e1, e2 = _ring_basis(axis / np.linalg.norm(axis))
    ring = [base + radius * (math.cos(a) * e1 + math.sin(a) * e2)
            for a in (2.0 * math.pi * j / TUBE_SIDES for j in range(TUBE_SIDES))]
    md = MeshData()
    md.vertices = [tuple(v) for v in ring] + [tuple(tip), tuple(base)]
    t, b = TUBE_SIDES, TUBE_SIDES + 1
    md.faces = ([[j, (j + 1) % TUBE_SIDES, t] for j in range(TUBE_SIDES)]
                + [[b, (j + 1) % TUBE_SIDES, j] for j in range(TUBE_SIDES)])
    return md


def axes_tips(t1, za, zb):
    """Le punte delle due frecce, nel riferimento del modello."""
    return [p + AXIS_BEYOND * n for p, n in
            (_apex_in_model(FACE_A, t1, za), _apex_in_model(FACE_B, t1, zb))]


def axes_shape(t1, za, zb):
    """I due assi di simmetria di A e di B, nel riferimento del modello: da
    AXIS_BEYOND oltre P0 fino al punto in cui si incontrano, con una punta a
    cono all'estremo esterno, una sferetta sul punto d'incontro e il settore
    fra le due direzioni. Prima cilindri, coni e sferetta (materiale 0), poi
    il settore (materiale 1)."""
    pa, na = _apex_in_model(FACE_A, t1, za)
    pb, nb = _apex_in_model(FACE_B, t1, zb)
    c = axes_meeting(pa, na, pb, nb)
    out = MeshData()
    for p, n in ((pa, na), (pb, nb)):
        tip = p + AXIS_BEYOND * n
        base = tip - ARROW_LENGTH * n
        out.append(_tube(base, c, AXIS_RADIUS, caps=True))
        out.append(_cone(base, tip, ARROW_RADIUS))
    out.append(_sphere(c, 1.8 * AXIS_RADIUS))
    ua = (pa - c) / np.linalg.norm(pa - c)
    ub = (pb - c) / np.linalg.norm(pb - c)
    out.append(_sector(c, ua, ub, SECTOR_RADIUS))
    return out


def _flex_margin(a):
    """Il minimo h2 dei vertici pari (si veda _equidistant) per le ampiezze a."""
    if not any(a):
        return 1.0
    md = extended_face.make_extended_face(extended_face.PHI_CLOSING)
    Q = np.asarray(flexed(md, a).vertices, dtype=float)
    n = extended_face.N_TRIANGLES
    return min(_equidistant(Q[n], Q[k - 1], Q[(k + 1) % n], Q[k])[1] for k in range(1, n, 2))


def plane_residual():
    """Quanto i cinque punti di un lato si scostano dal loro piano, sul
    percorso di t1: la cosa che i piani affermano, misurata."""
    worst = 0.0
    for t1 in np.linspace(T1_MIN, T1_MAX, 7):
        P = np.asarray(fan_shape(float(t1), 0.0).vertices, dtype=float)
        for side in range(extended_face.N_EDGES):
            pts = P[[(4 * side + i) % 12 for i in range(5)]]
            worst = max(worst, float(np.linalg.svd(pts - pts.mean(axis=0))[1][-1]))
    return worst


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
    return SPOKE_RADIUS * smoothstep(g, 0.0, SPOKE_RAMP)


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


def wire_shape(t1, s, a, g1, g2, w=1.0):
    """Il bordo del ventaglio: 24 cilindri e 13 sferette in un solo MeshData,
    con numero di vertici e facce sempre uguale.

    g1 e g2 sono indipendenti da s: e' questo che permette di far arrivare gli
    spigoli a forma ferma e poi piegare la faccia a spigoli fermi. `w` scala
    tutti i raggi: 0 = spigoli invisibili, 1 = pieni (WIRE_TRACK)."""
    P = np.asarray(fan_shape(t1, s, a).vertices, dtype=float)
    apex = P[extended_face.N_TRIANGLES]
    n = extended_face.N_TRIANGLES

    out = MeshData()
    for k in range(n):                                  # la spezzata esterna
        out.append(_tube(P[k], P[(k + 1) % n], TUBE_RADIUS * w, caps=False))
    for k in range(n):                                  # i raggi, che crescono da P0
        g = g1 if k in SPOKE_GROUP_1 else g2
        out.append(_tube(apex, apex + g * (P[k] - apex), spoke_radius(g) * w, caps=True))
    for k in range(n):                                  # i vertici della spezzata
        out.append(_sphere(P[k], vertex_radius(k, g1, g2) * w))
    out.append(_sphere(apex, SPOKE_RADIUS * g1 * w))    # il mozzo, appare coi raggi
    return out


def wire_face_attributes():
    """(use_smooth, material_index) per ogni faccia del bordo, nell'ordine in cui
    `wire_shape` le costruisce.

    Lo smooth va su tutto tranne i tappi dei raggi: se un tappo e' smooth, la
    sua normale si media con quella del fianco sull'anello condiviso e l'orlo
    del cilindro si sfoca. Piatto, l'orlo resta netto e il fianco conserva la
    normale radiale.

    Il materiale (si veda WIRE_SLOTS) distingue i tre lati della spezzata --
    ogni lato e' fatto di 4 segmenti e si accende da solo -- dai raggi che
    passano per P0 (e dal mozzo). Le sferette dei punti interni di un lato
    stanno col lato; quelle dei tre angoli, che sono di due lati, hanno un
    materiale proprio che non si accende."""
    n = extended_face.N_TRIANGLES
    per_side = extended_face.SEG_PER_EDGE
    smooth, material = [], []

    for k in range(n):                                  # spezzata: senza tappi
        smooth += [True] * TUBE_SIDES
        material += [k // per_side] * TUBE_SIDES
    for _ in range(n):                                  # raggi: fianco + 2 tappi
        smooth += [True] * TUBE_SIDES + [False] * (2 * TUBE_SIDES)
        material += [SLOT_SPOKE] * (3 * TUBE_SIDES)
    faces_per_sphere = SPHERE_SEGMENTS * SPHERE_RINGS
    for k in range(n + 1):                              # sferette, mozzo per ultimo
        smooth += [True] * faces_per_sphere
        if k == n:
            slot = SLOT_SPOKE
        elif k % per_side == 0:
            slot = SLOT_CORNER
        else:
            slot = k // per_side
        material += [slot] * faces_per_sphere
    return smooth, material


# gli slot di materiale della mesh del bordo: 0, 1, 2 sono i tre lati
SLOT_SPOKE  = 3
SLOT_CORNER = 4


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
    prefixes = tuple(p + "_" for p in (FAN_PREFIX, SEAT_PREFIX, WIRE_PREFIX, CHORD_NAME))
    for obj in list(bpy.data.objects):
        if obj.name.startswith(prefixes) or obj.name in (PIVOT_NAME, PLANE_NAME,
                                                         TILT_NAME, AXES_NAME):
            bpy.data.objects.remove(obj, do_unlink=True)
    for name in (MESH_NAME, WIRE_MESH_NAME, PLANE_NAME, CHORD_NAME, AXES_NAME):
        if name in bpy.data.meshes:
            bpy.data.meshes.remove(bpy.data.meshes[name])
    KIT.clear_previous_run()            # camera, luce, fondo e materiali S6V4_


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
    # piu' di mezzo giro per segmento, e qui i giri sono interi. Un keyframe
    # per fotogramma, lineare: l'ease-in finale non e' una Bezier fra due chiavi.
    for frame in range(FRAME_START, FRAME_END + 1):
        obj.rotation_euler = (0.0, 0.0, pivot_angle(frame))
        obj.keyframe_insert("rotation_euler", index=2, frame=frame)
    # la comparsa: tutto il poliedro cresce da niente
    for frame, value in ((beat("comparsa")[0], 0.0), (beat("comparsa")[1], 1.0)):
        obj.scale = (value, value, value)
        obj.keyframe_insert("scale", frame=frame)
    obj.scale = (1.0, 1.0, 1.0)
    _set_interpolation(obj, 'BEZIER', "scale")
    _set_interpolation(obj, 'LINEAR', "rotation_euler")
    return obj


def create_tilt(collection, pivot, frames):
    """L'empty che inclina il modello (tilt_matrix), padre del pivot: un
    keyframe per fotogramma, lineare, su posizione e rotazione."""
    obj = bpy.data.objects.new(TILT_NAME, None)
    obj.empty_display_type = 'ARROWS'
    obj.empty_display_size = 0.5
    collection.objects.link(obj)
    obj.rotation_mode = 'QUATERNION'
    prev = None
    for frame in frames:
        loc, quat, _ = tilt_matrix(frame).decompose()
        if prev is not None and quat.dot(prev) < 0.0:   # stesso emisfero: niente salti
            quat.negate()
        prev = quat
        obj.location = loc
        obj.rotation_quaternion = quat
        obj.keyframe_insert("location", frame=frame)
        obj.keyframe_insert("rotation_quaternion", frame=frame)
    _set_interpolation(obj, 'LINEAR')
    pivot.parent = obj
    pivot.matrix_parent_inverse = mathutils.Matrix.Identity(4)
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

    Due canali animati, tutti e due ritoccabili a mano nel Graph Editor:
      * la Z locale, cioe' l'allontanamento dal posto (uguale per tutti);
      * la scala, che e' il modo in cui una faccia compare e sparisce (sua).
    """
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
        obj.visible_shadow = CAST_SHADOWS

        obj.location = (0.0, 0.0, 0.0)
        for frame, value in z_keys(face):
            obj.location = (0.0, 0.0, value)
            obj.keyframe_insert("location", index=2, frame=frame)

        # la rotazione sul proprio asse (z locale): l'asse passa per il
        # centro del triangolo di base e per P0, ed e' una simmetria del ventaglio
        for frame, value in spin_keys(face):
            obj.rotation_euler = (0.0, 0.0, value)
            obj.keyframe_insert("rotation_euler", index=2, frame=frame)
        obj.rotation_euler = (0.0, 0.0, 0.0)

        for frame, value in scale_keys(face):
            obj.scale = (value, value, value)
            obj.keyframe_insert("scale", frame=frame)

        obj.scale = (1.0, 1.0, 1.0)
        _set_interpolation(obj, 'BEZIER')
        fans.append(obj)
    return fans


def create_wires(collection, fans, mesh):
    """Un oggetto-bordo per ogni ventaglio, **figlio del ventaglio stesso**.

    Cosi' eredita tutto -- la posa dell'empty, l'allontanamento e anche la
    scalatura con cui la faccia compare e sparisce
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
        obj.visible_shadow = CAST_SHADOWS
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


KIT = m_scene.Kit(PREFIX, COLLECTION_NAME, ASSETS_DIR)
RIG = m_scene.CameraRig('PERSP', CAMERA_FAR, 36.0, RESOLUTION)


def camera_direction(frame=FRAME_START):
    """Il versore dal punto inquadrato verso la camera: CAMERA_DIRECTION,
    abbassato di CAMERA_LOWER_DEG * LOWER_TRACK(frame) a parita' di azimut.
    Per vedere il ventaglio da sotto non si muove la camera ma il modello
    (tilt_matrix)."""
    d = mathutils.Vector(CAMERA_DIRECTION).normalized()
    azimuth = math.atan2(d.y, d.x)
    elevation = math.asin(d.z) - math.radians(CAMERA_LOWER_DEG) * LOWER_TRACK(frame)
    return mathutils.Vector((math.cos(elevation) * math.cos(azimuth),
                             math.cos(elevation) * math.sin(azimuth),
                             math.sin(elevation)))


def tilt_frame():
    """(centro, asse, angolo pieno) dell'inclinazione del modello.

    Il centro e' P0 della faccia A quando l'inclinazione comincia (il
    punto che la camera tiene al centro, quindi resta fermo nell'immagine);
    l'asse e' perpendicolare all'asse del ventaglio A e alla direzione della
    camera; l'angolo porta l'asse del ventaglio da dov'e' a CAMERA_BELOW_DEG
    gradi dalla direzione della camera. Ruotare il modello di -angolo attorno
    a questo asse equivale a ruotare la camera di +angolo, come si faceva
    prima."""
    f = beat("verso_basso")[0]
    d = camera_direction(f)
    axis = mathutils.Vector(tuple(float(c) for c in SEATS[FACE_A][1]))
    hinge = axis.cross(d).normalized()
    start = math.acos(max(-1.0, min(1.0, axis.dot(d))))
    p, _ = _apex_in_model(FACE_A, T1_TRACK(f), Z_OUT)
    center = mathutils.Matrix.Rotation(pivot_angle(f), 3, 'Z') @ mathutils.Vector(tuple(p))
    return center, hinge, math.radians(CAMERA_BELOW_DEG) - start


_TILT = None


def tilt_matrix(frame):
    """La 4x4 che inclina il modello nel fotogramma: rotazione di
    -angolo * BELOW_TRACK attorno all'asse di tilt_frame, per il suo centro."""
    global _TILT
    if _TILT is None:
        _TILT = tilt_frame()
    center, hinge, full = _TILT
    R = mathutils.Matrix.Rotation(-full * BELOW_TRACK(frame), 4, hinge)
    return mathutils.Matrix.Translation(center) @ R @ mathutils.Matrix.Translation(-center)


def camera_rotation(frame=FRAME_START):
    """La rotazione della camera: guarda verso -camera_direction(frame), con
    l'alto dell'immagine verso +Z del mondo."""
    return camera_direction(frame).to_track_quat('Z', 'Y')


def light_direction():
    """LIGHT_IN_CAMERA in coordinate mondo, con la camera com'e' all'inizio.
    La luce resta ferma nel mondo mentre la camera si abbassa: e' il
    poliedro che si guarda da un'altra parte, non la luce che si sposta."""
    return camera_rotation().to_matrix() @ mathutils.Vector(LIGHT_IN_CAMERA)


def _fcurve_value(obj, data_path, index, frame, default):
    for fcurve in bl_anim.action_fcurves(obj):
        if fcurve.data_path == data_path and fcurve.array_index == index:
            return fcurve.evaluate(frame)
    return default


class FaceTracker:
    """Dove sta una faccia in un fotogramma, letto dalle stesse fcurve che
    usa Blender (rotazione del pivot, allontanamento del ventaglio) e dalla
    stessa forma (params_at): e' la faccia vera, non una
    stima. La scala si ignora apposta: per la camera conta dove la faccia
    *sara'* quando c'e', non che stia ancora comparendo."""

    def __init__(self, pivot, fans):
        self.pivot = pivot
        self.fans = fans
        self._shapes = {}

    def _shape(self, key):
        if key not in self._shapes:
            self._shapes[key] = [mathutils.Vector(v) for v in fan_shape(*key).vertices]
        return self._shapes[key]

    def points(self, face, frame):
        key = fan_params_at(frame)
        t1 = key[0]
        fan = self.fans[face]
        angle = _fcurve_value(self.pivot, "rotation_euler", 2, frame, 0.0)
        z = _fcurve_value(fan, "location", 2, frame, 0.0)
        spin = _fcurve_value(fan, "rotation_euler", 2, frame, 0.0)
        M = (tilt_matrix(frame)
             @ mathutils.Matrix.Rotation(angle, 4, 'Z')
             @ mathutils.Matrix.Translation(seat_location(face, t1))
             @ SEATS[face][0].to_matrix().to_4x4()
             @ mathutils.Matrix.Translation((0.0, 0.0, z))
             @ mathutils.Matrix.Rotation(spin, 4, 'Z'))
        return [M @ v for v in self._shape(key)]

    def model_matrix(self, frame):
        """Dal riferimento del modello (il pivot) al mondo."""
        angle = _fcurve_value(self.pivot, "rotation_euler", 2, frame, 0.0)
        return tilt_matrix(frame) @ mathutils.Matrix.Rotation(angle, 4, 'Z')

    def axes_key(self, frame):
        """(t1, zA, zB) da cui dipendono gli assi, arrotondati come params_at."""
        return (params_at(frame)[0],
                round(_fcurve_value(self.fans[FACE_A], "location", 2, frame, 0.0), PARAM_DECIMALS),
                round(_fcurve_value(self.fans[FACE_B], "location", 2, frame, 0.0), PARAM_DECIMALS))

    def axes_meeting(self, frame):
        """Il punto in cui si incontrano gli assi di A e B, nel mondo."""
        t1, za, zb = self.axes_key(frame)
        pa, na = _apex_in_model(FACE_A, t1, za)
        pb, nb = _apex_in_model(FACE_B, t1, zb)
        c = axes_meeting(pa, na, pb, nb)
        return self.model_matrix(frame) @ mathutils.Vector(tuple(float(x) for x in c))

    def axes_points(self, frame):
        """Il punto d'incontro e le due punte delle frecce, nel mondo: devono
        stare nell'inquadratura."""
        M = self.model_matrix(frame)
        tips = [M @ mathutils.Vector(tuple(float(x) for x in t))
                for t in axes_tips(*self.axes_key(frame))]
        return [self.axes_meeting(frame)] + tips


def framing_center(points, frame):
    """Il punto da tenere al centro dell'inquadratura: il centro del
    rettangolo che i punti occupano visti dalla camera (sugli assi destra e
    alto della camera), alla loro profondita' media. Si usa per la coppia A+B;
    per la faccia sola si usa P0 (si veda camera_keys)."""
    R = camera_rotation(frame).to_matrix()
    right, up, back = R.col[0], R.col[1], R.col[2]
    xs = [p.dot(right) for p in points]
    ys = [p.dot(up) for p in points]
    ds = [p.dot(back) for p in points]
    return (right * (min(xs) + max(xs)) / 2 + up * (min(ys) + max(ys)) / 2
            + back * (sum(ds) / len(ds)))


def camera_keys(tracker, frames):
    """(posizioni, rotazioni) della camera, un keyframe per fotogramma, gia'
    raccordato: il punto inquadrato (FOLLOW_TRACK, PAIR_TRACK) piu'
    DISTANCE_TRACK lungo camera_direction(frame).

    Della faccia A si tiene al centro P0, il vertice centrale: sta sull'asse
    del ventaglio, quindi non si muove quando la faccia gira, e si piega
    restando dov'e'. Il centro del rettangolo occupato dalla faccia invece
    cambia quando la faccia gira, e la camera che lo rincorreva oscillava."""
    apex = extended_face.N_TRIANGLES
    locations, rotations = [], []
    for f in frames:
        follow, pair = FOLLOW_TRACK(f), PAIR_TRACK(f)
        # il centro del poliedro, spostato dall'inclinazione
        target = tilt_matrix(f) @ mathutils.Vector((0.0, 0.0, 0.0))
        if follow > 0.0:
            a = tracker.points(FACE_A, f)
            focus = a[apex]
            if pair > 0.0:
                pts = a + tracker.points(FACE_B, f) + tracker.axes_points(f)
                focus = focus.lerp(framing_center(pts, f), pair)
            target = target.lerp(focus, follow)
        locations.append((f, tuple(target + camera_direction(f) * DISTANCE_TRACK(f))))
        rotations.append((f, tuple(camera_rotation(f))))
    return locations, rotations


def build_camera(tracker, frames):
    cam = RIG.build(KIT, mathutils.Vector((0.0, 0.0, 0.0)), clip_end=CAMERA_FAR + BACKGROUND_DEPTH + 10.0)
    cam.data.lens = CAMERA_LENS
    cam.rotation_mode = 'QUATERNION'
    locations, rotations = camera_keys(tracker, frames)
    bl_anim.key_value(cam, "location", locations, interpolation='LINEAR')
    bl_anim.key_value(cam, "rotation_quaternion", rotations, interpolation='LINEAR')
    m_scene.build_background(KIT, RIG, cam, CAMERA_LENS, BACKGROUND_DEPTH,
                             BACKGROUND_CORNERS_SRGB, BACKGROUND_BLEED)
    return cam


def wire_materials():
    """I materiali del bordo, nell'ordine degli slot: i tre lati (che si
    accendono con glow0, glow1, glow2), i raggi, gli angoli."""
    edge, spoke_color = m_scene.linear_rgba(EDGE_SRGB), m_scene.linear_rgba(SPOKE_SRGB)
    sides = [m_scene.wire_material(KIT, f"edge_side{i}", edge,
                                   glow_property=f"glow{i}", glow_color=GLOW_COLOR,
                                   glow_strength=GLOW_STRENGTH)
             for i in range(extended_face.N_EDGES)]
    spoke = m_scene.wire_material(KIT, "spoke", spoke_color)
    corner = m_scene.wire_material(KIT, "edge_corner", edge)
    for mat in sides + [spoke, corner]:
        _matte(mat)
    return sides + [spoke, corner]


def _matte(mat):
    """Toglie i riflessi: niente speculare, ruvidita' piena (WIRE_*)."""
    for node in mat.node_tree.nodes:
        if node.type == 'BSDF_PRINCIPLED':
            node.inputs["Specular IOR Level"].default_value = WIRE_SPECULAR
            node.inputs["Roughness"].default_value = WIRE_ROUGHNESS


def apply_glow(wires):
    for (face, side), keys in glow_keys().items():
        bl_anim.key_value(wires[face], f'["glow{side}"]', keys)


def check_framing(tracker, cam, frames):
    """Quanto la faccia A (e B, quando si vede) si avvicina al bordo
    dell'immagine mentre la camera la segue: il minimo margine, in frazione
    dell'inquadratura, sui fotogrammi in cui FOLLOW_TRACK e' 1. Negativo vuol
    dire che una faccia esce dall'inquadratura."""
    from bpy_extras.object_utils import world_to_camera_view as w2c
    scene = bpy.context.scene
    worst = (1.0, None)
    for f in frames[::4]:
        if FOLLOW_TRACK(f) < 1.0:
            continue
        pts = tracker.points(FACE_A, f)
        # B si conta da quando e' grande almeno a meta': prima e' un puntino,
        # e i suoi punti a grandezza piena (FaceTracker ignora la scala)
        # stanno dove B non e' ancora
        if _fcurve_value(tracker.fans[FACE_B], "scale", 0, f, 0.0) >= 0.5:
            pts = pts + tracker.points(FACE_B, f) + tracker.axes_points(f)
        scene.frame_set(f)
        for p in pts:
            q = w2c(scene, cam, p)
            m = min(q.x, 1.0 - q.x, q.y, 1.0 - q.y)
            if m < worst[0]:
                worst = (m, f)
    return worst


def check_final_framing(tracker, cam, frames):
    """Lo stesso controllo di check_framing, sulle 20 facce, da quando M si e'
    riformata alla fine: (margine minimo, fotogramma). Il punto critico e'
    quando le facce sono staccate."""
    from bpy_extras.object_utils import world_to_camera_view as w2c
    scene = bpy.context.scene
    worst = (1.0, None)
    for f in frames:
        if f < beat("entrano_tutte")[1] or (f - frames[0]) % 4:
            continue
        scene.frame_set(f)
        for face in range(len(SEATS)):
            for p in tracker.points(face, f):
                q = w2c(scene, cam, p)
                m = min(q.x, 1.0 - q.x, q.y, 1.0 - q.y)
                if m < worst[0]:
                    worst = (m, f)
    return worst


def lowest_point(tracker, frames):
    """(z minimo, fotogramma) delle facce che si vedono (scala sopra 0.01),
    dopo la comparsa: deve restare sopra il pavimento anche col modello
    inclinato."""
    worst = (math.inf, None)
    for f in frames[::4]:
        if f < beat("comparsa")[1]:
            continue
        for face in range(len(SEATS)):
            if _fcurve_value(tracker.fans[face], "scale", 0, f, 1.0) < 0.01:
                continue
            z = min(p.z for p in tracker.points(face, f))
            if z < worst[0]:
                worst = (z, f)
    return worst


def face_material():
    """Le facce: FACE_SRGB uniforme su un Principled."""
    mat, nodes, links = KIT.new_material("face")
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    color = m_scene.linear_rgba(FACE_SRGB)
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = FACE_ROUGHNESS
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.2
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    mat.diffuse_color = color
    return mat


def veil_material(suffix, color, strength):
    """Un velo: emissione e trasparenza mescolate dal nodo Fade (0 =
    invisibile). Emissivo e non illuminato, perche' un Principled
    semitrasparente, visto controluce, diventava una lastra grigia."""
    mat, nodes, links = KIT.new_material(suffix)
    out = nodes.new("ShaderNodeOutputMaterial")
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = color
    emit.inputs["Strength"].default_value = strength
    clear = nodes.new("ShaderNodeBsdfTransparent")
    fade = nodes.new("ShaderNodeMixShader")
    fade.name = "Fade"
    fade.inputs["Fac"].default_value = 0.0
    links.new(clear.outputs["BSDF"], fade.inputs[1])
    links.new(emit.outputs["Emission"], fade.inputs[2])
    links.new(fade.outputs["Shader"], out.inputs["Surface"])
    mat.diffuse_color = color
    return mat


ALPHA_PATH  = 'nodes["Alpha"].outputs[0].default_value'
REVEAL_PATH = 'nodes["Reveal"].outputs[0].default_value'


def plane_material(side, color):
    """Il velo di un piano, con la tendina: l'opacita' e' il valore del nodo
    Alpha per una maschera che vale 1 sopra la quota del nodo Reveal (z nel
    riferimento dell'oggetto, cioe' del ventaglio A) e 0 sotto, con un bordo
    sfumato largo PLANE_WIPE_BAND."""
    mat = veil_material(f"plane{side}", color, PLANE_GLOW)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    coords = nodes.new("ShaderNodeTexCoord")
    xyz = nodes.new("ShaderNodeSeparateXYZ")
    reveal = nodes.new("ShaderNodeValue")
    reveal.name = "Reveal"
    alpha = nodes.new("ShaderNodeValue")
    alpha.name = "Alpha"
    below = nodes.new("ShaderNodeMath")
    below.operation = 'SUBTRACT'
    mask = nodes.new("ShaderNodeMath")
    mask.operation = 'DIVIDE'
    mask.use_clamp = True
    mask.inputs[1].default_value = PLANE_WIPE_BAND
    fac = nodes.new("ShaderNodeMath")
    fac.operation = 'MULTIPLY'
    links.new(coords.outputs["Object"], xyz.inputs[0])
    links.new(xyz.outputs["Z"], below.inputs[0])
    links.new(reveal.outputs[0], below.inputs[1])
    links.new(below.outputs[0], mask.inputs[0])
    links.new(mask.outputs[0], fac.inputs[0])
    links.new(alpha.outputs[0], fac.inputs[1])
    links.new(fac.outputs[0], nodes["Fade"].inputs["Fac"])
    return mat


def chord_material(side):
    """Il lato arancio `side`, opaco e senza riflessi; si dissolve nel
    trasparente secondo la proprieta' fade<side> dell'oggetto, cosi' la
    stessa mesh puo' comparire in tempi diversi su A e su B."""
    color = m_scene.linear_rgba(CHORD_SRGB)
    mat = m_scene.fading_material(KIT, f"chord{side}", color)
    _matte(mat)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    attr = nodes.new("ShaderNodeAttribute")
    attr.attribute_type = 'OBJECT'
    attr.attribute_name = f"fade{side}"
    links.new(attr.outputs["Fac"], nodes["Fade"].inputs["Fac"])
    return mat


def build_planes(collection, fan, frames):
    """I tre piani trasparenti, figli della faccia A: ne seguono posa e
    allontanamento senza keyframe propri, e la forma (che dipende solo da t1)
    e' in shape key come quella del ventaglio. Ogni piano ha il suo materiale,
    con la tendina (Reveal) e l'opacita' (Alpha) keyframate."""
    color = m_scene.linear_rgba(PLANE_SRGB)
    materials = []
    for side in range(extended_face.N_EDGES):
        mat = plane_material(side, color)
        bl_anim.key_value(mat.node_tree, REVEAL_PATH, plane_reveal_keys(), interpolation='LINEAR')
        bl_anim.key_value(mat.node_tree, ALPHA_PATH, plane_alpha_keys())
        materials.append(mat)
    md = plane_shape(params_at(FRAME_START)[0])
    per_plane = extended_face.SEG_PER_EDGE + 1
    index = [i // per_plane for i in range(len(md.faces))]
    mesh = _make_mesh(PLANE_NAME, md, materials, material_index=index)
    obj = bpy.data.objects.new(PLANE_NAME, mesh)
    collection.objects.link(obj)
    obj.parent = fan
    obj.matrix_parent_inverse = mathutils.Matrix.Identity(4)
    obj.visible_shadow = False
    blocks = bake_shapes(obj, frames, lambda f: (params_at(f)[0],), plane_shape)
    return obj, blocks


def chord_key(frame):
    """(t1, quota) da cui dipende il triangolo arancio. Fuori dalla discesa
    dei vetri la quota e' fissa (sopra P3 prima, sotto zero dopo), cosi' le
    forme sono poche."""
    return (params_at(frame)[0], chord_height(frame))


def build_chords(collection, fans, frames):
    """Il triangolo arancio su A e su B: una mesh sola (forma in shape key,
    dipende solo da t1), due oggetti figli dei ventagli; ogni lato ha il suo
    materiale, che legge l'opacita' dalla proprieta' fade<lato> dell'oggetto."""
    sides = range(extended_face.N_EDGES)
    materials = [chord_material(side) for side in sides]
    md = chord_shape(*chord_key(FRAME_START))
    per_tube = 3 * TUBE_SIDES
    index = [i // per_tube for i in range(len(md.faces))]
    smooth = [(i % per_tube) < TUBE_SIDES for i in range(len(md.faces))]   # il fianco, non i tappi
    mesh = _make_mesh(CHORD_NAME, md, materials, smooth=smooth, material_index=index)
    objs = []
    for face, tag in ((FACE_A, "A"), (FACE_B, "B")):
        obj = bpy.data.objects.new(f"{CHORD_NAME}_{tag}", mesh)
        collection.objects.link(obj)
        obj.parent = fans[face]
        obj.matrix_parent_inverse = mathutils.Matrix.Identity(4)
        obj.visible_shadow = False
        for side in sides:
            bl_anim.key_value(obj, f'["fade{side}"]', chord_fade_keys(face, side))
        objs.append(obj)
    blocks = bake_shapes(objs[0], frames, chord_key, chord_shape)
    return objs, blocks


def build_axes(collection, pivot, tracker, frames):
    """I due assi di simmetria e il settore, figli del pivot (girano col
    modello). La forma dipende da t1 e dagli allontanamenti di A e B, letti
    dalle loro fcurve; fuori dal tratto in cui si vedono resta ferma."""
    color = m_scene.linear_rgba(AXIS_SRGB)
    line = veil_material("axis", color, AXIS_GLOW)
    sector = veil_material("sector", color, AXIS_GLOW)
    bl_anim.key_value(line.node_tree, m_scene.FADE_PATH, axes_fade_keys(1.0))
    bl_anim.key_value(sector.node_tree, m_scene.FADE_PATH, axes_fade_keys(SECTOR_ALPHA))
    first = beat("entra_B")[0]
    last = beat("entrano_tutte")[0] + FPS

    def key(f):
        return tracker.axes_key(min(max(f, first), last))

    md = axes_shape(*key(FRAME_START))
    n_sector = SECTOR_SEGMENTS
    index = [0] * (len(md.faces) - n_sector) + [1] * n_sector
    mesh = _make_mesh(AXES_NAME, md, [line, sector], material_index=index)
    obj = bpy.data.objects.new(AXES_NAME, mesh)
    collection.objects.link(obj)
    obj.parent = pivot
    obj.matrix_parent_inverse = mathutils.Matrix.Identity(4)
    obj.visible_shadow = False
    blocks = bake_shapes(obj, frames, key, axes_shape)
    return obj, blocks


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

    KIT.collection = collection
    scene.render.resolution_x, scene.render.resolution_y = RESOLUTION
    if USE_STANDARD_VIEW:
        scene.view_settings.view_transform = 'Standard'
        scene.view_settings.look = 'None'
    m_scene.use_cycles(scene)
    if WORLD == 'SKY':
        toward_sun = -light_direction()
        m_scene.setup_sky_world(KIT, math.radians(SKY_SUN_ELEVATION),
                                m_scene.sky_rotation(toward_sun), SKY_STRENGTH,
                                sun_size=math.radians(SUN_SIZE_DEG))
    elif WORLD == 'FLAT':
        m_scene.setup_world(KIT, m_scene.mean_srgb(BACKGROUND_CORNERS_SRGB.values()), AMBIENT)
        m_scene.build_light(KIT, light_direction(), LIGHT_STRENGTH)
    else:
        raise ValueError(f"WORLD dev'essere 'SKY' o 'FLAT', non {WORLD!r}")
    m_scene.setup_glare(KIT, scene, GLARE_THRESHOLD, GLARE_STRENGTH, GLARE_SIZE)

    mesh = _make_mesh(MESH_NAME, fan_shape(*fan_params_at(FRAME_START)), [face_material()])
    wire_smooth, wire_material = wire_face_attributes()
    wire_mesh = _make_mesh(WIRE_MESH_NAME, wire_shape(*params_at(FRAME_START)),
                           wire_materials(),
                           smooth=wire_smooth, material_index=wire_material)

    pivot = create_pivot(collection)
    tilt = create_tilt(collection, pivot, frames)
    seats, changing = create_seats(collection, pivot, frames)
    fans = create_fans(collection, seats, mesh)
    wires = create_wires(collection, fans, wire_mesh)
    blocks = bake_shapes(fans[0], frames, fan_params_at, fan_shape)
    wblocks = bake_shapes(wires[0], frames, params_at, wire_shape)
    apply_glow(wires)
    planes, pblocks = build_planes(collection, fans[FACE_A], frames)
    chords, cblocks = build_chords(collection, fans, frames)
    tracker = FaceTracker(pivot, fans)
    axes, ablocks = build_axes(collection, pivot, tracker, frames)
    floor = m_scene.build_floor(KIT, FLOOR_SRGB, FLOOR_ROUGHNESS, FLOOR_SPECULAR, FLOOR_SIZE)
    floor.location = (0.0, 0.0, -FLOOR_BELOW)

    cam = build_camera(tracker, frames)
    margin, margin_frame = check_framing(tracker, cam, frames)
    final_margin, final_frame = check_final_framing(tracker, cam, frames)
    low, low_frame = lowest_point(tracker, frames)
    _, hinge, full = _TILT
    meet0, meet1 = (tracker.axes_meeting(f) for f in (beat("entra_B")[1], beat("t1_giusto")[1]))

    scene.frame_set(FRAME_START)

    print(f"[scene-6 v4] {len(fans)} ventagli su una sola mesh di {len(mesh.vertices)} "
          f"vertici, {len(seats)} empty; frame {FRAME_START}-{FRAME_END} a {FPS} fps "
          f"({(FRAME_END - FRAME_START + 1) / FPS:.1f} s)")
    print(f"[scene-6 v4] bordo: {len(wires)} oggetti su una mesh di "
          f"{len(wire_mesh.vertices)} vertici (spezzata senza tappi, raggi coi "
          f"tappi, {extended_face.N_TRIANGLES + 1} sferette), raggio {TUBE_RADIUS}")
    print(f"[scene-6 v4] shape key: {len(blocks)} forme del ventaglio e "
          f"{len(wblocks)} del bordo, su {len(frames)} fotogrammi; keyframe di "
          f"posizione degli empty su {len(changing)} fotogrammi; {len(pblocks)} forme dei piani")
    print(f"[scene-6 v4] t1: {T1_M:.6f} (M) -> {T1_MIN} -> {T1_MAX} -> {T1_OVERSHOOT} -> {T1_M:.6f}; "
          f"pivot: {pivot_angle(FRAME_END) / (2.0 * math.pi):.2f} giri; "
          f"ventaglio A: {FAN_SPIN_TURNS} giri sul suo asse")
    print("[scene-6 v4] le altre 18 cominciano a comparire a (s): "
          + ", ".join(f"{(enter_start(i) - FRAME_START) / FPS:.2f}"
                      for i in sorted(set(range(len(SEATS))) - {FACE_A, FACE_B},
                                      key=enter_start)))
    print(f"[scene-6 v4] con s=0, t1=T1_M, z=0 le 20 facce ricostruiscono M: "
          f"scarto {_check_reproduces_M():.2e}")
    print(f"[scene-6 v4] t1 per il contatto: {T1_MAX} (fessura) -> {T1_OVERSHOOT} "
          f"(sovrapposizione) -> {T1_M:.6f}; lati in comune (indice nella mesh): "
          f"A {shared_side(FACE_A, FACE_B)}, B {shared_side(FACE_B, FACE_A)}")
    print(f"[scene-6 v4] camera: distanza {CAMERA_ICO} / {CAMERA_NEAR} / {CAMERA_PAIR} / {CAMERA_FAR}, "
          f"focale {CAMERA_LENS}; mentre segue la faccia, margine minimo dal bordo "
          f"dell'immagine {margin:.1%} (fotogramma {margin_frame}); su M intera, alla fine, {final_margin:.1%} "
          f"(fotogramma {final_frame})")
    worst_h2 = min(_flex_margin(flex_at(f)) for f in range(*beat("flessione")))
    print(f"[scene-6 v4] flessione: P3, P7, P11 su di {FLEX_UP_DEG} e giu' di {FLEX_DOWN_DEG} gradi, "
          f"sfalsati di {FLEX_STAGGER} s; margine minimo dei vertici pari h2 = {worst_h2:.3f}; "
          f"piani: scarto dalla complanarita' {plane_residual():.1e}")
    right = camera_rotation(beat("verso_basso")[0]).to_matrix().col[0]
    print(f"[scene-6 v4] inclinazione del modello: {math.degrees(full):.1f} gradi attorno a "
          f"{tuple(round(c, 3) for c in hinge)} ({math.degrees(hinge.angle(right)):.1f} gradi "
          f"dall'orizzontale dell'immagine); punto piu' basso delle facce visibili "
          f"z = {low:.2f} (fotogramma {low_frame}), pavimento a {-FLOOR_BELOW}")
    print(f"[scene-6 v4] assi: si incontrano in {tuple(round(c, 3) for c in meet0)} quando B e' "
          f"entrata e in {tuple(round(c, 3) for c in meet1)} a contatto fatto; "
          f"{len(ablocks)} forme degli assi, {len(cblocks)} del triangolo arancio")
    print("[scene-6 v4] nessun handler registrato: a render time non gira Python")
    return pivot, fans, seats, wires, blocks, wblocks


PIVOT, FANS, SEATS_OBJ, WIRES, BLOCKS, WBLOCKS = build()
