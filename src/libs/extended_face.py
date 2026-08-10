"""
Costruzione della "faccia estesa" del poliedro M di Saffaro.

Il poliedro M nasce da un icosaedro regolare sostituendo ogni faccia triangolare
con una "faccia estesa": un ventaglio (fan) di 12 triangoli equilateri identici
che condividono un vertice comune (l'apice, o centro del ventaglio) e formano un
anello chiuso con simmetria di ordine 3 attorno all'asse dell'apice.

Ogni lato del triangolo di partenza viene sostituito da SEG_PER_EDGE=4 segmenti
unitari ripiegati; i 3 lati danno quindi 3*4 = 12 triangoli. I 4 segmenti che
sostituiscono un lato giacciono su un unico piano: quando questo piano passa per
il centro dell'icosaedro, due facce estese adiacenti si saldano senza fessure e
il poliedro M "si chiude". Questo accade per un solo valore del parametro, che
`find_closing_parameter()` individua per bisezione.

Convenzioni:
- i triangoli hanno lato 1 (normalizzazione implicita: r = 0.5/sin(phi/2) rende
  unitari i 4 lati uguali);
- il parametro `phi` e' l'angolo sotto cui, dal centro dell'arco, si vedono i 4
  lati uguali del bordo. Dominio valido: phi in (60°, 90°). Vedi `edge_span` per
  un parametro alternativo piu' intuitivo.

Nessuna dipendenza da Blender.
"""

import math

import numpy as np

import geometry
from geometry import Vector, MeshData

# --- costanti strutturali della faccia estesa ---
N_EDGES = 3                       # nasce da un triangolo: 3 lati
SEG_PER_EDGE = 4                  # ogni lato e' sostituito da 4 segmenti unitari
N_TRIANGLES = N_EDGES * SEG_PER_EDGE   # 12 triangoli equilateri (= vertici esterni)

# Dominio del parametro phi: sotto i 60° si avrebbe r>=1, sopra i 90° a<=0.
PHI_MIN = math.pi / 3            # 60°
PHI_MAX = math.pi / 2            # 90°

# Valore di phi che chiude il poliedro M (le facce estese adiacenti si saldano
# senza fessura). Calcolato con find_closing_parameter(); qui congelato come
# costante per non ripetere la bisezione a ogni uso.
#   PHI_CLOSING = 1.282675310973946 rad = 73.491882°   (a = 0.9107570938533813)
PHI_CLOSING = 1.282675310973946


def edge_span(phi):
    """Lunghezza in linea retta del bordo di base (la corda che sottende i 4
    segmenti ripiegati), in unita' di lato del triangolo piccolo.

        a = 4 * cos(phi/2) * cos(phi)

    E' un parametro alternativo a `phi`, piu' facile da descrivere: e' il
    rapporto fra il lato del triangolo di partenza e quello delle tessere. E'
    una biiezione monotona decrescente: a va da sqrt(3) (phi=60°) a 0 (phi=90°).
    """
    return 4.0 * math.cos(phi / 2) * math.cos(phi)


def phi_from_edge_span(a, iters=100):
    """Inversa numerica di `edge_span`: dato `a` in (0, sqrt(3)) restituisce il
    corrispondente `phi` in (60°, 90°). Utile per pilotare la costruzione con il
    parametro geometrico `a` invece che con l'angolo `phi`."""
    if not (0.0 < a < math.sqrt(3)):
        raise ValueError(f"a deve stare in (0, sqrt(3)), ricevuto {a}")
    # edge_span e' decrescente: bisezione classica sul dominio di phi.
    lo, hi = PHI_MIN, PHI_MAX
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if edge_span(mid) > a:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def make_extended_face(phi):
    """Calcola le coordinate della faccia estesa (ventaglio di 12 triangoli
    equilateri unitari) per il valore `phi` del grado di liberta'.

    Restituisce un `MeshData` con 13 vertici (i 12 esterni in ordine lungo
    l'anello, indici 0..11, piu' l'apice all'indice 12) e 12 facce triangolari.

    Il parametro `phi` deve stare in (60°, 90°): al di fuori la costruzione e'
    degenere. Per il valore che chiude il poliedro M usare
    `find_closing_parameter()`.
    """
    if not (PHI_MIN < phi < PHI_MAX):
        raise ValueError(
            f"phi deve stare in ({math.degrees(PHI_MIN):.0f}°, "
            f"{math.degrees(PHI_MAX):.0f}°), ricevuto {math.degrees(phi):.2f}°"
        )

    sn_half_phi = math.sin(phi / 2)
    r = 0.5 / sn_half_phi                 # raggio dell'arco; 2*r*sin(phi/2)=1 -> lato=1
    a = math.sin(2 * phi) / sn_half_phi   # = edge_span(phi): corda del bordo di base
    cm = (1 - r**2)**0.5                  # centro arco -> centro del ventaglio
    cp = (1 - (a / 2)**2)**0.5            # centro ventaglio -> punto medio del lato di base
    cq = (cp**2 - a**2 / 12)**0.5         # altezza dell'apice sul triangolo di base
    cpq = math.asin(cq / cp)
    cpm = math.asin(cm / cp)
    offset = r * math.cos(math.pi - 2 * phi)
    theta = math.pi - cpq - cpm           # inclinazione del piano dei 5 punti del bordo
    cs_theta = math.cos(theta)
    sn_theta = math.sin(theta)

    base_r = a * 3**0.5 / 3               # circonraggio del triangolo di base (lato a)
    base = []
    for i in range(N_EDGES):
        angle = math.pi * 2 * (i + 1) / N_EDGES
        base.append(Vector((base_r * math.cos(angle), base_r * math.sin(angle), 0)))

    pts = []
    for i in range(N_EDGES):
        pa = base[i]
        pb = base[(i + 1) % N_EDGES]
        pab = (pa + pb) / 2
        e0 = (pb - pa).normalized()                                   # lungo il lato
        e1 = pab.normalized() * cs_theta + Vector((0, 0, 1)) * sn_theta  # nel piano inclinato
        orig = pab + e1 * offset                                      # centro dell'arco del bordo
        pts.append(pa.tup())                                          # vertice del triangolo di base
        for j in range(-1, 2):                                        # 3 punti interni (SEG_PER_EDGE-1)
            angle = j * phi
            x = r * math.sin(angle)
            y = r * math.cos(angle)
            p = orig + e0 * x + e1 * y
            pts.append(p.tup())
    pts.append((0, 0, cq))                                            # apice, indice N_TRIANGLES

    faces = [[N_TRIANGLES, i, (i + 1) % N_TRIANGLES] for i in range(N_TRIANGLES)]

    mesh_data = MeshData()
    mesh_data.vertices = pts
    mesh_data.faces = faces
    return mesh_data


# --- ricerca del parametro che chiude il poliedro M ---------------------------

# Indici dei vertici interni del bordo condiviso fra due facce estese adiacenti,
# per la coppia di facce ico.faces[0]=(0,1,8) e ico.faces[1]=(0,8,4), entrambi
# ordinati lungo lo spigolo v0->v8. Servono a misurare la fessura di saldatura.
_SHARED_MID_FACE0 = 10   # punto interno centrale del bordo, lato faccia 0
_SHARED_MID_FACE1 = 2    # stesso punto, lato faccia 1


def _closure_gap_vector(phi):
    """Vettore-scarto fra le due copie del punto interno centrale dello spigolo
    condiviso da due facce estese adiacenti, dopo averle posate sull'icosaedro.
    E' nullo esattamente quando M si chiude; cambia verso attraversando phi*."""
    ico = geometry.Polyhedron.ico
    ico_side = (ico.vertices[ico.faces[0][0]] - ico.vertices[ico.faces[0][1]]).length()
    md = make_extended_face(phi)

    def place(face):
        corners = [Vector(md.vertices[SEG_PER_EDGE * i]) for i in range(N_EDGES)]
        a = (corners[0] - corners[1]).length()
        factor = a / ico_side                     # scala l'ico al lato del triangolo di base
        qs = [ico.vertices[face[j]] * factor for j in range(3)]
        mat = geometry.matrix_from_triples(corners, qs)
        return geometry.transform_points(mat, md.vertices)

    w0 = place(ico.faces[0])
    w1 = place(ico.faces[1])
    return w0[_SHARED_MID_FACE0] - w1[_SHARED_MID_FACE1]


def find_closing_parameter(lo=None, hi=None, iters=100):
    """Trova per bisezione il valore di `phi` che chiude il poliedro M, cioe' per
    cui due facce estese adiacenti si saldano senza fessura.

    L'obiettivo con segno e' la proiezione del vettore-scarto di saldatura lungo
    la direzione (fissa) su cui esso si inverte attraversando la chiusura.

    `lo`, `hi` (radianti) devono racchiudere phi* con segni opposti; i valori di
    default (72°, 75°) vanno bene per M. Restituisce phi* (~1.28268 rad ~ 73.49°).
    """
    if lo is None:
        lo = math.radians(72)
    if hi is None:
        hi = math.radians(75)

    # direzione di riferimento: l'asse su cui lo scarto si inverte fra lo e hi.
    ref = _closure_gap_vector(lo) - _closure_gap_vector(hi)
    ref = ref / np.linalg.norm(ref)

    def g(phi):
        return float(_closure_gap_vector(phi) @ ref)

    flo, fhi = g(lo), g(hi)
    if flo * fhi > 0:
        raise ValueError("intervallo non valido: g(lo) e g(hi) hanno lo stesso segno")

    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        fm = g(mid)
        if flo * fm <= 0:
            hi = mid
        else:
            lo, flo = mid, fm
    return 0.5 * (lo + hi)


def make_M(phi=PHI_CLOSING):
    """Costruisce il poliedro M completo come un unico MeshData.

    Strategia:
    1. crea una faccia estesa con il parametro di chiusura `phi` (di default la
       costante precalcolata PHI_CLOSING);
    2. scala l'icosaedro di riferimento in modo che il lato delle sue facce
       coincida con il lato `a` del triangolo di base della faccia estesa;
    3. per ognuna delle 20 facce calcola la matrice che roto-trasla il triangolo
       di base sulla faccia scalata (matrix_from_triples) e vi trasporta una copia
       della faccia estesa;
    4. fonde le 20 copie in un solo MeshData con MeshData.append.

    I vertici sugli spigoli condivisi restano duplicati (due copie coincidenti):
    per saldarli si puo' usare un "merge by distance" in Blender.
    """
    ico = geometry.Polyhedron.ico
    ico_side = (ico.vertices[ico.faces[0][0]] - ico.vertices[ico.faces[0][1]]).length()

    base = make_extended_face(phi)
    corners = [Vector(base.vertices[SEG_PER_EDGE * i]) for i in range(N_EDGES)]
    a = (corners[0] - corners[1]).length()
    factor = a / ico_side                      # scala l'ico al lato del triangolo di base

    M = MeshData()
    for face in ico.faces:
        qs = [ico.vertices[face[j]] * factor for j in range(3)]
        mat = geometry.matrix_from_triples(corners, qs)
        piece = MeshData()
        piece.vertices = geometry.transform_points(mat, base.vertices).tolist()
        piece.faces = base.faces               # stessa topologia; append rimappa gli indici
        M.append(piece)
    return M


def _equidistant_point(p, q, r, dist, reference):
    """Punto a distanza `dist` da tutti e tre i punti p, q, r.

    E' l'intersezione di tre sfere di raggio `dist`: le soluzioni sono due,
    simmetriche rispetto al piano di p, q, r, e si sceglie quella che sta dalla
    stessa parte del punto `reference` (cosi' il risultato resta dalla parte da
    cui si arriva, invece di ribaltarsi).

    Il centro delle due soluzioni e' il circocentro di pqr, che si ricava dal
    sistema lineare "equidistante da p,q,r" + "nel piano di p,q,r".
    """
    u = q - p
    v = r - p
    n = u.cross(v)
    if n.length2() == 0.0:
        raise ValueError("_equidistant_point(): i tre punti sono allineati o coincidenti")

    # circocentro: (c-p).u = |u|^2/2, (c-p).v = |v|^2/2, (c-p).n = 0
    center = p + Vector(np.linalg.solve(
        np.array([u.a, v.a, n.a]),
        np.array([0.5 * u.length2(), 0.5 * v.length2(), 0.0]),
    ))
    h2 = dist**2 - (center - p).length2()   # distanza dal piano, al quadrato
    if h2 < 0.0:
        raise ValueError(
            f"_equidistant_point(): nessuna soluzione, il circoraggio "
            f"({(center - p).length():.6f}) supera la distanza richiesta ({dist:.6f})"
        )

    offset = n.normalized() * math.sqrt(h2)
    if (reference - center).dot(offset) < 0.0:
        offset = offset * -1.0
    return center + offset


def flatten1_extended_face(md):
    """Trasforma la faccia estesa md in una faccia estesa a 6 triangoli
    equilateri. I vertici P0, P4, P8 (e l'apex P12) restano fissi;
    I vertici P2, P6, P10 vengono spostati in modo da formare triangoli equilateri
    con i vertici fissi. I vertici P1,P3, ecc. vengono messi nei punti medi dei
    segmenti P0-P2, P4-P6, ecc.
    Restituisce un nuovo MeshData con gli stessi vertici e facce di `md`, ma
    con le coordinate modificate.

    Costruzione: perche' il triangolo (apice, P0, P2) e quello (apice, P2, P4)
    siano equilateri di lato s = |apice-P0|, il nuovo P2 deve stare a distanza s
    dall'apice, da P0 e da P4: e' l'intersezione di tre sfere (vedi
    `_equidistant_point`), di cui si prende la soluzione dalla parte del vecchio
    P2. Mettendo poi P1 e P3 nei punti medi, i due triangolini che li usano
    restano complanari con la meta' di ventaglio a cui appartengono: la mesh
    conserva 13 vertici e 12 facce ma "si vede" come 6 triangoli.

    Nota: i 6 triangoli sommano 6*60 = 360 gradi attorno all'apice, quindi la
    faccia estesa diventa sviluppabile (un pezzo di carta piano, ma piegato lungo
    le tre diagonali apice-P0, apice-P4, apice-P8).
    """
    if len(md.vertices) != N_TRIANGLES + 1:
        raise ValueError(
            f"flatten1_extended_face(): attesa una faccia estesa con "
            f"{N_TRIANGLES + 1} vertici, ricevuti {len(md.vertices)}"
        )

    pts = [Vector(v) for v in md.vertices]
    apex = pts[N_TRIANGLES]
    side = apex.dist(pts[0])          # lato dei triangoli del ventaglio (1 per costruzione)
    half = SEG_PER_EDGE // 2          # 2: passo fra un vertice dell'esagono e il successivo

    # i 3 vertici mobili dell'esagono (P2, P6, P10)
    for i in range(N_EDGES):
        k = SEG_PER_EDGE * i + half
        corner0 = pts[SEG_PER_EDGE * i]
        corner1 = pts[SEG_PER_EDGE * ((i + 1) % N_EDGES)]
        pts[k] = _equidistant_point(apex, corner0, corner1, side, reference=pts[k])

    # i vertici rimasti finiscono nei punti medi dei lati dell'esagono
    for k in range(1, N_TRIANGLES, half):
        pts[k] = (pts[k - 1] + pts[(k + 1) % N_TRIANGLES]) / 2

    new_md = MeshData()
    new_md.vertices = [p.tup() for p in pts]
    new_md.faces = md.faces.copy()
    return new_md


def flatten2_extended_face(md):
    """Trasforma la faccia estesa md in un singolo triangolo.
    i vertici P0, P4 e P8 rimangono fissi. 
    P12 va al centro del triangolo P0,P4,P8. 
    I vertici P1,P2,P3 sono rispettivamente ad 1/4, 2/4 e 3/4 del segmento P0-P4.
    Analogamente per gli altri due lati.
    Restituisce un nuovo MeshData con gli stessi vertici e facce di `md`, ma con le coordinate modificate.

    E' il ventaglio completamente appiattito: tutti i vertici finiscono sul piano
    del triangolo di base e le 12 facce, invece di degenerare, tassellano
    esattamente il triangolo P0-P4-P8 (i 12 spicchi che si ottengono unendo il
    baricentro ai 12 punti del bordo). Insieme a `flatten1_extended_face` da' la
    sequenza triangolo -> 6 triangoli -> 12 triangoli usata per il morphing.

    Usa solo P0, P4, P8, che sono fissi anche in `flatten1_extended_face`: la si
    puo' quindi applicare indifferentemente alla faccia estesa o al risultato di
    flatten1.
    """
    if len(md.vertices) != N_TRIANGLES + 1:
        raise ValueError(
            f"flatten2_extended_face(): attesa una faccia estesa con "
            f"{N_TRIANGLES + 1} vertici, ricevuti {len(md.vertices)}"
        )

    pts = [Vector(v) for v in md.vertices]
    corners = [pts[SEG_PER_EDGE * i] for i in range(N_EDGES)]

    # ogni lato del triangolo di base torna dritto: i SEG_PER_EDGE-1 punti
    # intermedi si distribuiscono uniformemente fra un angolo e il successivo
    for i in range(N_EDGES):
        p0 = corners[i]
        p1 = corners[(i + 1) % N_EDGES]
        for j in range(1, SEG_PER_EDGE):
            pts[SEG_PER_EDGE * i + j] = p0 + (p1 - p0) * (j / SEG_PER_EDGE)

    # l'apice scende nel baricentro del triangolo di base
    pts[N_TRIANGLES] = Vector(np.mean([c.a for c in corners], axis=0))

    new_md = MeshData()
    new_md.vertices = [p.tup() for p in pts]
    new_md.faces = md.faces.copy()
    return new_md


def morph(md1, md2, t):
    """Interpolate linearly between two MeshData objects with the same topology.
    `t` in [0,1] gives the interpolation factor: 0 returns md1, 1 returns md2."""
    if len(md1.vertices) != len(md2.vertices):
        raise ValueError("morph(): MeshData must have the same number of vertices")
    if len(md1.faces) != len(md2.faces):
        raise ValueError("morph(): MeshData must have the same number of faces")

    new_md = MeshData()
    new_md.vertices = [
        tuple((1 - t) * np.array(v1) + t * np.array(v2))
        for v1, v2 in zip(md1.vertices, md2.vertices)
    ]
    new_md.faces = md1.faces.copy()  # same topology
    return new_md

