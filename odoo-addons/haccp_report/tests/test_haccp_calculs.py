from datetime import date, timedelta
from odoo.tests.common import TransactionCase
from odoo import fields as ofields


class TestHaccpDlc(TransactionCase):

    def _make_dlc(self, famille, condition, date_fab=None):
        return self.env['haccp.dlc'].create({
            'famille': famille,
            'condition': condition,
            'date_fabrication': date_fab or date.today(),
        })

    def test_duree_viande_crue_refrigere(self):
        rec = self._make_dlc('viande_crue', 'refrigere')
        self.assertEqual(rec.duree_jours, 3)

    def test_duree_poisson_congele(self):
        rec = self._make_dlc('poisson', 'congele')
        self.assertEqual(rec.duree_jours, 90)

    def test_duree_charcuterie_ambiant(self):
        rec = self._make_dlc('charcuterie', 'ambiant')
        self.assertEqual(rec.duree_jours, 30)

    def test_duree_ambiant_zero_viande(self):
        rec = self._make_dlc('viande_crue', 'ambiant')
        self.assertEqual(rec.duree_jours, 0)

    def test_date_limite_calculee(self):
        fab = date.today() - timedelta(days=1)
        rec = self._make_dlc('viande_crue', 'refrigere', fab)
        self.assertEqual(rec.date_limite, fab + timedelta(days=3))

    def test_statut_valide(self):
        fab = date.today()
        rec = self._make_dlc('charcuterie', 'refrigere', fab)
        self.assertIn('✓ Valide', rec.statut)

    def test_statut_expire(self):
        fab = date.today() - timedelta(days=10)
        rec = self._make_dlc('viande_crue', 'refrigere', fab)
        self.assertEqual(rec.statut, '✗ Expiré')

    def test_statut_expire_bientot(self):
        fab = date.today() - timedelta(days=2)
        rec = self._make_dlc('viande_crue', 'refrigere', fab)
        self.assertIn('⚠', rec.statut)

    def test_statut_non_applicable_ambiant(self):
        rec = self._make_dlc('viande_crue', 'ambiant')
        self.assertIn('⚠', rec.statut)


class TestHaccpRefroidissement(TransactionCase):

    def test_heure_limite_plus_2h(self):
        debut = ofields.Datetime.now()
        rec = self.env['haccp.refroidissement'].create({'heure_debut': debut})
        diff = rec.heure_limite - debut
        self.assertAlmostEqual(diff.total_seconds(), 7200, delta=5)

    def test_heure_mi_parcours_plus_1h(self):
        debut = ofields.Datetime.now()
        rec = self.env['haccp.refroidissement'].create({'heure_debut': debut})
        diff = rec.heure_mi_parcours - debut
        self.assertAlmostEqual(diff.total_seconds(), 3600, delta=5)

    def test_statut_en_cours(self):
        debut = ofields.Datetime.now() - timedelta(minutes=30)
        rec = self.env['haccp.refroidissement'].create({'heure_debut': debut})
        self.assertEqual(rec.statut, '⏳ EN COURS')

    def test_statut_depasse(self):
        debut = ofields.Datetime.now() - timedelta(minutes=130)
        rec = self.env['haccp.refroidissement'].create({'heure_debut': debut})
        self.assertEqual(rec.statut, '✗ FENÊTRE DÉPASSÉE')


class TestHaccpDilution(TransactionCase):

    def _make_dil(self, volume, ratio, ratio_custom=0):
        return self.env['haccp.dilution'].create({
            'volume_total': volume,
            'ratio': ratio,
            'ratio_custom': ratio_custom,
        })

    def test_ratio_1_10_produit(self):
        rec = self._make_dil(1.0, '10')
        self.assertAlmostEqual(rec.volume_produit_ml, 1000 / 11, places=1)

    def test_ratio_1_10_eau(self):
        rec = self._make_dil(1.0, '10')
        self.assertAlmostEqual(rec.volume_eau_l, 1.0 - (1 / 11), places=3)

    def test_ratio_1_100(self):
        rec = self._make_dil(2.0, '100')
        self.assertAlmostEqual(rec.volume_produit_ml, 2000 / 101, places=1)

    def test_ratio_custom(self):
        rec = self._make_dil(1.0, 'custom', ratio_custom=30)
        self.assertAlmostEqual(rec.volume_produit_ml, 1000 / 31, places=1)

    def test_volume_zero_retourne_zero(self):
        rec = self._make_dil(0.0, '10')
        self.assertEqual(rec.volume_produit_ml, 0.0)
        self.assertEqual(rec.volume_eau_l, 0.0)

    def test_ratio_custom_zero_retourne_zero(self):
        rec = self._make_dil(1.0, 'custom', ratio_custom=0)
        self.assertEqual(rec.volume_produit_ml, 0.0)


class TestHaccpDecongelation(TransactionCase):

    def _make_dec(self, famille, poids, debut=None):
        return self.env['haccp.decongelation'].create({
            'famille': famille,
            'poids_kg': poids,
            'debut_decongelation': debut or ofields.Datetime.now(),
        })

    def test_duree_viande_entiere_2kg(self):
        rec = self._make_dec('viande_entiere', 2.0)
        self.assertAlmostEqual(rec.duree_heures, 48.0, places=1)

    def test_duree_poisson_1kg(self):
        rec = self._make_dec('poisson', 1.0)
        self.assertAlmostEqual(rec.duree_heures, 12.0, places=1)

    def test_duree_minimum_2h(self):
        rec = self._make_dec('viande_hachee', 0.1)
        self.assertEqual(rec.duree_heures, 2.0)

    def test_fin_decongelation_calculee(self):
        debut = ofields.Datetime.now()
        rec = self.env['haccp.decongelation'].create({
            'famille': 'volaille',
            'poids_kg': 1.0,
            'debut_decongelation': debut,
        })
        diff = rec.fin_decongelation - debut
        self.assertAlmostEqual(diff.total_seconds(), 20 * 3600, delta=60)

    def test_dlc_secondaire_j_plus_1(self):
        debut = ofields.Datetime.now()
        rec = self.env['haccp.decongelation'].create({
            'famille': 'poisson',
            'poids_kg': 1.0,
            'debut_decongelation': debut,
        })
        expected = (debut + timedelta(hours=12)).date() + timedelta(days=1)
        self.assertEqual(rec.dlc_secondaire, expected)
