from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestHaccpDlcOuvertureSecurity(TransactionCase):

    def setUp(self):
        super().setUp()
        self.portal_user = self.env['res.users'].create({
            'name': 'Cuisinier Test',
            'login': 'cuisinier.test@example.com',
            'group_ids': [(6, 0, [
                self.env.ref('base.group_portal').id,
                self.env.ref('haccp_report.group_haccp_kitchen').id,
            ])],
        })
        self.quality_user = self.env['res.users'].create({
            'name': 'Quality User Test',
            'login': 'quality.test@example.com',
            'group_ids': [(6, 0, [
                self.env.ref('quality.group_quality_user').id,
            ])],
        })

    def test_utilisateur_portail_cuisine_ne_peut_pas_creer_directement(self):
        with self.assertRaises(AccessError):
            self.env['haccp.dlc.ouverture'].with_user(self.portal_user).check_access_rights(
                'create', raise_exception=True
            )

    def test_utilisateur_portail_cuisine_ne_peut_pas_lire_directement(self):
        rec = self.env['haccp.dlc.ouverture'].create({
            'product_name': 'Test',
            'famille': 'autre',
            'condition': 'refrigere',
            'date_ouverture': fields.Datetime.now(),
            'operateur_id': self.env.user.id,
        })
        with self.assertRaises(AccessError):
            rec.with_user(self.portal_user).read(['product_name'])

    def test_quality_user_peut_creer(self):
        rec = self.env['haccp.dlc.ouverture'].with_user(self.quality_user).create({
            'product_name': 'Test',
            'famille': 'autre',
            'condition': 'refrigere',
            'date_ouverture': fields.Datetime.now(),
            'operateur_id': self.quality_user.id,
        })
        self.assertTrue(rec)

    def test_quality_user_ne_peut_pas_supprimer(self):
        rec = self.env['haccp.dlc.ouverture'].create({
            'product_name': 'Test',
            'famille': 'autre',
            'condition': 'refrigere',
            'date_ouverture': fields.Datetime.now(),
            'operateur_id': self.env.user.id,
        })
        with self.assertRaises(AccessError):
            rec.with_user(self.quality_user).unlink()
