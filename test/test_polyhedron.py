"""
Test di non regressione per Polyhedron, make_icosahedron e Polyhedron.ico.
"""

import unittest

from context import geometry

Vector = geometry.Vector
Polyhedron = geometry.Polyhedron


class TestPolyhedron(unittest.TestCase):
    def test_get_face_vertices_risolve_gli_indici(self):
        verts = [Vector((0, 0, 0)), Vector((1, 0, 0)), Vector((0, 1, 0))]
        poly = Polyhedron(verts, [(0, 1, 2)])
        got = poly.get_face_vertices(0)
        self.assertEqual([v.tup() for v in got], [(0, 0, 0), (1, 0, 0), (0, 1, 0)])

    def test_get_face_vertices_indice_fuori_range(self):
        poly = Polyhedron([Vector((0, 0, 0))], [])
        with self.assertRaises(AssertionError):
            poly.get_face_vertices(0)


class TestIcosaedro(unittest.TestCase):
    def setUp(self):
        self.ico = geometry.make_icosahedron()

    def test_conteggi(self):
        self.assertEqual(len(self.ico.vertices), 12)
        self.assertEqual(len(self.ico.faces), 20)

    def test_vertici_sulla_sfera_unitaria(self):
        for v in self.ico.vertices:
            self.assertAlmostEqual(v.length(), 1.0, places=9)

    def test_facce_tutte_triangolari(self):
        for f in self.ico.faces:
            self.assertEqual(len(f), 3)

    def test_indici_delle_facce_validi(self):
        n = len(self.ico.vertices)
        for f in self.ico.faces:
            for idx in f:
                self.assertTrue(0 <= idx < n)

    def test_formula_di_eulero(self):
        # V - E + F = 2. Gli spigoli si contano dalle facce (ogni spigolo e'
        # condiviso da due facce, quindi si divide per 2).
        V = len(self.ico.vertices)
        F = len(self.ico.faces)
        edges = set()
        for f in self.ico.faces:
            for i in range(len(f)):
                a, b = f[i], f[(i + 1) % len(f)]
                edges.add((min(a, b), max(a, b)))
        E = len(edges)
        self.assertEqual(E, 30)
        self.assertEqual(V - E + F, 2)

    def test_ogni_spigolo_condiviso_da_due_facce(self):
        # Superficie chiusa e ben orientata: ogni spigolo non orientato compare
        # in esattamente due facce.
        from collections import Counter
        conta = Counter()
        for f in self.ico.faces:
            for i in range(len(f)):
                a, b = f[i], f[(i + 1) % len(f)]
                conta[(min(a, b), max(a, b))] += 1
        self.assertTrue(all(c == 2 for c in conta.values()))

    def test_normali_uscenti(self):
        # Per un poliedro convesso centrato nell'origine, la normale di ogni
        # faccia (ordine antiorario) punta nello stesso verso del baricentro.
        for f in self.ico.faces:
            a, b, c = [self.ico.vertices[i] for i in f]
            n = (b - a).cross(c - a)
            centro = (a + b + c) / 3
            dot = n.x * centro.x + n.y * centro.y + n.z * centro.z
            self.assertGreater(dot, 0.0)

    def test_istanza_condivisa_ico(self):
        self.assertIsInstance(Polyhedron.ico, Polyhedron)
        self.assertEqual(len(Polyhedron.ico.vertices), 12)
        self.assertEqual(len(Polyhedron.ico.faces), 20)


if __name__ == "__main__":
    unittest.main()
