"""
Test per geometry.read_obj: lettura di un OBJ minimo e conversione da Y in alto
a Z in alto.
"""

import os
import tempfile
import unittest

import numpy as np

from context import geometry


OBJ = """# un tetraedro
o tetra
v 1.0 0.0 0.0
v 0.0 1.0 0.0
v 0.0 0.0 1.0
v 0.0 0.0 0.0
vn 0 0 1
s off
f 1//1 2//1 3//1
f 4/1/1 2/1/1 1/1/1
f 4 3 2
f 4 1 3
"""


class TestReadObj(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".obj")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(OBJ)

    def tearDown(self):
        os.remove(self.path)

    def test_facce_con_e_senza_barre(self):
        md = geometry.read_obj(self.path, y_up=False)
        self.assertEqual(len(md.vertices), 4)
        self.assertEqual(md.faces, [[0, 1, 2], [3, 1, 0], [3, 2, 1], [3, 0, 2]])

    def test_y_in_alto_diventa_z_in_alto(self):
        md = geometry.read_obj(self.path, y_up=True)
        # (x, y, z) -> (x, -z, y): l'asse Y del file va su Z
        self.assertEqual(md.vertices[1], (0.0, -0.0, 1.0))
        self.assertEqual(md.vertices[2], (0.0, -1.0, 0.0))

    def test_la_conversione_e_una_rotazione(self):
        a = np.asarray(geometry.read_obj(self.path, y_up=False).vertices)
        b = np.asarray(geometry.read_obj(self.path, y_up=True).vertices)
        R = np.linalg.lstsq(a, b, rcond=None)[0].T
        self.assertAlmostEqual(np.linalg.det(R), 1.0, places=12)


if __name__ == "__main__":
    unittest.main()
