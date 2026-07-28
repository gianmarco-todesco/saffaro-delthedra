"""
Test di non regressione per extended_face.py (faccia estesa del poliedro M).

Bloccano le proprieta' geometriche fondamentali (12 triangoli equilateri unitari)
e il valore del parametro che chiude M, trovato per bisezione.
"""

import math
import unittest

import numpy as np

from context import geometry  # noqa: F401  (sistema il sys.path)
import extended_face as ef

Vector = geometry.Vector

# alcuni phi di prova nel dominio (60°, 90°)
PHIS = [math.radians(63), math.radians(70), 1.283, math.radians(85)]


class TestGeometriaFacciaEstesa(unittest.TestCase):
    def test_conteggi(self):
        md = ef.make_extended_face(math.radians(73))
        self.assertEqual(len(md.vertices), 13)   # 12 esterni + apice
        self.assertEqual(len(md.faces), 12)

    def test_apice_sull_asse(self):
        md = ef.make_extended_face(math.radians(73))
        apex = md.vertices[12]
        self.assertAlmostEqual(apex[0], 0.0, places=9)
        self.assertAlmostEqual(apex[1], 0.0, places=9)
        self.assertGreater(apex[2], 0.0)

    def test_facce_equilatere_unitarie(self):
        for phi in PHIS:
            md = ef.make_extended_face(phi)
            V = np.array(md.vertices)
            for f in md.faces:
                L = [np.linalg.norm(V[f[a]] - V[f[b]]) for a, b in [(0, 1), (1, 2), (2, 0)]]
                self.assertAlmostEqual(max(L) - min(L), 0.0, places=9)  # equilatero
                self.assertAlmostEqual(np.mean(L), 1.0, places=9)       # lato 1

    def test_anello_esterno_unitario(self):
        for phi in PHIS:
            V = np.array(ef.make_extended_face(phi).vertices)
            outer = V[:12]
            for i in range(12):
                self.assertAlmostEqual(np.linalg.norm(outer[(i + 1) % 12] - outer[i]), 1.0, places=9)

    def test_raggi_apice_unitari(self):
        for phi in PHIS:
            V = np.array(ef.make_extended_face(phi).vertices)
            apex = V[12]
            for o in V[:12]:
                self.assertAlmostEqual(np.linalg.norm(o - apex), 1.0, places=9)

    def test_dominio(self):
        for bad in [math.radians(45), math.radians(60), math.radians(90), math.radians(95)]:
            with self.assertRaises(ValueError):
                ef.make_extended_face(bad)


class TestReparametrizzazione(unittest.TestCase):
    def test_edge_span_agli_estremi(self):
        # a -> sqrt(3) quando phi -> 60°, a -> 0 quando phi -> 90°.
        self.assertAlmostEqual(ef.edge_span(math.radians(60)), math.sqrt(3), places=6)
        self.assertAlmostEqual(ef.edge_span(math.radians(90)), 0.0, places=6)

    def test_edge_span_monotona_decrescente(self):
        vals = [ef.edge_span(math.radians(d)) for d in range(61, 90)]
        self.assertTrue(all(x > y for x, y in zip(vals, vals[1:])))

    def test_roundtrip_phi_da_a(self):
        for a in [0.2, 0.9108, 1.5]:
            phi = ef.phi_from_edge_span(a)
            self.assertAlmostEqual(ef.edge_span(phi), a, places=9)

    def test_edge_span_coerente_con_la_costruzione(self):
        # `a` deve coincidere con la distanza fra due vertici del triangolo di base.
        phi = math.radians(73)
        md = ef.make_extended_face(phi)
        corners = [Vector(md.vertices[ef.SEG_PER_EDGE * i]) for i in range(ef.N_EDGES)]
        a_costruito = (corners[0] - corners[1]).length()
        self.assertAlmostEqual(a_costruito, ef.edge_span(phi), places=9)


class TestChiusuraM(unittest.TestCase):
    def test_bisezione_trova_phi_di_chiusura(self):
        phi = ef.find_closing_parameter()
        self.assertAlmostEqual(math.degrees(phi), 73.491882, places=4)

    def test_alla_chiusura_la_fessura_e_nulla(self):
        phi = ef.find_closing_parameter()
        gap = np.linalg.norm(ef._closure_gap_vector(phi))
        self.assertLess(gap, 1e-9)

    def test_fuori_chiusura_la_fessura_e_grande(self):
        # a ~1° dal valore di chiusura la fessura e' gia' evidente.
        phi = ef.find_closing_parameter()
        gap_off = np.linalg.norm(ef._closure_gap_vector(phi + math.radians(1)))
        self.assertGreater(gap_off, 0.01)

    def test_costante_PHI_CLOSING_coerente(self):
        # La costante congelata deve coincidere con la bisezione e chiudere M.
        self.assertAlmostEqual(ef.PHI_CLOSING, ef.find_closing_parameter(), places=9)
        self.assertLess(np.linalg.norm(ef._closure_gap_vector(ef.PHI_CLOSING)), 1e-9)


class TestMakeM(unittest.TestCase):
    def setUp(self):
        self.M = ef.make_M()
        self.V = np.array(self.M.vertices)

    def test_conteggi(self):
        # 20 facce estese x 13 vertici / 12 triangoli.
        self.assertEqual(len(self.M.vertices), 20 * 13)   # 260
        self.assertEqual(len(self.M.faces), 20 * 12)       # 240

    def test_trasporto_rigido_triangoli_unitari(self):
        # Ogni faccia resta equilatera di lato 1 (matrix_from_triples e' una
        # similitudine fra triangoli equilateri uguali => isometria).
        for f in self.M.faces:
            p = self.V[f]
            L = [np.linalg.norm(p[a] - p[b]) for a, b in [(0, 1), (1, 2), (2, 0)]]
            self.assertAlmostEqual(max(L) - min(L), 0.0, places=9)
            self.assertAlmostEqual(np.mean(L), 1.0, places=9)

    def test_saldatura_vertici_distinti(self):
        # Le facce adiacenti si saldano: i 260 vertici collassano su 122 distinti
        # (12 vertici dell'icosaedro + 30*3 interni di spigolo + 20 apici).
        distinti = {tuple(np.round(v, 6)) for v in self.V}
        self.assertEqual(len(distinti), 122)

    def test_indici_facce_validi(self):
        n = len(self.M.vertices)
        for f in self.M.faces:
            for idx in f:
                self.assertTrue(0 <= idx < n)


if __name__ == "__main__":
    unittest.main()
