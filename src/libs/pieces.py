"""
pieces.py -- M come 240 pezzi rigidi: il triangolo canonico, la posa di ognuno
dei 240 triangoli di M, e la griglia in cui si allineano per essere contati.

Puro numpy, come `geometry` ed `extended_face`: niente bpy, quindi e' coperto
dai test. La conversione in mathutils (location + quaternione) sta in
`bl_anim`, che e' il suo lato Blender.

I 240 triangoli di M sono tutti equilateri di lato 1, quindi la matrice che
porta il triangolo canonico su ciascuno di essi e' una rotazione pura piu' una
traslazione: e' per questo che in Blender basta *una* mesh di 3 vertici,
istanziata 240 volte.
"""

import math

import numpy as np

import geometry
import extended_face
from geometry import Vector


# =============================================================================
# IL TRIANGOLO CANONICO
# =============================================================================
#
# E' il triangolo equilatero di lato 1 che sta sul piano XZ (y = 0) col
# baricentro nell'origine e il vertice 0 in alto; i vertici 1 e 2 seguono in
# senso antiorario guardando dalla vista Fronte (da -Y).
#
# Il piano XZ e la normale -Y non sono una scelta estetica: un pezzo con
# rotazione identita' e' gia' coricato su un piano rivolto verso una camera che
# guarda lungo +Y, ed e' cosi' che lo si mette nella griglia.

CIRCUMRADIUS = 1.0 / math.sqrt(3.0)    # circonraggio di un equilatero di lato 1

CANONICAL_TRIANGLE = tuple(
    Vector((
        CIRCUMRADIUS * math.cos(math.radians(90.0 + 120.0 * k)),
        0.0,
        CIRCUMRADIUS * math.sin(math.radians(90.0 + 120.0 * k)),
    ))
    for k in range(3)
)

# Con questa numerazione dei vertici la normale (v1-v0)x(v2-v0) e' -Y.
CANONICAL_NORMAL = (0.0, -1.0, 0.0)


# =============================================================================
# I 240 PEZZI
# =============================================================================

class Piece:
    """Un triangolo di M, come trasformazione rigida del triangolo canonico.

    index  : 0..239, ordine di costruzione (= fan * 12 + slot)
    fan    : 0..19, quale faccia estesa
    slot   : 0..11, quale triangolo dentro il ventaglio (0..3 sul primo lato
             del triangolo di base, 4..7 sul secondo, 8..11 sul terzo)
    matrix : numpy 4x4, porta CANONICAL_TRIANGLE sul triangolo in M; il
             vertice k canonico va sul vertice k della faccia di M, e il
             vertice 0 e' sempre l'apice del ventaglio
    center : numpy (3,), baricentro in M
    normal : numpy (3,), normale uscente in M, versore
    """

    __slots__ = ("index", "fan", "slot", "matrix", "center", "normal")

    def __init__(self, index, fan, slot, matrix, center, normal):
        self.index = index
        self.fan = fan
        self.slot = slot
        self.matrix = matrix
        self.center = center
        self.normal = normal

    def __repr__(self):
        return f"<Piece {self.index:03d} fan={self.fan} slot={self.slot}>"


def m_pieces(md=None):
    """I 240 pezzi di M, nell'ordine delle facce di `md` (default: make_M()).

    Se la trasformazione di un pezzo non e' rigida la mesh non e' fatta di
    triangoli equilateri unitari, e l'intera impalcatura "un solo triangolo
    istanziato 240 volte" non sta in piedi: meglio accorgersene subito. Il
    controllo si fa qui, in doppia precisione: mathutils tiene i numeri in
    singola, e una soglia stretta li' scatterebbe a vuoto.
    """
    if md is None:
        md = extended_face.make_M()
    verts = np.asarray(md.vertices, dtype=float)

    pieces = []
    for index, face in enumerate(md.faces):
        target = tuple(Vector(verts[i]) for i in face)
        mat = geometry.matrix_from_triples(CANONICAL_TRIANGLE, target)

        scale = np.linalg.norm(mat[:3, :3], axis=0)
        assert np.abs(scale - 1.0).max() < 1e-9, \
            f"triangolo {index}: la trasformazione non e' rigida (scala {scale})"

        p = verts[list(face)]
        normal = np.cross(p[1] - p[0], p[2] - p[0])
        pieces.append(Piece(
            index=index,
            fan=index // extended_face.N_TRIANGLES,
            slot=index % extended_face.N_TRIANGLES,
            matrix=mat,
            center=p.mean(axis=0),
            normal=normal / np.linalg.norm(normal),
        ))
    return pieces


# =============================================================================
# LA GRIGLIA
# =============================================================================

class Grid:
    """Una griglia rettangolare di gruppi, sul piano XZ, centrata nell'origine.

    Le unita' sono lati di triangolo. Ogni gruppo e' un rettangolo di
    cols_per_group x rows_per_group celle a passo `spacing`; fra un gruppo e
    l'altro c'e' in piu' `group_gap`. La riga 0 sta in alto.

    Il raggruppamento serve a contare a colpo d'occhio: con un gruppo per
    faccia estesa (20 gruppi da 12) chi guarda conta 20 volte 12, non 240.
    """

    def __init__(self, group_cols, group_rows, cols_per_group, rows_per_group,
                 spacing=1.2, group_gap=0.6):
        self.group_cols = group_cols
        self.group_rows = group_rows
        self.cols_per_group = cols_per_group
        self.rows_per_group = rows_per_group
        self.spacing = spacing
        self.group_gap = group_gap

    @property
    def n_groups(self):
        return self.group_cols * self.group_rows

    @property
    def group_size(self):
        return self.cols_per_group * self.rows_per_group

    def _span(self):
        """Distanza fra i centri delle celle estreme, (x, z)."""
        cols = self.group_cols * self.cols_per_group
        rows = self.group_rows * self.rows_per_group
        return ((cols - 1) * self.spacing + (self.group_cols - 1) * self.group_gap,
                (rows - 1) * self.spacing + (self.group_rows - 1) * self.group_gap)

    def extent(self):
        """Ingombro della griglia piena di triangoli canonici, (larghezza,
        altezza): lo span dei centri piu' un triangolo (lato 1 in orizzontale,
        altezza sqrt(3)/2 in verticale)."""
        sx, sz = self._span()
        return sx + 1.0, sz + math.sqrt(3.0) / 2.0

    def cell(self, group, cell):
        """Centro (x, z) della cella `cell` del gruppo `group`."""
        if not (0 <= group < self.n_groups and 0 <= cell < self.group_size):
            raise IndexError(f"cella ({group}, {cell}) fuori da una griglia di "
                             f"{self.n_groups} gruppi da {self.group_size}")
        gcol, grow = group % self.group_cols, group // self.group_cols
        ccol, crow = cell % self.cols_per_group, cell // self.cols_per_group
        col = gcol * self.cols_per_group + ccol
        row = grow * self.rows_per_group + crow
        sx, sz = self._span()
        x = col * self.spacing + gcol * self.group_gap
        z = row * self.spacing + grow * self.group_gap
        return x - sx / 2.0, sz / 2.0 - z
