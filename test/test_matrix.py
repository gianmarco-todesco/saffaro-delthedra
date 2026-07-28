"""
Test di non regressione per apply_matrix e matrix_from_triples.

Mostrano anche i due usi tipici: trasformare un punto con una matrice 4x4 e
costruire la matrice che porta un triangolo su un altro (triangolo->triangolo).
"""

import unittest

import numpy as np

from context import geometry

Vector = geometry.Vector
apply_matrix = geometry.apply_matrix
matrix_from_triples = geometry.matrix_from_triples


def assert_vector_almost_equal(test, v, expected, places=9):
    for got, exp in zip(v.tup(), expected):
        test.assertAlmostEqual(got, exp, places=places)


class TestApplyMatrix(unittest.TestCase):
    def test_identita(self):
        v = Vector((1, 2, 3))
        assert_vector_almost_equal(self, apply_matrix(np.eye(4), v), (1, 2, 3))

    def test_traslazione(self):
        # Convenzione della libreria: la traslazione sta nell'ultima COLONNA
        # (p = M @ [x, y, z, 1]).
        m = np.array([
            [1, 0, 0, 10],
            [0, 1, 0, 20],
            [0, 0, 1, 30],
            [0, 0, 0, 1],
        ], dtype=float)
        assert_vector_almost_equal(self, apply_matrix(m, Vector((1, 2, 3))), (11, 22, 33))

    def test_scala(self):
        m = np.diag([2.0, 3.0, 4.0, 1.0])
        assert_vector_almost_equal(self, apply_matrix(m, Vector((1, 1, 1))), (2, 3, 4))

    def test_divisione_prospettica_per_w(self):
        # w != 1: il risultato viene diviso per la componente omogenea.
        m = np.eye(4)
        m[3, 3] = 2.0  # w = 2
        assert_vector_almost_equal(self, apply_matrix(m, Vector((2, 4, 6))), (1, 2, 3))

    def test_accetta_liste_python(self):
        # apply_matrix passa per np.asarray: una lista di liste va bene.
        m = [[1, 0, 0, 1], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
        assert_vector_almost_equal(self, apply_matrix(m, Vector((0, 0, 0))), (1, 0, 0))


class TestMatrixFromTriples(unittest.TestCase):
    def setUp(self):
        self.src = (Vector((0, 0, 0)), Vector((1, 0, 0)), Vector((0, 1, 0)))

    def test_mappa_esattamente_i_tre_punti(self):
        dst = (Vector((2, 1, 0)), Vector((2, 2, 0)), Vector((1, 1, 0)))
        m = matrix_from_triples(self.src, dst)
        for s, d in zip(self.src, dst):
            assert_vector_almost_equal(self, apply_matrix(m, s), d.tup(), places=7)

    def test_src_uguale_dst_da_identita_sui_punti(self):
        m = matrix_from_triples(self.src, self.src)
        for s in self.src:
            assert_vector_almost_equal(self, apply_matrix(m, s), s.tup(), places=7)

    def test_composizione_e_inversa(self):
        # La matrice da src a dst, composta con quella da dst a src, riporta
        # ogni punto della tripla su se stesso.
        dst = (Vector((5, 0, 1)), Vector((5, 2, 1)), Vector((4, 0, 3)))
        m = matrix_from_triples(self.src, dst)
        m_inv = matrix_from_triples(dst, self.src)
        back = m_inv @ m
        for s in self.src:
            assert_vector_almost_equal(self, apply_matrix(back, s), s.tup(), places=7)

    def test_conserva_la_normale_del_triangolo(self):
        # Lo scambio di due vertici (riflessione) e' un caso usato in prova2.py:
        # verifichiamo che i tre punti finiscano dove previsto.
        dst = (self.src[2], self.src[1], self.src[0])  # inverte 0 <-> 2
        m = matrix_from_triples(self.src, dst)
        assert_vector_almost_equal(self, apply_matrix(m, self.src[0]), self.src[2].tup(), places=7)
        assert_vector_almost_equal(self, apply_matrix(m, self.src[2]), self.src[0].tup(), places=7)

    def test_tripla_collineare_solleva(self):
        # Tre punti allineati -> normale nulla -> frame singolare: errore esplicito.
        collineari = (Vector((0, 0, 0)), Vector((1, 0, 0)), Vector((2, 0, 0)))
        with self.assertRaises(ValueError):
            matrix_from_triples(self.src, collineari)


class TestTransformPoints(unittest.TestCase):
    """Versione batch di apply_matrix (Proposta B)."""

    def test_coerente_con_apply_matrix(self):
        m = np.array([
            [2, 0, 0, 1],
            [0, 3, 0, 2],
            [0, 0, 4, 3],
            [0, 0, 0, 1],
        ], dtype=float)
        punti = [(1, 1, 1), (0, 0, 0), (-1, 2, 5)]

        batch = geometry.transform_points(m, punti)
        for p, riga in zip(punti, batch):
            atteso = apply_matrix(m, Vector(p)).tup()
            for got, exp in zip(riga, atteso):
                self.assertAlmostEqual(got, exp, places=9)

    def test_ritorna_array_Nx3(self):
        out = geometry.transform_points(np.eye(4), [(1, 2, 3), (4, 5, 6)])
        self.assertEqual(out.shape, (2, 3))

    def test_accetta_vector_e_divisione_prospettica(self):
        m = np.eye(4)
        m[3, 3] = 2.0  # w = 2
        out = geometry.transform_points(m, [Vector((2, 4, 6))])
        for got, exp in zip(out[0], (1, 2, 3)):
            self.assertAlmostEqual(got, exp, places=9)


if __name__ == "__main__":
    unittest.main()
