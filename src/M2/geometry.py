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
  - apply_matrix          : applica una matrice 4x4 a un Vector (coord. omogenee).
  - matrix_from_triples   : matrice che mappa una tripla di punti in un'altra.
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


def apply_matrix(m, v):
    """Applica una matrice 4x4 (coordinate omogenee) al vettore v e restituisce
    il Vector trasformato.

    Il punto viene esteso a (x, y, z, 1), moltiplicato per m e riportato in R^3
    dividendo per la componente omogenea w (per trasformazioni affini w vale 1,
    ma la divisione gestisce correttamente anche matrici proiettive).
    """
    m = np.asarray(m, dtype=float)
    p = m @ np.array([v.x, v.y, v.z, 1.0])
    w = p[3]
    return Vector((p[0]/w, p[1]/w, p[2]/w))


def matrix_from_triples(src, dst):
    """Restituisce la matrice 4x4 che mappa la tripla di punti src nella tripla dst.

    Tre corrispondenze di punti non bastano a determinare un'affinità generica
    (9 vincoli contro 12 gradi di libertà), quindi si adotta l'approccio classico
    triangolo->triangolo: da ciascuna tripla (a, b, c) si costruisce un sistema di
    riferimento locale con origine in a e assi (b-a), (c-a) e la loro normale
    (b-a)x(c-a). La matrice F che porta la base canonica su questo riferimento ha
    per colonne i tre assi e per quarta colonna l'origine; componendo
    F_dst * F_src^-1 si ottiene la trasformazione cercata.
    """
    def frame(triple):
        # Matrice 4x4 riferimento->mondo: mappa (0,0,0)->a, (1,0,0)->b, (0,1,0)->c.
        a, b, c = triple
        u = b - a          # primo asse (spigolo a->b)
        v = c - a          # secondo asse (spigolo a->c)
        n = u.cross(v)     # terzo asse: normale al piano della tripla
        return np.array([
            [u.x, v.x, n.x, a.x],
            [u.y, v.y, n.y, a.y],
            [u.z, v.z, n.z, a.z],
            [0.0, 0.0, 0.0, 1.0],
        ])

    return frame(dst) @ np.linalg.inv(frame(src))


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


class MeshData:
    """Contenitore della mesh finale: vertici e facce pronti per l'export
    (es. verso Blender tramite from_pydata)."""

    def __init__(self):
        self.vertices = []  # lista di punti (tuple x, y, z)
        self.faces = []     # lista di facce, ciascuna come lista di indici dei vertici

