"""
Utilità geometriche per la costruzione del modello M2 di Lucio Saffaro.

Il modello M2 nasce da un icosaedro regolare: su ciascuna delle sue 20 facce
triangolari viene innalzata una struttura a "ventaglio" (FaceFan). L'idea è
sollevare un vertice sopra il centro della faccia e raccordare la faccia con un
arco di circonferenza, in modo che le strutture di facce adiacenti si incontrino
con la giusta inclinazione lungo gli spigoli condivisi.

Il parametro chiave che governa la forma viene scelto (get_M2_parameter) in modo
che l'angolo di apertura del ventaglio combaci con metà dell'angolo diedro
dell'icosaedro: così le porzioni provenienti da due facce adiacenti risultano
tangenti/complanari e il solido si chiude in modo coerente.

Struttura del modulo:
  - Vector                : vettore 3D con le operazioni di base.
  - Polyhedron            : poliedro generico (vertici + facce), con l'icosaedro
                            di riferimento pre-costruito in Polyhedron.ico.
  - make_icosahedron      : costruzione dell'icosaedro regolare.
  - compute_angle_from_sides : teorema del coseno.
  - FaceFanData           : calcolo dei parametri geometrici del ventaglio.
  - get_M2_parameter      : ricerca del parametro caratteristico di M2.
  - FaceFan               : generazione dei punti 3D del ventaglio su una faccia.
  - MeshData              : contenitore di vertici e facce della mesh finale.
  - make_M2_mesh_data     : assemblaggio dell'intera mesh M2 sui 20 triangoli.
"""

import numpy as np


class Vector:
    """Vettore in R^3 con le operazioni algebriche e metriche essenziali."""

    def __init__(self, tup = (0,0,0)):
        # Inizializza le tre componenti a partire da una tupla/lista (x, y, z).
        self.x, self.y, self.z = tup

    def __repr__(self):
        # Rappresentazione testuale compatta "(x,y,z)".
        return f"({self.x},{self.y},{self.z})"

    def __add__(self, other):
        # Somma componente per componente.
        return Vector((self.x+other.x,self.y+other.y,self.z+other.z))

    def __sub__(self, other):
        # Differenza componente per componente.
        return Vector((self.x-other.x,self.y-other.y,self.z-other.z))

    def __mul__(self, k):
        # Moltiplicazione per uno scalare k.
        return Vector((self.x*k,self.y*k,self.z*k))
    def __truediv__(self, k):
        # Divisione per uno scalare k.
        return Vector((self.x/k,self.y/k,self.z/k))

    def length(self):
        # Norma euclidea (modulo) del vettore.
        return (self.x**2+self.y**2+self.z**2)**0.5
    def length2(self):
        # Norma al quadrato: evita la radice quando serve solo confrontare distanze.
        return (self.x**2+self.y**2+self.z**2)
    def dist(self, other):
        # Distanza euclidea tra questo punto e un altro.
        return (self-other).length()

    def normalized(self):
        # Restituisce il versore (vettore di modulo 1) con la stessa direzione.
        d = 1.0/self.length()
        return Vector((self.x*d,self.y*d,self.z*d))

    def cross(self,other):
        # Prodotto vettoriale: restituisce un vettore ortogonale a self e other.
        return Vector((
            self.y*other.z-self.z*other.y,
            self.z*other.x-self.x*other.z,
            self.x*other.y-self.y*other.x))

    def tup(self):
        # Converte il vettore in una tupla (x, y, z), utile per l'export dei punti.
        return (self.x,self.y,self.z)


class Polyhedron:
    """Poliedro descritto da una lista di vertici e dalle facce (indici dei vertici)."""

    def __init__(self, vertices, faces):
        self.vertices = vertices  # lista di Vector
        self.faces = faces        # lista di tuple di indici nella lista dei vertici

    def get_face_vertices(self, idx):
        # Restituisce i Vector che compongono la faccia idx-esima.
        assert 0<=idx<len(self.faces)
        return [self.vertices[i] for i in self.faces[idx]]


def make_icosahedron():
    """Costruisce un icosaedro regolare inscritto in una sfera unitaria.

    I 12 vertici sono le combinazioni cicliche di (0, ±1, ±PHI) con PHI sezione
    aurea; vengono normalizzati per giacere sulla sfera di raggio 1. Le 20 facce
    triangolari sono elencate con orientamento coerente (normali uscenti).
    """
    PHI = (1.0 + 5.0 ** 0.5) / 2.0  # golden ratio

    # Icosahedron vertices on a unit circumscribed sphere
    vertices = [v.normalized() for v in [
        Vector([ 0.0,  1.0,  PHI]),
        Vector([ 0.0, -1.0,  PHI]),
        Vector([ 0.0,  1.0, -PHI]),
        Vector([ 0.0, -1.0, -PHI]),
        Vector([ 1.0,  PHI,  0.0]),
        Vector([-1.0,  PHI,  0.0]),
        Vector([ 1.0, -PHI,  0.0]),
        Vector([-1.0, -PHI,  0.0]),
        Vector([ PHI,  0.0,  1.0]),
        Vector([-PHI,  0.0,  1.0]),
        Vector([ PHI,  0.0, -1.0]),
        Vector([-PHI,  0.0, -1.0])
    ]]

    faces = [
        (0, 1, 8), (0, 8, 4), (0, 4, 5), (0, 5, 9), (0, 9, 1),
        (1, 6, 8), (8, 6, 10), (8, 10, 4), (4, 10, 2), (4, 2, 5),
        (5, 2, 11), (5, 11, 9), (9, 11, 7), (9, 7, 1), (1, 7, 6),
        (3, 6, 7), (3, 7, 11), (3, 11, 2), (3, 2, 10), (3, 10, 6),
    ]
    return Polyhedron(vertices, faces)

# Icosaedro di riferimento condiviso, usato come base per il modello M2.
Polyhedron.ico = make_icosahedron()

def compute_angle_from_sides(a,b,c):
    """Teorema del coseno: dato un triangolo con lati a, b, c, restituisce
    l'angolo (in radianti) opposto al lato a."""
    cosA = (b**2+c**2-a**2)/(2*b*c)
    return np.arccos(cosA)


class FaceFanData:
    """Calcola le grandezze geometriche del ventaglio innalzato su una faccia.

    A partire dai tre vertici della faccia e dal parametro adimensionale `param`
    (che regola quanto viene sollevato l'apice sopra il baricentro), ricava:
      - base_edge     : lunghezza dello spigolo di base della faccia,
      - triangle_side : lato inclinato dall'apice sollevato a un vertice di base,
      - h             : distanza dall'apice al punto medio dello spigolo di base,
      - radius        : raggio dell'arco di raccordo (vedi _compute_radius),
      - h1_low, h1    : quote geometriche del centro dell'arco,
      - theta         : angolo di apertura del ventaglio.
    Espone inoltre i punti/direzioni di base della faccia (center, normal, p3,
    p01), riutilizzati da FaceFan per generare i punti 3D senza ricalcolarli.
    """

    def __init__(self, pts, param):
        p0,p1,p2 = pts
        self.param = param
        # Spigolo di base della faccia (i triangoli sono equilateri: basta un lato).
        self.base_edge = base_edge = p0.dist(p1)
        self.center = center = (p0+p1+p2)/3        # baricentro della faccia
        self.normal = normal = (p1-p0).cross(p2-p0).normalized()  # normale uscente alla faccia
        # Apice sollevato sopra il baricentro lungo la normale, di param*base_edge.
        self.p3 = p3 = center + normal * (param * base_edge)
        # Lato inclinato: distanza da un vertice di base all'apice sollevato.
        self.triangle_side = triangle_side = p0.dist(p3)
        self.p01 = p01 = (pts[0]+pts[1])/2      # punto medio dello spigolo di base p0-p1
        # Altezza del triangolo laterale: dall'apice al punto medio dello spigolo.
        self.h = h = (p3-p01).length()

        # Raggio dell'arco di circonferenza che raccorda le facce adiacenti.
        self.radius = radius = self._compute_radius(triangle_side, base_edge)

        # Quote del centro dell'arco rispetto allo spigolo di base:
        # h1_low = distanza dal centro dell'arco alla corda (spigolo di base).
        self.h1_low = h1_low = (radius**2-(base_edge/2)**2)**0.5
        self.h1 = h1 = radius + h1_low

        # Angolo di apertura theta del ventaglio, ottenuto scomponendo l'angolo
        # nel triangolo che lega apice, punto medio dello spigolo e centro dell'arco.
        theta0 = np.arcsin((param*base_edge)/h)
        theta1 = compute_angle_from_sides(triangle_side, h, h1)
        theta = np.pi - (theta0 + theta1)
        self.theta = theta

    def _compute_radius(self, a, b):
        """Trova per bisezione il raggio r dell'arco tale che f(r, a) = b.

        f(r, a) = 2 r sin(pi - 4 arcsin(a/(2r))) è la corda sottesa dall'arco in
        funzione del raggio; la si inverte numericamente affinché combaci con la
        lunghezza `b` (lo spigolo di base). Gli estremi r0, r1 racchiudono la
        soluzione e le assert verificano che il segno sia opposto (radice interna).
        """
        def f(r,a):
            phi = (np.pi - 4*np.arcsin(a*0.5/r))
            return 2 * r * np.sin(phi)
        r0 = a/2**0.5
        r1 = a/(2*np.sin(np.pi/8))
        assert f(r0,a)<b
        assert f(r1,a)>b
        assert r0<r1
        while r1-r0>1.0e-15:
            r = (r0+r1)/2
            v = f(r,a)
            if v<b: r0=r
            else: r1=r
        return r

def get_M2_parameter():
    """Determina per bisezione il parametro `param` caratteristico del modello M2.

    Si cerca il valore per cui l'angolo di apertura del ventaglio (theta) è pari a
    metà dell'angolo diedro dell'icosaedro, arccos(-sqrt(5)/3): questa condizione
    fa sì che i ventagli di due facce adiacenti si raccordino correttamente lungo
    lo spigolo comune.
    """
    face = Polyhedron.ico.get_face_vertices(0)
    def f(param):
        p = FaceFanData(face, param)
        return p.theta
    dihedral_angle = np.arccos(-5**0.5/3)

    target = dihedral_angle/2 #(2*np.pi - dihedral_angle)/2

    # Intervallo iniziale: theta è decrescente in param, quindi f(p0)>target>f(p1).
    p0 = 0.2
    p1 = 1.0
    assert f(p0)>target
    assert f(p1)<target

    while p1-p0>1.0e-15:
        p = (p0+p1)/2
        v = f(p)
        if v>target: p0 = p
        else: p1 = p
    return p

class FaceFan:
    """Genera i punti 3D del ventaglio costruito su una singola faccia triangolare.

    A partire dai tre vertici della faccia (pts) e dal parametro adimensionale
    `parameter` — dal quale ricava internamente i FaceFanData — colloca nello spazio:
      - p0, p1, p2 : i vertici originali della faccia,
      - p3         : l'apice sollevato sopra il baricentro,
      - q0         : il vertice dell'arco sul piano di simmetria del ventaglio,
      - q1, q2     : gli estremi laterali dell'arco di raccordo.
    Il risultato è salvato in self.points come lista di tuple (x, y, z).
    """

    def __init__(self, pts, parameter):
        self.pts = pts
        p0,p1,p2 = pts
        face_fan_data = FaceFanData(pts, parameter)

        # Punti e direzioni della faccia, già calcolati da FaceFanData.
        center = face_fan_data.center   # baricentro della faccia
        normal = face_fan_data.normal   # normale uscente
        p3 = face_fan_data.p3           # apice sollevato sopra il baricentro
        p01 = face_fan_data.p01         # punto medio dello spigolo di base

        # Parametri geometrici precalcolati.
        theta = face_fan_data.theta
        radius = face_fan_data.radius
        h1 = face_fan_data.h1
        h1_low = face_fan_data.h1_low
        triangle_side = face_fan_data.triangle_side

        # Terna ortonormale locale del ventaglio:
        #  e0 = direzione dal centro verso il punto medio dello spigolo (nel piano faccia),
        #  e1 = e0 ruotato di theta verso la normale (direzione di apertura del ventaglio),
        #  e2 = direzione dello spigolo di base (per l'apertura laterale dell'arco).
        e0 = (p01-center).normalized()
        e1 = e0 * np.cos(theta) + normal * np.sin(theta)
        e2 = (p1-p0).normalized()

        # q0: punto dell'arco sul piano di simmetria, a distanza h1 lungo e1.
        q0 = p01 + e1 * h1
        # phi: semiapertura angolare dell'arco vista dal suo centro.
        phi = 2 * np.arcsin(triangle_side/(2*radius))
        # q1, q2: estremi laterali dell'arco, ottenuti ruotando di ±phi attorno al centro.
        q1 = p01 + e1 * h1_low + (e1 * np.cos(phi) + e2 * np.sin(phi)) * radius
        q2 = p01 + e1 * h1_low + (e1 * np.cos(phi) - e2 * np.sin(phi)) * radius

        # Esporta tutti i punti come tuple (x, y, z).
        self.points = [p.tup() for p in [p0,p1,p2,p3,q0,q1,q2]]


#def get_M2_face_fan():
#    """Comodità: restituisce i FaceFanData della faccia 0 dell'icosaedro
#    valutati con il parametro caratteristico del modello M2."""
#    return FaceFan(Polyhedron.ico.get_face_vertices(0), get_M2_parameter())


class MeshData:
    """Contenitore della mesh finale: vertici e facce pronti per l'export
    (es. verso Blender tramite from_pydata)."""

    def __init__(self):
        self.vertices = []  # lista di punti (tuple x, y, z)
        self.faces = []     # lista di facce, ciascuna come lista di indici dei vertici


def make_M2_mesh_data():
    """Assembla l'intera mesh del modello M2 percorrendo le 20 facce dell'icosaedro.

    Il parametro caratteristico viene calcolato una sola volta. Per ogni faccia si
    generano tre ventagli, uno per ciascuna rotazione ciclica dei suoi vertici (così
    ogni spigolo/angolo riceve la sua porzione di raccordo). Ogni FaceFan produce 7
    punti (p0,p1,p2,p3,q0,q1,q2, indici locali 0..6) da cui si ricavano 4 triangoli
    a raggiera attorno all'apice p3. Gli indici sono traslati di `k`, cioè il numero
    di vertici già accumulati, per riferirsi alla lista globale.
    """
    ico = Polyhedron.ico
    param = get_M2_parameter()

    mesh_data = MeshData()

    for face_index in range(len(ico.faces)):
        face = ico.get_face_vertices(face_index)
        # Tre orientamenti della faccia: ruota ciclicamente i vertici (p0,p1,p2).
        for vindex in range(3):
            pts = [face[(vindex+i)%3] for i in range(3)]
            fan = FaceFan(pts, param)
            k = len(mesh_data.vertices)  # offset di questo ventaglio nella lista globale
            mesh_data.vertices.extend(fan.points)
            # Quattro triangoli a ventaglio attorno all'apice p3 (indice locale 3):
            # collegano l'apice a p1, q1, q0, q2, p0 in sequenza.
            mesh_data.faces.extend([
                [k+3,k+1,k+5],
                [k+3,k+5,k+4],
                [k+3,k+4,k+6],
                [k+3,k+6,k+0]
            ])
    return mesh_data

def make_M2_fan_mesh_data(face_index, param):

    ico = Polyhedron.ico
    mesh_data = MeshData()

    face = ico.get_face_vertices(face_index)
    # Tre orientamenti della faccia: ruota ciclicamente i vertici (p0,p1,p2).
    for vindex in range(3):
        pts = [face[(vindex+i)%3] for i in range(3)]
        fan = FaceFan(pts, param)
        k = len(mesh_data.vertices)  # offset di questo ventaglio nella lista globale
        mesh_data.vertices.extend(fan.points)
        # Quattro triangoli a ventaglio attorno all'apice p3 (indice locale 3):
        # collegano l'apice a p1, q1, q0, q2, p0 in sequenza.
        mesh_data.faces.extend([
            [k+3,k+1,k+5],
            [k+3,k+5,k+4],
            [k+3,k+4,k+6],
            [k+3,k+6,k+0]
        ])
    return mesh_data

