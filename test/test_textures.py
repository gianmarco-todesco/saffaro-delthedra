"""
Test per textures.border_triangle: il triangolo e' equilatero, il bordo e'
scuro, il centro chiaro, e lo spessore del bordo e' quello chiesto.
"""

import math
import unittest

import numpy as np

import context  # noqa: F401  (sistema il sys.path)
import textures


def pixel(img, uv):
    size = img.shape[0]
    return img[int(uv[1] * size), int(uv[0] * size), 0]


class TestBorderTriangle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.img, cls.uvs = textures.border_triangle(size=512, border=0.25, dark=0.1, light=1.0)

    def test_uv_equilatero(self):
        A, B, C = (np.asarray(p) for p in self.uvs)
        for p, q in ((A, B), (B, C), (C, A)):
            self.assertAlmostEqual(np.linalg.norm(p - q), 1.0 - 2 * 0.02, places=12)
        self.assertGreater(A[1], B[1])                 # il primo vertice in alto
        self.assertLess(B[0], C[0])                    # poi in basso a sinistra, poi a destra

    def test_centro_chiaro_bordo_e_fuori_scuri(self):
        centre = sum(np.asarray(p) for p in self.uvs) / 3.0
        self.assertAlmostEqual(pixel(self.img, centre), 1.0)
        self.assertAlmostEqual(pixel(self.img, (0.01, 0.99)), 0.1)     # fuori
        A, B = (np.asarray(p) for p in self.uvs[:2])
        mid = (A + B) / 2                                              # sul lato
        self.assertAlmostEqual(pixel(self.img, mid + (centre - mid) * 0.1), 0.1)

    def test_spessore_del_bordo(self):
        # lungo il raggio che va dal centro al punto medio di un lato, il
        # passaggio da chiaro a scuro e' a border * inraggio dal lato
        centre = sum(np.asarray(p) for p in self.uvs) / 3.0
        A, B = (np.asarray(p) for p in self.uvs[:2])
        mid = (A + B) / 2
        inradius = (1.0 - 2 * 0.02) * math.sqrt(3) / 6
        unit = (centre - mid) / np.linalg.norm(centre - mid)
        self.assertAlmostEqual(pixel(self.img, mid + unit * 0.20 * inradius), 0.1)
        self.assertAlmostEqual(pixel(self.img, mid + unit * 0.30 * inradius), 1.0)

    def test_grigio_neutro(self):
        self.assertTrue(np.all(self.img[..., 0] == self.img[..., 1]))
        self.assertTrue(np.all(self.img[..., 1] == self.img[..., 2]))
        self.assertTrue(np.all(self.img[..., 3] == 1.0))


class TestSpessoreConLeUV(unittest.TestCase):
    def test_ingrandire_allarga_la_fascia(self):
        # texture col bordo sottile; la faccia mappata sul triangolo ingrandito
        # di k ha la fascia 1 - (1 - b0) / k: la si misura sui pixel
        b0, target = 0.05, 0.20
        img, uvs = textures.border_triangle(size=1024, border=b0, margin=0.12)
        k = textures.border_scale(target, b0)
        big = [np.asarray(p) for p in textures.scaled_uvs(uvs, k)]
        centre = sum(big) / 3.0
        mid = (big[0] + big[1]) / 2                       # punto medio di un lato della faccia
        r = np.linalg.norm(centre - mid)                  # inraggio della faccia, nella texture
        unit = (centre - mid) / r
        self.assertAlmostEqual(pixel(img, mid + unit * (target - 0.02) * r), 0.10)
        self.assertAlmostEqual(pixel(img, mid + unit * (target + 0.02) * r), 1.0)

    def test_k_uno_e_il_disegnato(self):
        self.assertAlmostEqual(textures.border_scale(0.1, 0.1), 1.0)

    def test_fuori_dominio(self):
        with self.assertRaises(ValueError):
            textures.border_scale(0.03, 0.05)          # piu' sottile del disegnato
        with self.assertRaises(ValueError):
            textures.scaled_uvs(textures.border_triangle_uvs(0.02), 1.5)   # esce dall'immagine


if __name__ == "__main__":
    unittest.main()
