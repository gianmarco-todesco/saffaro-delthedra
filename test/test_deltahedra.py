"""
Test per deltahedra: il composto di tre tetraedri, la saldatura dei vertici
degli OBJ, la platea e la sua inquadratura.
"""

import itertools
import os
import tempfile
import unittest

import numpy as np

import context  # noqa: F401  (sistema il sys.path)
import deltahedra


class TestChain(unittest.TestCase):
    def setUp(self):
        self.V, self.faces = deltahedra.tetrahedron_chain()

    def test_spigoli_unitari(self):
        for f in self.faces:
            for a, b in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])):
                self.assertAlmostEqual(np.linalg.norm(self.V[a] - self.V[b]), 1.0, places=12)

    def test_tre_tipi_di_vertice(self):
        deg = deltahedra.vertex_degrees(len(self.V), self.faces)
        self.assertEqual(sorted(deg), [3, 3, 4, 4, 5, 5])
        self.assertEqual(len(self.faces), 8)

    def test_normali_verso_l_esterno(self):
        # volume positivo, e ogni spigolo percorso una volta per verso
        vol = sum(np.dot(self.V[f[0]], np.cross(self.V[f[1]], self.V[f[2]])) for f in self.faces) / 6
        self.assertAlmostEqual(vol, 3 * (1 / (6 * np.sqrt(2))), places=12)
        edges = [(f[k], f[(k + 1) % 3]) for f in self.faces for k in range(3)]
        self.assertEqual(len(set(edges)), len(edges))
        self.assertTrue(all((b, a) in edges for a, b in edges))


class TestSection(unittest.TestCase):
    OCTA_V = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    OCTA_F = [(0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4), (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5)]

    def test_ottaedro_a_meta_altezza(self):
        # appena sopra l'equatore: un quadrato, i quattro punti a z = 0.1
        loops = deltahedra.plane_section(self.OCTA_V, self.OCTA_F, axis=2, value=0.1)
        self.assertEqual(len(loops), 1)
        L = loops[0]
        self.assertEqual(len(L), 4)
        np.testing.assert_allclose(L[:, 2], 0.1)
        np.testing.assert_allclose(np.abs(L[:, :2]).sum(axis=1), 0.9)     # sul quadrato |x|+|y| = 0.9
        # in ordine: due punti consecutivi stanno su una stessa faccia (distanza = lato)
        for a, b in zip(L, np.roll(L, -1, axis=0)):
            self.assertAlmostEqual(np.linalg.norm(a - b), 0.9 * np.sqrt(2), places=12)

    def test_vertici_ripetuti_per_faccia(self):
        # le facce coi vertici duplicati, come nella mesh di M: la sezione e' la stessa
        V = [self.OCTA_V[i] for f in self.OCTA_F for i in f]
        F = [(3 * k, 3 * k + 1, 3 * k + 2) for k in range(len(self.OCTA_F))]
        loops = deltahedra.plane_section(V, F, axis=2, value=0.1)
        self.assertEqual([len(L) for L in loops], [4])

    def test_fuori_e_due_pezzi(self):
        self.assertEqual(deltahedra.plane_section(self.OCTA_V, self.OCTA_F, axis=2, value=2.0), [])
        # due ottaedri separati: due curve
        V = self.OCTA_V + [(x + 5, y, z) for x, y, z in self.OCTA_V]
        F = self.OCTA_F + [tuple(i + 6 for i in f) for f in self.OCTA_F]
        self.assertEqual(len(deltahedra.plane_section(V, F, axis=2, value=-0.3)), 2)


class TestWelded(unittest.TestCase):
    def test_vertici_saldati_e_centrati(self):
        # un tetraedro coi vertici ripetuti per faccia, come negli OBJ dei modelli
        P = [(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)]
        faces = [(0, 1, 2), (0, 3, 1), (0, 2, 3), (1, 3, 2)]
        lines = []
        for f in faces:
            lines += [f"v {P[i][0]} {P[i][1]} {P[i][2]}" for i in f]
        lines += [f"f {3 * k + 1} {3 * k + 2} {3 * k + 3}" for k in range(len(faces))]
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "t.obj")
            with open(path, "w") as fp:
                fp.write("\n".join(lines) + "\n")
            V, F = deltahedra.load_welded(path)
        self.assertEqual(len(V), 4)
        self.assertEqual(deltahedra.vertex_degrees(4, F), [3, 3, 3, 3])
        np.testing.assert_allclose(V.mean(axis=0), 0.0, atol=1e-12)


class TestStl(unittest.TestCase):
    def test_tetraedro_binario(self):
        import struct
        P = [(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)]
        faces = [(0, 1, 2), (0, 3, 1), (0, 2, 3), (1, 3, 2)]
        data = b"x" * 80 + struct.pack("<I", len(faces))
        for f in faces:
            data += struct.pack("<3f", 0, 0, 0)
            for i in f:
                data += struct.pack("<3f", *(c + 5.0 for c in P[i]))     # fuori dall'origine
            data += struct.pack("<H", 0)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "t.stl")
            with open(path, "wb") as fp:
                fp.write(data)
            V, F = deltahedra.load_stl(path)
        self.assertEqual(len(V), 4)
        self.assertEqual(len(F), 4)
        np.testing.assert_allclose(V.mean(axis=0), 0.0, atol=1e-12)
        for f, g in zip(F, faces):                   # l'ordine dei vertici delle facce resta
            np.testing.assert_allclose(V[list(f)], np.asarray(P, float)[list(g)], atol=1e-6)


class FakeModel:
    def __init__(self, name, radius):
        self.name, self.radius, self.location = name, radius, np.zeros(3)


class TestPlatea(unittest.TestCase):
    def setUp(self):
        radii = [1.0, 1.2, 1.1, 2.0, 1.5, 1.4, 2.4, 1.8, 1.3]
        self.models = [FakeModel(f"m{k}", r) for k, r in enumerate(radii)]
        self.order, self.rows = deltahedra.arrange(self.models, [2, 3, 4], gap=0.8,
                                                   row_gap=0.6, clearance=0.3)

    def test_file_per_grandezza(self):
        self.assertEqual([len(r) for r in self.rows], [2, 3, 4])
        self.assertLessEqual(max(m.radius for m in self.rows[0]), min(m.radius for m in self.rows[1]))
        self.assertLessEqual(max(m.radius for m in self.rows[1]), min(m.radius for m in self.rows[2]))

    def test_non_si_toccano_e_stanno_sul_pavimento(self):
        for a, b in itertools.combinations(self.models, 2):
            self.assertGreater(np.linalg.norm(a.location - b.location), a.radius + b.radius + 0.5)
        for m in self.models:
            self.assertAlmostEqual(m.location[2], m.radius + 0.3)

    def test_inquadratura(self):
        view = deltahedra.View(22.0, 40.0, 36.0, 16 / 9)
        centres = [m.location for m in self.models]
        radii = [m.radius for m in self.models]
        target, d = deltahedra.frame_all(view, centres, radii, (0.9, 0.8))
        x, y = view.project(deltahedra.sphere_cloud(centres, radii), target, d)
        # piena in una delle due dimensioni, dentro nell'altra, centrata
        self.assertTrue(abs(x.max() - x.min() - 0.9) < 1e-3 or abs(y.max() - y.min() - 0.8) < 1e-3)
        self.assertLess(x.max() - x.min(), 0.9 + 1e-3)
        self.assertLess(y.max() - y.min(), 0.8 + 1e-3)
        self.assertAlmostEqual((x.min() + x.max()) / 2, 0.5, places=4)
        self.assertAlmostEqual((y.min() + y.max()) / 2, 0.5, places=4)


if __name__ == "__main__":
    unittest.main()
