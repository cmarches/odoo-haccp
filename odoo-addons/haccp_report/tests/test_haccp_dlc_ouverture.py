from datetime import timedelta
from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestHaccpDlcOuverture(TransactionCase):

    def _make(self, **overrides):
        vals = {
            'product_name': 'Sauce tomate maison',
            'famille': 'plat_cuisine',
            'condition': 'refrigere',
            'date_ouverture': fields.Datetime.now(),
            'operateur_id': self.env.user.id,
        }
        vals.update(overrides)
        return self.env['haccp.dlc.ouverture'].create(vals)

    def test_reference_auto_generee(self):
        rec = self._make()
        self.assertNotEqual(rec.reference, 'Nouveau')
        self.assertTrue(rec.reference)

    def test_duree_calculee_depuis_table_partagee(self):
        rec = self._make(famille='plat_cuisine', condition='refrigere')
        self.assertEqual(rec.duree_jours, 3)

    def test_date_limite_calculee(self):
        ouverture = fields.Datetime.now()
        rec = self._make(famille='laitier', condition='refrigere', date_ouverture=ouverture)
        self.assertEqual(rec.date_limite, ouverture.date() + timedelta(days=7))

    def test_statut_par_defaut_ouvert(self):
        rec = self._make()
        self.assertEqual(rec.statut, 'ouvert')

    def test_action_cloturer_termine(self):
        rec = self._make()
        rec.action_cloturer('termine')
        self.assertEqual(rec.statut, 'termine')
        self.assertTrue(rec.date_cloture)

    def test_action_cloturer_deja_cloture_leve_erreur(self):
        rec = self._make()
        rec.action_cloturer('jete')
        with self.assertRaises(UserError):
            rec.action_cloturer('termine')

    def test_est_expire_quand_date_limite_passee_et_ouvert(self):
        ouverture = fields.Datetime.now() - timedelta(days=30)
        rec = self._make(famille='laitier', condition='refrigere', date_ouverture=ouverture)
        self.assertTrue(rec.est_expire)

    def test_est_expire_faux_si_cloture(self):
        ouverture = fields.Datetime.now() - timedelta(days=30)
        rec = self._make(famille='laitier', condition='refrigere', date_ouverture=ouverture)
        rec.action_cloturer('jete')
        self.assertFalse(rec.est_expire)

    def test_access_token_genere_a_la_creation(self):
        rec = self._make()
        self.assertTrue(rec.access_token)

    def test_duree_zero_conservation_non_recommandee(self):
        rec = self._make(famille='viande_crue', condition='ambiant')
        self.assertEqual(rec.duree_jours, 0)
        self.assertFalse(rec.date_limite)

    def test_action_cloturer_statut_invalide_leve_erreur(self):
        rec = self._make()
        with self.assertRaises(ValueError):
            rec.action_cloturer('bogus')

    def test_lot_id_optionnel_et_stocke(self):
        product = self.env['product.template'].create({
            'name': 'Produit test lot',
            'tracking': 'lot',
        })
        lot = self.env['stock.lot'].create({
            'name': 'LOT-TEST-001',
            'product_id': product.product_variant_id.id,
        })
        rec = self._make(product_id=product.id, lot_id=lot.id)
        self.assertEqual(rec.lot_id, lot)

    def test_lot_id_vide_par_defaut(self):
        rec = self._make()
        self.assertFalse(rec.lot_id)
