"""
v2/scene-7.py -- M al centro di una platea di deltaedri di Saffaro, il volo
della camera fra i poliedri, e il ritorno al quadro.

--------------------------------------------------------------------------
LA SCALETTA (secondi, a 24 fps)
--------------------------------------------------------------------------
   0 - 1      M compare al centro, sul pavimento ardesia (scala da 0 a 1), e
              comincia a girare lentamente su se stesso
   1.5 - 7    attorno compaiono gli altri tredici deltaedri di Saffaro, su
              una spirale, quasi a contatto: i piu' grandi vicino a M, i piu'
              piccoli fuori, nell'ordine della spirale
   7 - 10.5   la camera scende lungo la striscia libera davanti a M, verso il
              poliedro piu' vicino al punto in cui entra nel giro (a destra di
              M), fino a sfiorarlo...
  10.5 - 16   ... e fa un giro completo attorno a M, bassa sul pavimento, in
              prima persona, all'altezza del centro di M e stretta attorno a
              lui: M le sfila enorme a sinistra e gli altri poliedri a destra.
              Entra ed esce dal giro piu' piano, a meta' va piu' forte, e
              nelle curve si inclina (BANK_MAX)
  16 - 18     torna indietro e si gira verso M, fino alla camera del quadro
  18 - 20.4   i poliedri spariscono uno dopo l'altro (scala da 1 a 0), da
              fuori verso dentro; intanto il pavimento svanisce (18 - 21)
  20          M ha finito il suo giro: e' nella posa del quadro, fermo
  21 - 22     M passa dal pastello azzurro ai colori del quadro (il materiale
              di scene-1, all'indietro)
  22 - 23     compare il quadro
  24          fine

--------------------------------------------------------------------------
LE SCELTE
--------------------------------------------------------------------------
* La fine si raccorda col quadro come l'inizio di scene-1: la camera,
  il fondo sfumato, la posa di M, il suo materiale e il quadro vengono da
  libs/story.py. Il mondo e' quello del racconto (M al centro, in origine);
  il pavimento sta sotto M, a CLEARANCE dalla sfera che lo contiene.
* Tutti i triangoli sono uguali: gli altri poliedri (STL di spigolo 1) sono
  scalati allo spigolo di M. Sono tredici: tutti i modelli di
  modelli-3d/saffaro-deltahedra tranne M stesso.
* La spirale: in pianta, i pezzi si posano dal piu' grande al piu' piccolo,
  ognuno a contatto col precedente e con un altro gia' posato (fra le sfere
  resta SPIRAL_GAP), sempre piu' avanti in verso antiorario, nella posizione
  piu' vicina al centro: il primo giro abbraccia M, il secondo si appoggia
  sul primo. Il primo pezzo sta dietro a M (SPIRAL_START). Due zone restano
  libere. Attorno a M, il corridoio dove gira la camera: M le sfila a
  sinistra e la spirale a destra. E una striscia davanti a M, verso la camera
  del quadro, larga quanto M: alla fine la camera vede M senza niente
  davanti. Quando la spirale arriva alla striscia, il pezzo dopo va oltre:
  il primo posto libero piu' avanti.
* La camera: ferma fino a 7 s, alta CAMERA_ELEVATION gradi, inquadra tutti
  i poliedri. Il volo e' calcolato fotogramma per fotogramma e non ha
  strappi: discesa, giro e ritorno sono raccordati nella posizione, nella
  velocita' e nell'accelerazione (polinomi di quinto grado; il giro rallenta
  verso i suoi estremi, CIRCLE_END_SPEED), e cosi' anche la direzione in cui
  guarda. Scende guardando prima il centro, poi il poliedro che sfiora, poi
  davanti a se' (il punto della strada LOOK_AHEAD secondi piu' avanti: nel
  giro e' un po' verso M); al ritorno si ferma guardando M, e arriva
  esattamente sulla camera del quadro. Durante il volo l'obiettivo si allarga
  a FLY_LENS, e la camera si inclina nelle curve come chi vola: dalla parte
  verso cui gira, tanto piu' quanto piu' forte e' l'accelerazione laterale
  (fino a BANK_MAX). Lo script controlla che la camera non entri mai nella sfera di
  un poliedro, e misura gli strappi (la derivata terza della posizione e la
  seconda della rotazione).
* Il fondo sfumato del racconto, figlio della camera, sta lontano
  (BACKGROUND_DEPTH): da bassa la camera vede l'orizzonte, e il fondo vicino
  taglierebbe il pavimento.
* Colori pastello, stessa luminosita' e saturazione in OKLCH (story.pastel),
  tinte lontane dall'azzurro di M. Ombre morbide sul pavimento, come in
  cundy_deltahedra.
* Il motore e' Cycles, a 256 campioni (m_scene.use_cycles).

Una sola scena, tutto in keyframe (nessun handler), script idempotente, nomi
col prefisso S7V2_.
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
        txt = bpy.data.texts.get("scene-7.py")
    if txt is None or not txt.filepath:
        raise RuntimeError(
            "non riesco a ricavare il path dello script: il testo non e' salvato "
            "su disco (Text > Save As) oppure e' un blocco 'interno'"
        )
    # attenzione: se il file e' stato aperto con l'opzione 'Relative Path' spuntata,
    # filepath e' del tipo '//../...' (relativo al .blend) e os.path lo interpreta
    # come percorso UNC. bpy.path.abspath lo risolve; sugli assoluti non fa nulla.
    path = os.path.abspath(bpy.path.abspath(txt.filepath))
    # script in src/scripts/v2, librerie in src/libs
    libs = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(path))), "libs")
    if not os.path.isdir(libs):
        raise RuntimeError(f"cartella libs non trovata: {libs}  (filepath: {txt.filepath})")
    return libs


_LIBS = _find_libs_dir()
if _LIBS not in sys.path:
    sys.path.insert(0, _LIBS)

# questo serve nel caso che tu faccia modifiche ai moduli senza interrompere la sessione di Blender
import geometry, bl_utils, extended_face, bl_anim, m_scene, story, deltahedra
for _mod in (geometry, bl_utils, extended_face, bl_anim, m_scene, story, deltahedra):
    importlib.reload(_mod)

from mathutils import Vector, Quaternion


# =============================================================================
# CONFIGURAZIONE
# =============================================================================

PREFIX          = "S7V2"
COLLECTION_NAME = "scene-7_v2"

# saffaro/..., accanto al repository: src/libs -> src -> saffaro-delthedra -> saffaro
_SAFFARO    = os.path.dirname(os.path.dirname(os.path.dirname(_LIBS)))
ASSETS_DIR  = os.path.join(_SAFFARO, "assets")
SAFFARO_DIR = os.path.join(_SAFFARO, "modelli-3d", "saffaro-deltahedra")
M_FILE      = "M.stl"            # M c'e' gia' (extended_face): gli altri sono tutti gli altri

FPS         = story.FPS
RESOLUTION  = story.RESOLUTION
FRAME_START = 1

# --- la scaletta, in secondi ---
M_IN          = (0.0, 1.0)       # M compare
M_TURN        = (0.0, 20.0)      # M fa un giro su se stesso, partendo e fermandosi piano
OTHERS_AT     = 1.5              # gli altri cominciano a comparire...
OTHERS_ALL_IN = 7.0              # ... e a quest'ora ci sono tutti
OTHERS_GROW   = 0.8
APPROACH      = (7.0, 10.5)      # la camera scende verso il primo poliedro
CIRCLE        = (10.5, 16.0)     # il giro attorno a M
EXIT          = (16.0, 18.0)     # torna alla camera del quadro
VANISH_AT     = 18.0             # i poliedri spariscono, uno dopo l'altro...
VANISH_GAP    = 0.15
VANISH_SECONDS = 0.6
FLOOR_FADE    = (18.0, 21.0)     # ... e il pavimento svanisce
LOOK_CHANGE   = (21.0, 22.0)     # M: dal pastello ai colori del quadro
PAINT_IN      = (22.0, 23.0)     # il quadro
END           = 24.0
OTHER_SECONDS_PER_TURN = 12.0    # gli altri, su se stessi

# --- la spirale ---
N_PIECES        = 13             # tutti i modelli tranne M
SPIRAL_START    = 90.0           # gradi: il primo pezzo (il piu' grande) sta dietro a M
SPIRAL_GAP      = 0.15           # fra due sfere vicine, in pianta: quasi a contatto
CORRIDOR_CLEAR  = 0.5            # fra il corridoio della camera e le sfere (M compreso), in pianta
STRIP_CLEAR     = 0.3            # la striscia libera davanti a M e' larga M piu' questo, per parte
CLEARANCE       = 0.3            # fra il pavimento e la sfera che contiene un pezzo

# --- la camera ---
CAMERA_ELEVATION = 30.0          # all'inizio, gradi sopra l'orizzonte
START_FILL  = (0.92, 0.88)       # quanta immagine occupa la platea all'inizio
FLY_LENS    = 20.0               # mm, durante il volo
CIRCLE_END_SPEED = 0.3           # velocita' all'ingresso e all'uscita del giro, rispetto alla media
LOOK_AHEAD  = 0.6                # secondi: in volo la camera guarda dove sara' fra tanto
FLY_HEIGHT  = 0.0                # durante il giro, rispetto al centro di M
BANK_MAX    = 15.0               # gradi: l'inclinazione massima nelle curve
BANK_ACCEL  = 8.0                # l'accelerazione laterale che da' tre quarti di BANK_MAX
BANK_OUT    = 0.8                # secondi: al ritorno l'inclinazione si spegne in tanto
MIN_DISTANCE = 0.3               # la camera non passa mai piu' vicina di cosi' a una sfera
BACKGROUND_DEPTH = 300.0         # il fondo sfumato, dietro l'orizzonte

# --- pavimento e luce: come cundy_deltahedra ---
FLOOR_SRGB      = (30, 38, 56)
FLOOR_ROUGHNESS = 0.85
FLOOR_SPECULAR  = 0.05
FLOOR_SIZE      = 800.0
SUN_SIZE_DEG    = 8.0
SKY_SUN_ELEVATION = 30.0

# --- i colori ---
HUE_START = 20.0
HUE_STEP  = 137.508              # l'angolo aureo
HUE_AVOID = 35.0                 # gradi di distanza minima dalla tinta di M
ROUGHNESS = 0.5


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


def smooth(u):
    return u * u * (3.0 - 2.0 * u)


def smoothstep(x, x0, x1):
    return smooth(ramp(x, x0, x1))


def hue_of(k):
    """La tinta del k-esimo poliedro: l'angolo aureo, saltando quelle vicine
    alla tinta di M."""
    h = (HUE_START + k * HUE_STEP) % 360.0
    d = (h - story.M_HUE + 180.0) % 360.0 - 180.0
    if abs(d) < HUE_AVOID:
        h = (story.M_HUE + math.copysign(HUE_AVOID, d if d else 1.0)) % 360.0
    return h


# =============================================================================
# LA PLATEA
# =============================================================================

KIT = m_scene.Kit(PREFIX, COLLECTION_NAME, ASSETS_DIR)


class Piece:
    def __init__(self, name, V, faces):
        self.name, self.V, self.faces = name, V, faces
        self.radius = float(np.linalg.norm(V, axis=1).max())
        self.location = None


def load_pieces(edge):
    """Gli altri poliedri, allo spigolo `edge` (quello di M), dal piu' grande
    al piu' piccolo (a pari grandezza, per nome)."""
    out = []
    for fname in sorted(os.listdir(SAFFARO_DIR)):
        if not fname.lower().endswith(".stl") or fname == M_FILE:
            continue
        V, faces = deltahedra.load_stl(os.path.join(SAFFARO_DIR, fname))
        out.append(Piece(os.path.splitext(fname)[0], V * edge, faces))
    if len(out) != N_PIECES:
        raise ValueError(f"{len(out)} poliedri in {SAFFARO_DIR}, non {N_PIECES}")
    return sorted(out, key=lambda p: (-round(p.radius, 3), p.name))


def corridor_radius(m_radius):
    """Il raggio del giro della camera: stretto attorno a M, che le sfila a
    sinistra, mentre la spirale le sfila a destra."""
    return m_radius + CORRIDOR_CLEAR


def tangent_points(a, ra, b, rb):
    """I punti a distanza ra da a e rb da b (in pianta): dove sta il centro di
    un disco che tocca due dischi."""
    d = float(np.linalg.norm(b - a))
    if d == 0.0 or d > ra + rb or d < abs(ra - rb):
        return []
    x = (ra * ra - rb * rb + d * d) / (2.0 * d)
    h = math.sqrt(max(0.0, ra * ra - x * x))
    u = (b - a) / d
    n = np.array([-u[1], u[0]])
    c = a + u * x
    return [c + n * h, c - n * h]


def arrange(pieces, m_radius, floor_z, corridor):
    """Posa i pezzi sulla spirale (si veda LE SCELTE), nell'ordine dato: tutto
    in pianta, dischi del raggio delle sfere. Il nucleo -- M e il corridoio
    della camera -- e' un disco come gli altri, a cui il primo giro si
    appoggia. Restituisce i pezzi che, arrivati alla striscia, sono andati
    oltre."""
    strip = m_radius + STRIP_CLEAR
    core = (np.zeros(2), corridor + CORRIDOR_CLEAR - SPIRAL_GAP)
    placed, jumped = [], []

    def free(q, R):
        return (np.linalg.norm(q) >= core[1] + SPIRAL_GAP + R - 1e-9
                and not (q[1] - R < 0.0 and abs(q[0]) - R < strip)
                and all(np.linalg.norm(q - c) >= R + r + SPIRAL_GAP - 1e-9 for c, r in placed))

    def advance(q, last):
        return (math.atan2(q[1], q[0]) - last) % (2.0 * math.pi)

    last = math.radians(SPIRAL_START)
    for p in pieces:
        R = p.radius
        if not placed:
            q = np.array([math.cos(last), math.sin(last)]) * (core[1] + SPIRAL_GAP + R)
        else:
            discs = [core] + placed
            prev = placed[-1]
            near = [q for c, r in discs[:-1]
                    for q in tangent_points(prev[0], prev[1] + R + SPIRAL_GAP, c, r + R + SPIRAL_GAP)]
            near = [q for q in near if free(q, R) and 0.0 < advance(q, last) < math.pi]
            if near:
                q = min(near, key=np.linalg.norm)
            else:
                # la striscia: si salta, al primo posto libero piu' avanti
                far = [q for i, (a, ra) in enumerate(discs) for b, rb in discs[i + 1:]
                       for q in tangent_points(a, ra + R + SPIRAL_GAP, b, rb + R + SPIRAL_GAP)]
                far = [q for q in far if free(q, R)]
                if not far:
                    raise ValueError(f"non trovo posto per {p.name}")
                q = min(far, key=lambda q: advance(q, last) + 0.15 * np.linalg.norm(q))
                jumped.append(p.name)
        p.location = np.array([q[0], q[1], floor_z + R + CLEARANCE])
        placed.append((q, R))
        last = math.atan2(q[1], q[0])
    return jumped


# =============================================================================
# IL VOLO DELLA CAMERA
# =============================================================================

def smoother(u):
    """Raccordo da 0 a 1 con derivate prima e seconda nulle agli estremi."""
    return u * u * u * (u * (6.0 * u - 15.0) + 10.0)


def smootherstep(x, x0, x1):
    return smoother(ramp(x, x0, x1))


class Quintic:
    """Il polinomio di quinto grado da (p0, v0, a0) a (p1, v1, a1) in T
    secondi: posizione, velocita' e accelerazione date ai due estremi, cosi'
    che due tratti consecutivi si raccordano senza strappi. Vale per scalari e
    per vettori numpy."""

    def __init__(self, p0, v0, a0, p1, v1, a1, T):
        d = p1 - p0
        v0, v1, a0, a1 = v0 * T, v1 * T, a0 * T * T, a1 * T * T
        self.c = [p0, v0, a0 / 2.0,
                  10 * d - 6 * v0 - 4 * v1 - 1.5 * a0 + 0.5 * a1,
                  -15 * d + 8 * v0 + 7 * v1 + 1.5 * a0 - a1,
                  6 * d - 3 * v0 - 3 * v1 - 0.5 * a0 + 0.5 * a1]
        self.T = T

    def value(self, u):
        return sum(c * u ** k for k, c in enumerate(self.c))

    def speed(self, u):
        """La derivata rispetto al tempo."""
        return sum(k * c * u ** (k - 1) for k, c in enumerate(self.c) if k) / self.T

    def accel(self, u):
        return sum(k * (k - 1) * c * u ** (k - 2) for k, c in enumerate(self.c) if k > 1) / self.T ** 2


def look_quat(direction):
    """La rotazione della camera che guarda lungo `direction`, con
    l'orizzonte dritto."""
    return Vector(direction).normalized().to_track_quat('-Z', 'Y')


def unit(v):
    return v / np.linalg.norm(v)


class Flight:
    """La posa della camera (posizione, rotazione, focale) a ogni istante.

    Il giro parte dal punto del corridoio a destra di M (a 0 gradi, dove il
    giro antiorario va verso +y, cioe' verso dove guarda la camera fin
    dall'inizio), e ci torna dopo un giro intero. Cosi' la discesa arriva gia'
    nella direzione del giro e la camera non deve girarsi da una parte e poi
    dall'altra; la striscia libera davanti a M e' larga abbastanza da farla
    passare. L'angolo segue un polinomio di quinto grado nel tempo: velocita'
    CIRCLE_END_SPEED volte la media agli estremi, accelerazione nulla, quindi
    li' l'accelerazione e' solo quella centripeta, e discesa e ritorno la
    raccolgono."""

    def __init__(self, start, start_target, start_lens, end, end_lens, corridor, height, grazed):
        self.start, self.start_target, self.start_lens = start, start_target, start_lens
        self.end, self.end_lens = end, end_lens
        self.r, self.h, self.grazed = corridor, height, grazed
        self.theta0 = 0.0
        T = CIRCLE[1] - CIRCLE[0]
        self.turn = Quintic(0.0, CIRCLE_END_SPEED / T, 0.0, 1.0, CIRCLE_END_SPEED / T, 0.0, T)
        p, v, a = self.circle(CIRCLE[0])
        self.approach = Quintic(start, np.zeros(3), np.zeros(3), p, v, a, APPROACH[1] - APPROACH[0])
        p, v, a = self.circle(CIRCLE[1])
        self.back = Quintic(p, v, a, end, np.zeros(3), np.zeros(3), EXIT[1] - EXIT[0])
        # al ritorno l'imbardata parte da dove guardava (la tangente, cioe'
        # l'angolo del giro piu' 90 gradi), con la velocita' del giro, e si
        # ferma guardando lungo +y: e' la stessa direzione, quindi oscilla
        # appena (il giro finisce piano)
        yaw0 = self.theta0 + 2.0 * math.pi + math.pi / 2.0
        rate0 = 2.0 * math.pi * self.turn.speed(1.0)
        yaw1 = math.pi / 2.0 + 2.0 * math.pi * round((yaw0 - math.pi / 2.0) / (2.0 * math.pi))
        self.yaw = Quintic(yaw0, rate0, 0.0, yaw1, 0.0, 0.0, EXIT[1] - EXIT[0])
        self.mean_speed = 2.0 * math.pi * corridor / T

    def circle(self, t):
        """Posizione, velocita', accelerazione sul giro."""
        u = ramp(t, *CIRCLE)
        th = self.theta0 + 2.0 * math.pi * self.turn.value(u)
        w = 2.0 * math.pi * self.turn.speed(u)
        dw = 2.0 * math.pi * self.turn.accel(u)
        radial = np.array([math.cos(th), math.sin(th), 0.0])
        tangent = np.array([-math.sin(th), math.cos(th), 0.0])
        return (np.array([self.r * radial[0], self.r * radial[1], self.h]),
                self.r * w * tangent, self.r * dw * tangent - self.r * w * w * radial)

    def track(self, t):
        """La strada per guardare avanti: la discesa e il giro, e dopo il giro
        il giro stesso, prolungato alla velocita' con cui finisce. Non il
        ritorno: il ritorno torna indietro, e chi guardasse li' si
        volterebbe di colpo."""
        if t <= APPROACH[1]:
            return self.approach.value(ramp(t, *APPROACH))
        if t <= CIRCLE[1]:
            return self.circle(t)[0]
        th = self.theta0 + 2.0 * math.pi * (1.0 + self.turn.speed(1.0) * (t - CIRCLE[1]))
        return np.array([self.r * math.cos(th), self.r * math.sin(th), self.h])

    def ahead(self, t):
        """Dove guarda chi vola: il punto della strada LOOK_AHEAD secondi piu'
        avanti. Segue la strada senza inseguire ogni piega della velocita'
        (la discesa frena forte in fondo, e la direzione del moto li' gira
        in fretta), e nel giro guarda un po' verso M."""
        return unit(self.track(t + LOOK_AHEAD) - self.track(t))

    def accel(self, t):
        """L'accelerazione da cui viene l'inclinazione: quella della discesa e
        del giro, e dopo il giro quella del giro prolungato (la sola
        centripeta), come per guardare avanti: la frenata del ritorno non
        deve far ondeggiare la camera."""
        if t <= APPROACH[1]:
            return self.approach.accel(ramp(t, *APPROACH))
        if t <= CIRCLE[1]:
            return self.circle(t)[2]
        th = self.theta0 + 2.0 * math.pi * (1.0 + self.turn.speed(1.0) * (t - CIRCLE[1]))
        w = 2.0 * math.pi * self.turn.speed(1.0)
        return -self.r * w * w * np.array([math.cos(th), math.sin(th), 0.0])

    def banked(self, t, d):
        """La rotazione che guarda lungo d, inclinata verso dove la camera gira:
        l'accelerazione laterale (in orizzontale, verso sinistra) da' l'angolo,
        che si satura dolcemente a BANK_MAX. L'inclinazione entra nel primo
        secondo della discesa ed esce nel primo BANK_OUT del ritorno, con
        raccordi senza strappi."""
        q = look_quat(d)
        h = np.array([d[0], d[1], 0.0])
        if np.linalg.norm(h) < 1e-6:
            return q
        left = unit(np.cross([0.0, 0.0, 1.0], h))
        window = (smootherstep(t, APPROACH[0], APPROACH[0] + 1.0)
                  * (1.0 - smootherstep(t, CIRCLE[1], CIRCLE[1] + BANK_OUT)))
        roll = window * math.radians(BANK_MAX) * math.tanh(float(np.dot(self.accel(t), left)) / BANK_ACCEL)
        return q @ Quaternion((0.0, 0.0, 1.0), roll)

    def at(self, t):
        if t <= APPROACH[0]:
            return self.start, look_quat(self.start_target - self.start), self.start_lens
        if t <= APPROACH[1]:
            u = ramp(t, *APPROACH)
            p = self.approach.value(u)
            # guarda prima il centro, poi il poliedro che sfiora, poi davanti a se'
            target = self.start_target + (self.grazed - self.start_target) * smoother(min(1.0, 2.0 * u))
            d = unit(target - p)
            d = d + (self.ahead(t) - d) * smootherstep(u, 0.3, 1.0)
            lens = self.start_lens + (FLY_LENS - self.start_lens) * smoother(u)
            return p, self.banked(t, d), lens
        if t <= CIRCLE[1]:
            return self.circle(t)[0], self.banked(t, self.ahead(t)), FLY_LENS
        if t <= EXIT[1]:
            u = ramp(t, *EXIT)
            p = self.back.value(u)
            # da davanti a se' (lungo il giro prolungato) all'imbardata che si
            # ferma guardando M
            y = self.yaw.value(u)
            d = np.array([math.cos(y), math.sin(y), 0.0])
            if u < 0.5:
                a = self.ahead(t)
                d = a + (d - a) * smootherstep(u, 0.0, 0.5)
            lens = FLY_LENS + (self.end_lens - FLY_LENS) * smoother(u)
            return p, self.banked(t, d), lens
        return self.end, look_quat((0.0, 1.0, 0.0)), self.end_lens


def roughness(poses):
    """Gli strappi del volo: il massimo della derivata terza della posizione
    (unita' al secondo cubo) e della derivata seconda dell'angolo di
    rotazione (gradi al secondo quadrato), stimate sui fotogrammi."""
    P = np.array([np.asarray(p) for p, _, _ in poses])
    jerk = np.linalg.norm(np.diff(P, n=3, axis=0), axis=1).max() * FPS ** 3
    Q = [q for _, q, _ in poses]
    # l'angolo fra due rotazioni: q e -q sono la stessa, quindi il valore assoluto
    rate = np.array([math.degrees(2.0 * math.acos(min(1.0, abs(a.dot(b))))) for a, b in zip(Q, Q[1:])]) * FPS
    spin_acc = np.abs(np.diff(rate)).max() * FPS
    return jerk, spin_acc, rate.max()


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
    scene.cycles.transparent_max_bounces = 32       # il pavimento che svanisce
    KIT.new_collection(scene)
    frames = range(FRAME_START, FRAME_END + 1)

    # --- M, come in scene-1: perno (il giro) -> orient (la posa del quadro) -> M ---
    md = extended_face.make_M()
    painting_img = KIT.load_image(story.PAINTING_FILE)
    layout = story.Layout(md, painting_img.size)
    face_img = KIT.load_image(m_scene.FACE_TEXTURE_FILE)
    uvs = m_scene.face_uvs(face_img, m_scene.FACE_TEXTURE_UV_PX, m_scene.FACE_TEXTURE_UV_INSET)
    m_mat = story.face_material(KIT, face_img, uvs)
    bl_anim.key_value(m_mat.node_tree, m_scene.LOOK_PATH,
                      [(frame_of(LOOK_CHANGE[0]), 1.0), (frame_of(LOOK_CHANGE[1]), 0.0)])
    pivot = KIT.new_object("pivot")
    pivot.empty_display_size = 0.5
    bl_anim.key_value(pivot, "scale", [(frame_of(M_IN[0]), (0.0,) * 3), (frame_of(M_IN[1]), (1.0,) * 3)])
    bl_anim.key_value(pivot, "rotation_euler",
                      [(f, (0.0, 0.0, 2.0 * math.pi * smoothstep(time_of(f), *M_TURN))) for f in frames],
                      interpolation='LINEAR')
    orient = KIT.new_object("orient", parent=pivot)
    orient.rotation_euler = [math.radians(a) for a in story.ORIENT_EULER_DEG]
    m_obj = KIT.new_object("M", m_scene.merged_mesh(KIT, md, m_mat, uvs), parent=orient)
    bl_utils.merge_by_distance(m_obj)

    V_m = np.asarray(md.vertices, dtype=float)
    f0 = md.faces[0]
    edge = float(np.linalg.norm(V_m[f0[0]] - V_m[f0[1]]))
    m_radius = float(np.linalg.norm(V_m, axis=1).max())     # M e' centrato in origine
    floor_z = -(m_radius + CLEARANCE)

    # --- la platea ---
    pieces = load_pieces(edge)
    corridor = corridor_radius(m_radius)
    jumped = arrange(pieces, m_radius, floor_z, corridor)
    # da fuori verso dentro
    vanish_order = sorted(pieces, key=lambda p: (-np.linalg.norm(p.location[:2]), p.name))
    gap = (OTHERS_ALL_IN - OTHERS_AT - OTHERS_GROW) / (len(pieces) - 1)
    for k, p in enumerate(pieces):
        mesh = bpy.data.meshes.new(KIT.name(p.name))
        mesh.from_pydata([tuple(v) for v in p.V], [], p.faces)
        mesh.materials.append(m_scene.wire_material(KIT, f"mat_{p.name}", story.pastel(hue_of(k)),
                                                    roughness=ROUGHNESS))
        mesh.update()
        obj = KIT.new_object(p.name, mesh)
        obj.location = tuple(p.location)
        t_in = OTHERS_AT + k * gap
        t_out = VANISH_AT + vanish_order.index(p) * VANISH_GAP
        bl_anim.key_value(obj, "scale", [(frame_of(t_in), (0.0,) * 3), (frame_of(t_in + OTHERS_GROW), (1.0,) * 3),
                                         (frame_of(t_out), (1.0,) * 3),
                                         (frame_of(t_out + VANISH_SECONDS), (0.0,) * 3)])
        bl_anim.key_visibility(obj, [(FRAME_START, False), (frame_of(t_in) + 1, True),
                                     (frame_of(t_out + VANISH_SECONDS) + 1, False)])
        phase = 2.0 * math.pi * ((k * 0.618034) % 1.0)
        spin = 2.0 * math.pi / (OTHER_SECONDS_PER_TURN * FPS)
        obj.rotation_mode = 'XYZ'
        bl_anim.key_value(obj, "rotation_euler",
                          [(FRAME_START, (0.0, 0.0, phase)),
                           (FRAME_END, (0.0, 0.0, phase + spin * (FRAME_END - FRAME_START)))],
                          interpolation='LINEAR')

    # --- pavimento, cielo ---
    floor = m_scene.build_floor(KIT, FLOOR_SRGB, FLOOR_ROUGHNESS, FLOOR_SPECULAR, FLOOR_SIZE, fading=True)
    floor.location.z = floor_z
    bl_anim.key_value(floor.active_material.node_tree, m_scene.FADE_PATH,
                      [(frame_of(FLOOR_FADE[0]), 1.0), (frame_of(FLOOR_FADE[1]), 0.0)])
    bl_anim.key_visibility(floor, [(FRAME_START, True), (frame_of(FLOOR_FADE[1]) + 1, False)])
    m_scene.setup_sky_world(KIT, math.radians(SKY_SUN_ELEVATION),
                            m_scene.sky_rotation(-Vector(story.LIGHT_DIRECTION)), story.SKY_STRENGTH,
                            sun_size=math.radians(SUN_SIZE_DEG))

    # --- la camera: dall'alto, il volo, la camera del quadro ---
    rig = layout.rig
    view = deltahedra.View(CAMERA_ELEVATION, layout.lens, rig.sensor_width, rig.aspect)
    centres = [np.zeros(3)] + [p.location for p in pieces]
    sizes = [m_radius] + [p.radius for p in pieces]
    start_target, start_distance = deltahedra.frame_all(view, centres, sizes, START_FILL)
    start = start_target + view.back * start_distance
    # il poliedro piu' vicino al punto in cui la camera entra nel giro: e' quello
    # che sfiora per primo
    entry = np.array([corridor, 0.0])
    grazed = min(pieces, key=lambda p: np.linalg.norm(p.location[:2] - entry) - p.radius)
    flight = Flight(start, start_target, layout.lens, np.asarray(layout.eye), layout.lens,
                    corridor, FLY_HEIGHT, grazed.location)
    cam = rig.build(KIT, Vector(start), clip_end=BACKGROUND_DEPTH + 20.0)
    cam.data.lens = layout.lens
    cam.rotation_mode = 'QUATERNION'
    poses = [(f, flight.at(time_of(f))) for f in frames]
    # niente salti di segno fra quaternioni vicini: Blender li interpola componente per componente
    quats, prev = [], None
    for _, (_, q, _) in poses:
        q = q.copy()
        if prev is not None and prev.dot(q) < 0.0:
            q.negate()
        quats.append(q)
        prev = q
    bl_anim.key_value(cam, "location", [(f, tuple(p)) for f, (p, _, _) in poses], interpolation='LINEAR')
    bl_anim.key_value(cam, "rotation_quaternion", [(f, tuple(q)) for (f, _), q in zip(poses, quats)],
                      interpolation='LINEAR')
    bl_anim.key_value(cam.data, "lens", [(f, lens) for f, (_, _, lens) in poses], interpolation='LINEAR')
    m_scene.build_background(KIT, rig, cam, layout.lens, BACKGROUND_DEPTH,
                             story.BACKGROUND_CORNERS_SRGB, story.BACKGROUND_BLEED)

    # la camera non entra mai nei poliedri (le sfere che li contengono) ne' in M
    closest = min((np.linalg.norm(np.asarray(p) - c) - r, time_of(f))
                  for f, (p, _, _) in poses for c, r in zip(centres, sizes))
    if closest[0] < MIN_DISTANCE:
        raise ValueError(f"la camera passa a {closest[0]:.2f} da un poliedro a {closest[1]:.2f} s")
    jerk, spin_acc, spin_max = roughness([pose for _, pose in poses])

    # --- il quadro ---
    painting, p_mat = story.build_painting(KIT, painting_img, layout)
    bl_anim.key_value(p_mat.node_tree, m_scene.FADE_PATH,
                      [(frame_of(PAINT_IN[0]), 0.0), (frame_of(PAINT_IN[1]), 1.0)])
    bl_anim.key_visibility(painting, [(FRAME_START, False), (frame_of(PAINT_IN[0]), True)])

    scene.frame_set(FRAME_START)
    print(f"[scene-7 v2] frame {FRAME_START}-{FRAME_END} a {FPS} fps ({END:.0f} s); spigolo {edge:.4f}, "
          f"M raggio {m_radius:.3f}, pavimento a z = {floor_z:.3f}")
    print(f"[scene-7 v2] il giro della camera a raggio {corridor:.2f}, all'altezza {FLY_HEIGHT} "
          f"(il centro di M e' a 0), in media a {flight.mean_speed:.1f} unita' al secondo; la "
          f"spirale salta la striscia davanti a M con: " + ", ".join(jumped))
    for k, p in enumerate(pieces):
        x, y = p.location[:2]
        print(f"[scene-7 v2]   {k:2d} {p.name} ({len(p.faces)} facce, raggio {p.radius:.2f}): "
              f"a {math.hypot(x, y):5.2f} da M, {math.degrees(math.atan2(y, x)):7.1f} gradi")
    print(f"[scene-7 v2] camera: all'inizio a {start_distance:.1f} dal centro della platea; sfiora "
          f"{grazed.name}; passa al minimo a {closest[0]:.2f} da una sfera ({closest[1]:.2f} s)")
    print(f"[scene-7 v2] strappi: derivata terza della posizione al piu' {jerk:.0f} unita'/s^3; "
          f"rotazione al piu' {spin_max:.0f} gradi/s, accelerazione angolare al piu' "
          f"{spin_acc:.0f} gradi/s^2")


build()
