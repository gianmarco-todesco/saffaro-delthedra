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


class TestFlatten1(unittest.TestCase):
    """flatten1_extended_face: il ventaglio di 12 triangoli diventa un ventaglio
    di 6 triangoli equilateri (sviluppabile: 6*60 = 360 gradi all'apice)."""

    def test_conteggi_e_input_immutato(self):
        md = ef.make_extended_face(ef.PHI_CLOSING)
        prima = list(md.vertices)
        fd = ef.flatten1_extended_face(md)
        self.assertEqual(len(fd.vertices), 13)
        self.assertEqual(len(fd.faces), 12)
        self.assertEqual(md.vertices, prima)   # non modifica l'originale

    def test_vertici_fissi(self):
        for phi in PHIS:
            md = ef.make_extended_face(phi)
            fd = ef.flatten1_extended_face(md)
            for i in (0, 4, 8, 12):            # i 3 angoli del triangolo di base + apice
                self.assertTrue(Vector(fd.vertices[i]).almost_equal(Vector(md.vertices[i])))

    def test_sei_triangoli_equilateri_unitari(self):
        for phi in PHIS:
            V = np.array(ef.flatten1_extended_face(ef.make_extended_face(phi)).vertices)
            apex = V[12]
            for k in range(0, 12, 2):          # (apice, P_k, P_k+2)
                p, q = V[k], V[(k + 2) % 12]
                L = [np.linalg.norm(x - y) for x, y in [(apex, p), (p, q), (q, apex)]]
                self.assertAlmostEqual(max(L) - min(L), 0.0, places=9)
                self.assertAlmostEqual(np.mean(L), 1.0, places=9)

    def test_vertici_dispari_nei_punti_medi(self):
        V = np.array(ef.flatten1_extended_face(ef.make_extended_face(math.radians(73))).vertices)
        for k in range(1, 12, 2):
            np.testing.assert_allclose(V[k], (V[k - 1] + V[(k + 1) % 12]) / 2, atol=1e-12)

    def test_meta_triangoli_complanari(self):
        # P1 sta sul segmento P0-P2, quindi le facce (apice,P0,P1) e (apice,P1,P2)
        # giacciono sullo stesso piano: le normali devono essere parallele.
        V = np.array(ef.flatten1_extended_face(ef.make_extended_face(math.radians(73))).vertices)
        apex = V[12]
        for k in range(0, 12, 2):
            n1 = np.cross(V[k] - apex, V[k + 1] - apex)
            n2 = np.cross(V[k + 1] - apex, V[(k + 2) % 12] - apex)
            self.assertAlmostEqual(np.linalg.norm(np.cross(n1, n2)), 0.0, places=12)

    def test_angolo_totale_all_apice(self):
        # 6 triangoli equilateri => 360 gradi: la faccia estesa e' sviluppabile.
        V = np.array(ef.flatten1_extended_face(ef.make_extended_face(ef.PHI_CLOSING)).vertices)
        apex = V[12]
        tot = 0.0
        for k in range(12):
            u = V[k] - apex
            v = V[(k + 1) % 12] - apex
            cos = np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v))
            tot += math.acos(np.clip(cos, -1.0, 1.0))
        self.assertAlmostEqual(tot, 2 * math.pi, places=12)

    def test_mesh_non_valida(self):
        with self.assertRaises(ValueError):
            ef.flatten1_extended_face(geometry.MeshData())


class TestFlatten2(unittest.TestCase):
    """flatten2_extended_face: il ventaglio collassa sul triangolo di base, che
    resta tassellato dalle 12 facce."""

    def test_conteggi_e_input_immutato(self):
        md = ef.make_extended_face(ef.PHI_CLOSING)
        prima = list(md.vertices)
        fd = ef.flatten2_extended_face(md)
        self.assertEqual(len(fd.vertices), 13)
        self.assertEqual(len(fd.faces), 12)
        self.assertEqual(md.vertices, prima)

    def test_angoli_fissi_e_apice_nel_baricentro(self):
        for phi in PHIS:
            md = ef.make_extended_face(phi)
            fd = ef.flatten2_extended_face(md)
            for i in (0, 4, 8):
                self.assertTrue(Vector(fd.vertices[i]).almost_equal(Vector(md.vertices[i])))
            V = np.array(fd.vertices)
            np.testing.assert_allclose(V[12], V[[0, 4, 8]].mean(axis=0), atol=1e-12)

    def test_punti_intermedi_a_un_quarto(self):
        for phi in PHIS:
            V = np.array(ef.flatten2_extended_face(ef.make_extended_face(phi)).vertices)
            for i in range(3):
                p0, p1 = V[4 * i], V[(4 * i + 4) % 12]
                for j in (1, 2, 3):
                    atteso = p0 + (p1 - p0) * j / 4
                    np.testing.assert_allclose(V[4 * i + j], atteso, atol=1e-12)

    def test_tutto_sul_piano_del_triangolo_di_base(self):
        V = np.array(ef.flatten2_extended_face(ef.make_extended_face(math.radians(73))).vertices)
        n = np.cross(V[4] - V[0], V[8] - V[0])
        n /= np.linalg.norm(n)
        for v in V:
            self.assertAlmostEqual(float(np.dot(v - V[0], n)), 0.0, places=12)

    def test_le_12_facce_tassellano_il_triangolo(self):
        # nessuna faccia degenere e somma delle aree = area del triangolo di base.
        V = np.array(ef.flatten2_extended_face(ef.make_extended_face(ef.PHI_CLOSING)).vertices)

        def area(p, q, r):
            return 0.5 * np.linalg.norm(np.cross(q - p, r - p))

        totale = 0.0
        for f in ef.make_extended_face(ef.PHI_CLOSING).faces:
            a = area(V[f[0]], V[f[1]], V[f[2]])
            self.assertGreater(a, 1e-9)
            totale += a
        self.assertAlmostEqual(totale, area(V[0], V[4], V[8]), places=12)

    def test_lato_del_triangolo_e_edge_span(self):
        # il triangolo di base non viene toccato: il lato resta `a`.
        for phi in PHIS:
            V = np.array(ef.flatten2_extended_face(ef.make_extended_face(phi)).vertices)
            self.assertAlmostEqual(float(np.linalg.norm(V[4] - V[0])), ef.edge_span(phi), places=9)

    def test_anche_dopo_flatten1(self):
        # P0, P4, P8 sono fissi in flatten1: flatten2 deve dare lo stesso risultato.
        md = ef.make_extended_face(ef.PHI_CLOSING)
        da_originale = np.array(ef.flatten2_extended_face(md).vertices)
        da_flatten1 = np.array(ef.flatten2_extended_face(ef.flatten1_extended_face(md)).vertices)
        np.testing.assert_allclose(da_flatten1, da_originale, atol=1e-12)

    def test_mesh_non_valida(self):
        with self.assertRaises(ValueError):
            ef.flatten2_extended_face(geometry.MeshData())


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
