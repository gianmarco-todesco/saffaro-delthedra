"""
Test di non regressione per pieces.py (M come 240 pezzi rigidi, e la griglia)
e per le funzioni di contenimento di geometry.py usate per l'icosaedro-gabbia.
"""

import math
import unittest

import numpy as np

from context import geometry  # noqa: F401  (sistema il sys.path)
import extended_face as ef
import pieces


class TestTriangoloCanonico(unittest.TestCase):
    def test_equilatero_unitario_centrato(self):
        P = np.array([v.tup() for v in pieces.CANONICAL_TRIANGLE])
        for a, b in [(0, 1), (1, 2), (2, 0)]:
            self.assertAlmostEqual(np.linalg.norm(P[a] - P[b]), 1.0, places=12)
        np.testing.assert_allclose(P.mean(axis=0), 0.0, atol=1e-12)
        np.testing.assert_allclose(P[:, 1], 0.0, atol=1e-12)    # sul piano XZ
        self.assertEqual(int(np.argmax(P[:, 2])), 0)            # vertice 0 in alto

    def test_normale(self):
        P = np.array([v.tup() for v in pieces.CANONICAL_TRIANGLE])
        n = np.cross(P[1] - P[0], P[2] - P[0])
        np.testing.assert_allclose(n / np.linalg.norm(n), pieces.CANONICAL_NORMAL,
                                   atol=1e-12)


class TestPezziDiM(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.md = ef.make_M()
        cls.pieces = pieces.m_pieces(cls.md)

    def test_conteggi(self):
        self.assertEqual(len(self.pieces), 240)
        self.assertEqual(sorted({p.fan for p in self.pieces}), list(range(20)))
        self.assertEqual(sorted({p.slot for p in self.pieces}), list(range(12)))

    def test_la_matrice_porta_il_canonico_sulla_faccia(self):
        C = np.array([v.tup() for v in pieces.CANONICAL_TRIANGLE])
        V = np.asarray(self.md.vertices, dtype=float)
        for p in self.pieces:
            got = geometry.transform_points(p.matrix, C)
            np.testing.assert_allclose(got, V[self.md.faces[p.index]], atol=1e-9)

    def test_rotazione_propria(self):
        # determinante +1: nessuna riflessione, quindi un quaternione basta
        for p in self.pieces:
            self.assertAlmostEqual(np.linalg.det(p.matrix[:3, :3]), 1.0, places=9)

    def test_normali_uscenti(self):
        for p in self.pieces:
            self.assertAlmostEqual(np.linalg.norm(p.normal), 1.0, places=12)
            self.assertGreater(p.normal @ p.center, 0.0)


class TestGriglia(unittest.TestCase):
    def test_celle_distinte_e_centrate(self):
        g = pieces.Grid(5, 4, 4, 3)
        cells = [g.cell(gr, c) for gr in range(g.n_groups) for c in range(g.group_size)]
        self.assertEqual(len(cells), 240)
        self.assertEqual(len({(round(x, 9), round(z, 9)) for x, z in cells}), 240)
        np.testing.assert_allclose(np.mean(cells, axis=0), 0.0, atol=1e-12)

    def test_riga_zero_in_alto(self):
        g = pieces.Grid(5, 4, 4, 3)
        self.assertGreater(g.cell(0, 0)[1], g.cell(g.n_groups - 1, g.group_size - 1)[1])
        self.assertLess(g.cell(0, 0)[0], g.cell(0, 1)[0])

    def test_ingombro(self):
        g = pieces.Grid(5, 4, 4, 3, spacing=1.2, group_gap=0.6)
        w, h = g.extent()
        self.assertAlmostEqual(w, 19 * 1.2 + 4 * 0.6 + 1.0)
        self.assertAlmostEqual(h, 11 * 1.2 + 3 * 0.6 + math.sqrt(3) / 2)

    def test_fuori_griglia(self):
        g = pieces.Grid(5, 4, 4, 3)
        with self.assertRaises(IndexError):
            g.cell(20, 0)
        with self.assertRaises(IndexError):
            g.cell(0, 12)


class TestGabbia(unittest.TestCase):
    def test_piani_icosaedro(self):
        normals, dists = geometry.face_planes(geometry.Polyhedron.ico)
        self.assertEqual(normals.shape, (20, 3))
        # icosaedro regolare di circonraggio 1: inraggio uguale per tutte le facce
        np.testing.assert_allclose(dists, dists[0], atol=1e-12)
        self.assertTrue((dists > 0).all())

    def test_contenimento_dei_propri_vertici(self):
        ico = geometry.Polyhedron.ico
        pts = [v.tup() for v in ico.vertices]
        self.assertAlmostEqual(geometry.enclosing_scale(pts, ico), 1.0, places=12)
        self.assertAlmostEqual(
            geometry.enclosing_scale(np.asarray(pts) * 2.5, ico), 2.5, places=12)

    def test_core_scale_mette_l_icosaedro_sui_vertici_di_M(self):
        # a scala core_scale() i 12 vertici dell'icosaedro sono vertici di M
        V = np.asarray(ef.make_M().vertices, dtype=float)
        k = ef.core_scale()
        for v in geometry.Polyhedron.ico.vertices:
            p = np.asarray(v.tup()) * k
            self.assertLess(np.linalg.norm(V - p, axis=1).min(), 1e-9)

    def test_gabbia_di_M_piu_grande_dell_anima(self):
        V = ef.make_M().vertices
        self.assertGreater(geometry.enclosing_scale(V, geometry.Polyhedron.ico),
                           ef.core_scale())


if __name__ == "__main__":
    unittest.main()
