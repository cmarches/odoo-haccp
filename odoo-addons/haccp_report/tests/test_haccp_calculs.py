from datetime import date, timedelta
from odoo.tests.common import TransactionCase


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
