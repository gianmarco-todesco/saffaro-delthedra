"""
Test di non regressione per la classe Vector.

Doppio scopo: bloccano il comportamento attuale (utili in caso di refactoring,
ad es. se un giorno Vector diventasse basato su numpy) e mostrano come si usano
i vettori della libreria.
"""

import math
import unittest

from context import geometry

Vector = geometry.Vector


class TestVectorCostruzione(unittest.TestCase):
    def test_default_e_origine(self):
        v = Vector()
        self.assertEqual((v.x, v.y, v.z), (0, 0, 0))

    def test_da_tupla_e_da_lista(self):
        # Vector accetta indifferentemente tuple o liste di 3 elementi.
        self.assertEqual(Vector((1, 2, 3)).tup(), (1, 2, 3))
        self.assertEqual(Vector([4, 5, 6]).tup(), (4, 5, 6))

    def test_repr(self):
        # Lo storage e' numpy (float), quindi le componenti sono mostrate come float.
        self.assertEqual(repr(Vector((1, 2, 3))), "(1.0,2.0,3.0)")

    def test_tup_ritorna_tupla(self):
        t = Vector((1, 2, 3)).tup()
        self.assertIsInstance(t, tuple)
        self.assertEqual(t, (1, 2, 3))


class TestVectorAlgebra(unittest.TestCase):
    def setUp(self):
        self.a = Vector((1, 2, 3))
        self.b = Vector((4, 5, 6))

    def test_somma(self):
        self.assertEqual((self.a + self.b).tup(), (5, 7, 9))

    def test_differenza(self):
        self.assertEqual((self.b - self.a).tup(), (3, 3, 3))

    def test_prodotto_per_scalare(self):
        self.assertEqual((self.a * 2).tup(), (2, 4, 6))

    def test_divisione_per_scalare(self):
        self.assertEqual((Vector((2, 4, 6)) / 2).tup(), (1, 2, 3))

    def test_le_operazioni_non_mutano_gli_operandi(self):
        # Le operazioni restituiscono nuovi Vector senza toccare quelli di partenza.
        _ = self.a + self.b
        self.assertEqual(self.a.tup(), (1, 2, 3))
        self.assertEqual(self.b.tup(), (4, 5, 6))


class TestVectorMetriche(unittest.TestCase):
    def test_length(self):
        self.assertAlmostEqual(Vector((3, 4, 0)).length(), 5.0)

    def test_length2_evita_la_radice(self):
        self.assertAlmostEqual(Vector((3, 4, 0)).length2(), 25.0)

    def test_dist(self):
        self.assertAlmostEqual(Vector((0, 0, 0)).dist(Vector((3, 4, 0))), 5.0)

    def test_normalized_ha_modulo_unitario(self):
        n = Vector((0, 0, 5)).normalized()
        self.assertAlmostEqual(n.length(), 1.0)
        self.assertEqual(n.tup(), (0.0, 0.0, 1.0))

    def test_normalized_conserva_la_direzione(self):
        v = Vector((1, 2, 2))  # modulo 3
        n = v.normalized()
        for comp_v, comp_n in zip(v.tup(), n.tup()):
            self.assertAlmostEqual(comp_n, comp_v / 3.0)


class TestVectorCross(unittest.TestCase):
    def test_cross_versori_base(self):
        x = Vector((1, 0, 0))
        y = Vector((0, 1, 0))
        self.assertEqual(x.cross(y).tup(), (0, 0, 1))

    def test_cross_e_anticommutativo(self):
        a = Vector((1, 2, 3))
        b = Vector((4, 5, 6))
        self.assertEqual(a.cross(b).tup(), tuple(-c for c in b.cross(a).tup()))

    def test_cross_ortogonale_agli_operandi(self):
        a = Vector((1, 2, 3))
        b = Vector((-2, 0, 5))
        n = a.cross(b)
        # Il prodotto scalare con entrambi deve essere ~0.
        self.assertAlmostEqual(n.x * a.x + n.y * a.y + n.z * a.z, 0.0)
        self.assertAlmostEqual(n.x * b.x + n.y * b.y + n.z * b.z, 0.0)

    def test_cross_modulo_uguale_area_parallelogramma(self):
        a = Vector((1, 0, 0))
        b = Vector((math.cos(math.radians(60)), math.sin(math.radians(60)), 0))
        # |a x b| = |a||b| sin(theta) = 1*1*sin(60)
        self.assertAlmostEqual(a.cross(b).length(), math.sin(math.radians(60)))


class TestVectorAggiunte(unittest.TestCase):
    """Nuove funzionalita' additive introdotte col refactoring."""

    def test_dot(self):
        self.assertAlmostEqual(Vector((1, 2, 3)).dot(Vector((4, 5, 6))), 32.0)

    def test_dot_ortogonali_e_zero(self):
        self.assertAlmostEqual(Vector((1, 0, 0)).dot(Vector((0, 1, 0))), 0.0)

    def test_rmul_come_mul(self):
        # k * v deve dare lo stesso risultato di v * k.
        v = Vector((1, 2, 3))
        self.assertEqual((3 * v).tup(), (v * 3).tup())

    def test_almost_equal(self):
        self.assertTrue(Vector((1, 2, 3)).almost_equal(Vector((1, 2, 3 + 1e-12))))
        self.assertFalse(Vector((1, 2, 3)).almost_equal(Vector((1, 2, 3.1))))

    def test_normalized_su_vettore_nullo_solleva(self):
        with self.assertRaises(ValueError):
            Vector((0, 0, 0)).normalized()

    def test_accetta_array_numpy(self):
        # Lo storage e' numpy: costruire da un array deve funzionare.
        import numpy as np
        v = Vector(np.array([1.0, 2.0, 3.0]))
        self.assertEqual(v.tup(), (1.0, 2.0, 3.0))


if __name__ == "__main__":
    unittest.main()
