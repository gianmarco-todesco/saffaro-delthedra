"""
Test d'uso / integrazione: riproducono in piccolo i pattern reali del progetto
(vedi 20-fans.py, prova2.py) usando SOLO geometry.py, senza Blender.

Servono sia come non regressione end-to-end sia come esempio minimo di "come si
usa la libreria".
"""

import unittest

from context import geometry

Vector = geometry.Vector


class TestPatternTrasformaMesh(unittest.TestCase):
    """Pattern di prova2.py: trasformare tutti i vertici di una mesh con una
    matrice ottenuta da una corrispondenza di triangoli."""

    def test_riflessione_di_una_lista_di_punti(self):
        # Una mesh e' una lista di punti (tuple), come MeshData.vertices.
        vertices = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)]

        # Matrice che scambia due dei punti di riferimento (riflessione nel piano).
        V = [Vector(p) for p in vertices]
        mat = geometry.matrix_from_triples([V[0], V[1], V[2]], [V[2], V[1], V[0]])

        # Applicazione a tutti i vertici, tornando a tuple per l'export.
        out = [geometry.apply_matrix(mat, Vector(p)).tup() for p in vertices]

        # I punti di riferimento finiscono dove previsto.
        for got, exp in zip(out[0], vertices[2]):
            self.assertAlmostEqual(got, exp, places=7)
        for got, exp in zip(out[2], vertices[0]):
            self.assertAlmostEqual(got, exp, places=7)


class TestPatternProiezioneSuFaccia(unittest.TestCase):
    """Pattern di 20-fans.py: prendere una faccia dell'icosaedro e costruire la
    matrice che vi mappa un triangolo modello."""

    def test_mappa_triangolo_su_ogni_faccia_dellicosaedro(self):
        ico = geometry.Polyhedron.ico

        # Triangolo modello nel piano z=0.
        modello = (Vector((0, 0, 0)), Vector((1, 0, 0)), Vector((0, 1, 0)))

        for idx in range(len(ico.faces)):
            target = tuple(ico.get_face_vertices(idx))  # 3 Vector sulla sfera
            mat = geometry.matrix_from_triples(modello, target)

            # Ogni vertice del modello deve cadere esattamente sul vertice
            # corrispondente della faccia.
            for m, t in zip(modello, target):
                mapped = geometry.apply_matrix(mat, m)
                for got, exp in zip(mapped.tup(), t.tup()):
                    self.assertAlmostEqual(got, exp, places=6)


class TestBaricentroConservato(unittest.TestCase):
    """Una trasformazione affine porta il baricentro dei vertici sorgente nel
    baricentro di quelli destinazione."""

    def test_baricentro(self):
        src = (Vector((0, 0, 0)), Vector((2, 0, 0)), Vector((0, 2, 0)))
        dst = (Vector((1, 1, 1)), Vector((3, 1, 1)), Vector((1, 3, 5)))
        mat = geometry.matrix_from_triples(src, dst)

        g_src = (src[0] + src[1] + src[2]) / 3
        g_dst = (dst[0] + dst[1] + dst[2]) / 3
        mapped = geometry.apply_matrix(mat, g_src)
        for got, exp in zip(mapped.tup(), g_dst.tup()):
            self.assertAlmostEqual(got, exp, places=6)


if __name__ == "__main__":
    unittest.main()
