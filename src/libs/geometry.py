"""
Utilità geometriche.
Questo file contiene classi e funzioni relative alla geometria 3D
Non ha dipendenze da Blender 

In particolare definisce Vector (vettore in R^3), Polyhedron (poliedro tramite vertici e facce) e 
MeshData (molto simile a Polyhedron, ma utilizzato principalmente per l'export verso Blender).
"""

import numpy as np


class Vector:
    """Vettore in R^3 con le operazioni algebriche e metriche essenziali.

    Le tre componenti sono conservate in un unico array numpy `a` di forma (3,):
    questa e' la sola rappresentazione interna, cosi' le operazioni delegano a
    numpy e non c'e' piu' conversione Vector<->array sparsa nel codice.
    Le proprieta' `x`, `y`, `z` restano disponibili per compatibilita'.
    """

    __slots__ = ("a",)  # niente __dict__: meno memoria per i tanti vertici

    def __init__(self, tup: "tuple[float, float, float] | list[float]" = (0, 0, 0)):
        # Inizializza le componenti da una tupla/lista/array (x, y, z), come float.
        self.a = np.asarray(tup, dtype=float).reshape(3)

    @property
    def x(self):
        return self.a[0]

    @property
    def y(self):
        return self.a[1]

    @property
    def z(self):
        return self.a[2]

    def __repr__(self):
        # Rappresentazione testuale compatta "(x,y,z)".
        return f"({self.x},{self.y},{self.z})"

    def __add__(self, other):
        # Somma componente per componente.
        return Vector(self.a + other.a)

    def __sub__(self, other):
        # Differenza componente per componente.
        return Vector(self.a - other.a)

    def __mul__(self, k):
        # Moltiplicazione per uno scalare k.
        return Vector(self.a * k)

    def __rmul__(self, k):
        # Permette anche `k * v`, oltre a `v * k`.
        return Vector(self.a * k)

    def __truediv__(self, k):
        # Divisione per uno scalare k.
        return Vector(self.a / k)

    def length(self):
        # Norma euclidea (modulo) del vettore.
        return float(np.sqrt(self.a @ self.a))

    def length2(self):
        # Norma al quadrato: evita la radice quando serve solo confrontare distanze.
        return float(self.a @ self.a)

    def dist(self, other):
        # Distanza euclidea tra questo punto e un altro.
        return (self - other).length()

    def dot(self, other):
        # Prodotto scalare tra due vettori.
        return float(self.a @ other.a)

    def normalized(self):
        # Restituisce il versore (vettore di modulo 1) con la stessa direzione.
        n = np.sqrt(self.a @ self.a)
        if n == 0.0:
            raise ValueError("normalized(): il vettore nullo non ha direzione")
        return Vector(self.a / n)

    def cross(self, other):
        # Prodotto vettoriale: restituisce un vettore ortogonale a self e other.
        return Vector(np.cross(self.a, other.a))

    def almost_equal(self, other, tol=1e-9):
        # Uguaglianza approssimata, comoda per test e confronti robusti al float.
        return bool(np.allclose(self.a, other.a, atol=tol, rtol=0.0))

    def tup(self):
        # Converte il vettore in una tupla (x, y, z), utile per l'export dei punti.
        return (float(self.a[0]), float(self.a[1]), float(self.a[2]))


def apply_matrix(m, v:Vector):
    """Applica una matrice 4x4 (coordinate omogenee) al vettore v e restituisce
    il Vector trasformato.

    Il punto viene esteso a (x, y, z, 1), moltiplicato per m e riportato in R^3
    dividendo per la componente omogenea w (per trasformazioni affini w vale 1,
    ma la divisione gestisce correttamente anche matrici proiettive).

    La matrice può essere ad es. [[1,0,0,0],[0,1,0,0],[0,0,1,0],[tx,ty,tz,1]] per una traslazione di (tx, ty, tz).
    Il vettore v deve essere un'istanza di Vector.
    """
    m = np.asarray(m, dtype=float)
    p = m @ np.append(v.a, 1.0)
    return Vector(p[:3] / p[3])


def transform_points(m, points):
    """Applica una matrice 4x4 a molti punti in una sola operazione.

    E' la versione "in blocco" di apply_matrix, pensata per i loop caldi che
    trasformano tutti i vertici di una mesh (vedi 20-fans.py, prova2.py): invece
    di iterare in Python punto per punto avvolgendo ogni vertice in un Vector, si
    fa una singola moltiplicazione matriciale su tutti i punti.

    `points` puo' essere un array (N, 3) oppure una lista di tuple/Vector;
    restituisce un array numpy (N, 3). Per riportarlo a lista di tuple (es. per
    MeshData / Blender) usare `.tolist()`.
    """
    m = np.asarray(m, dtype=float)
    P = np.asarray([p.tup() if isinstance(p, Vector) else p for p in points], dtype=float)
    P = P.reshape(-1, 3)
    H = np.c_[P, np.ones(len(P))]        # coordinate omogenee (N, 4)
    Q = H @ m.T                          # (N, 4)
    return Q[:, :3] / Q[:, 3:4]          # divisione per la componente omogenea w


def matrix_from_triples(src:tuple[Vector, Vector, Vector], dst:tuple[Vector, Vector, Vector]):
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
        if n.length2() == 0.0:
            # Punti coincidenti o allineati: la normale e' nulla e il frame
            # sarebbe singolare (np.linalg.inv fallirebbe in modo oscuro).
            raise ValueError("matrix_from_triples(): tripla degenere (punti collineari)")
        return np.array([
            [u.x, v.x, n.x, a.x],
            [u.y, v.y, n.y, a.y],
            [u.z, v.z, n.z, a.z],
            [0.0, 0.0, 0.0, 1.0],
        ])

    return frame(dst) @ np.linalg.inv(frame(src))


class Polyhedron:
    """Poliedro descritto da una lista di vertici e dalle facce (indici dei vertici)."""

    def __init__(self, vertices:list[Vector], faces:list[tuple[int, ...]]):
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
    # Clamp a [-1, 1]: piccoli errori float potrebbero portare cosA appena fuori
    # dal dominio di arccos e produrre nan.
    cosA = np.clip(cosA, -1.0, 1.0)
    return np.arccos(cosA)


class MeshData:
    """Contenitore della mesh finale: vertici e facce pronti per l'export
    (es. verso Blender tramite from_pydata)."""

    def __init__(self):
        self.vertices = []  # lista di punti (tuple x, y, z)
        self.faces = []     # lista di facce, ciascuna come lista di indici dei vertici

    def append(self, other):
        """Fonde `other` in questa mesh: aggiunge i suoi vertici e le sue facce.

        I vertici si accodano; le facce vanno invece rimappate, perche' gli
        indici di `other` sono relativi alla sua lista di vertici e vanno traslati
        del numero di vertici gia' presenti in self. Modifica self (che viene
        restituito per comodita' di concatenazione) e non altera `other`.
        """
        offset = len(self.vertices)
        self.vertices.extend(other.vertices)
        self.faces.extend([i + offset for i in face] for face in other.faces)
        return self


# =============================================================================
# POLIEDRI CONVESSI: PIANI DELLE FACCE E CONTENIMENTO
# =============================================================================

def face_planes(poly):
    """Per ogni faccia di un poliedro convesso centrato nell'origine: normale
    uscente (versore) e distanza del suo piano dall'origine. Restituisce due
    array numpy (F, 3) e (F,).

    Il verso della normale viene rimesso a posto confrontandolo col baricentro
    della faccia, invece di fidarsi dell'ordine dei vertici: la funzione serve a
    misurare un contenimento, e una sola faccia girata al contrario darebbe una
    scala sbagliata senza che nulla lo segnali.
    """
    verts = np.asarray([v.tup() for v in poly.vertices], dtype=float)
    normals, dists = [], []
    for face in poly.faces:
        p = verts[list(face)]
        n = np.cross(p[1] - p[0], p[2] - p[0])
        n = n / np.linalg.norm(n)
        if n @ p.mean(axis=0) < 0.0:
            n = -n
        normals.append(n)
        dists.append(float(n @ p[0]))
    return np.asarray(normals), np.asarray(dists)


def enclosing_scale(points, poly):
    """Il piu' piccolo fattore k per cui k*poly contiene tutti i `points`.

    `poly` dev'essere convesso e centrato nell'origine: e' l'intersezione dei
    semispazi n_i . x <= d_i, e scalarlo di k scala i d_i. Il k minimo e'
    percio' il massimo, su tutti i punti e tutte le facce, di (n_i . p) / d_i.
    Si passa dai piani e non dal raggio massimo dei punti perche' il risultato
    resti giusto qualunque sia la faccia (o lo spigolo) che tocca per prima.
    """
    P = np.asarray(points, dtype=float).reshape(-1, 3)
    normals, dists = face_planes(poly)
    return float(((P @ normals.T) / dists).max())


def polyhedron_mesh(poly, scale=1.0):
    """MeshData del poliedro, scalato di `scale`. Le facce si riportano tali e
    quali, quindi l'orientamento e' quello di `poly`."""
    md = MeshData()
    md.vertices = [(v * scale).tup() for v in poly.vertices]
    md.faces = [list(f) for f in poly.faces]
    return md
