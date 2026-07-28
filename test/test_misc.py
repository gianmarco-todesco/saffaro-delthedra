"""
Test per compute_angle_from_sides e MeshData.
"""

import math
import unittest

from context import geometry


class TestComputeAngleFromSides(unittest.TestCase):
    def test_triangolo_equilatero(self):
        # Tutti i lati uguali -> ogni angolo e' 60 gradi.
        ang = geometry.compute_angle_from_sides(1, 1, 1)
        self.assertAlmostEqual(ang, math.radians(60), places=9)

    def test_triangolo_rettangolo_345(self):
        # Angolo opposto all'ipotenusa (lato a=5) = 90 gradi.
        ang = geometry.compute_angle_from_sides(5, 3, 4)
        self.assertAlmostEqual(ang, math.radians(90), places=9)

    def test_angolo_opposto_al_lato_piu_corto_e_il_piu_piccolo(self):
        # In 3-4-5 l'angolo opposto al lato 3 e' il piu' piccolo.
        piccolo = geometry.compute_angle_from_sides(3, 4, 5)
        grande = geometry.compute_angle_from_sides(4, 3, 5)
        self.assertLess(piccolo, grande)

    def test_triangolo_degenere_niente_nan(self):
        # Triangolo "piatto" (a = b + c): cosA e' al limite -1; il clamp evita nan.
        ang = geometry.compute_angle_from_sides(2, 1, 1)
        self.assertFalse(math.isnan(ang))
        self.assertAlmostEqual(ang, math.pi, places=9)


class TestMeshData(unittest.TestCase):
    def test_init_vuoto(self):
        md = geometry.MeshData()
        self.assertEqual(md.vertices, [])
        self.assertEqual(md.faces, [])

    def test_istanze_indipendenti(self):
        # Le liste non devono essere condivise tra istanze diverse.
        a = geometry.MeshData()
        b = geometry.MeshData()
        a.vertices.append((0, 0, 0))
        self.assertEqual(b.vertices, [])


class TestMeshDataAppend(unittest.TestCase):
    def _mesh(self, verts, faces):
        m = geometry.MeshData()
        m.vertices = list(verts)
        m.faces = [list(f) for f in faces]
        return m

    def test_fusione_vertici_e_facce(self):
        a = self._mesh([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [[0, 1, 2]])
        b = self._mesh([(2, 2, 2), (3, 2, 2), (2, 3, 2)], [[0, 1, 2]])
        a.append(b)
        self.assertEqual(len(a.vertices), 6)
        # la faccia di b va rimappata sommando l'offset (3 vertici gia' presenti)
        self.assertEqual(a.faces, [[0, 1, 2], [3, 4, 5]])

    def test_non_muta_l_argomento(self):
        a = self._mesh([(0, 0, 0)], [])
        b = self._mesh([(1, 1, 1), (2, 2, 2)], [[0, 1, 0]])
        a.append(b)
        self.assertEqual(b.vertices, [(1, 1, 1), (2, 2, 2)])
        self.assertEqual(b.faces, [[0, 1, 0]])

    def test_ritorna_self_ed_e_concatenabile(self):
        a = geometry.MeshData()
        b = self._mesh([(0, 0, 0)], [[0, 0, 0]])
        c = self._mesh([(1, 1, 1)], [[0, 0, 0]])
        self.assertIs(a.append(b), a)
        a.append(c)
        self.assertEqual(a.vertices, [(0, 0, 0), (1, 1, 1)])
        self.assertEqual(a.faces, [[0, 0, 0], [1, 1, 1]])

    def test_append_su_mesh_vuota(self):
        a = geometry.MeshData()
        b = self._mesh([(5, 5, 5)], [[0, 0, 0]])
        a.append(b)
        self.assertEqual(a.vertices, [(5, 5, 5)])
        self.assertEqual(a.faces, [[0, 0, 0]])


if __name__ == "__main__":
    unittest.main()
