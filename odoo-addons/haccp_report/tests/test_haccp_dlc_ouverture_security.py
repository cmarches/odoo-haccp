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

    def test_utilisateur_portail_cuisine_ne_peut_pas_creer_directement(self):
        with self.assertRaises(AccessError):
            self.env['haccp.dlc.ouverture'].with_user(self.portal_user).create({
                'product_name': 'Test',
                'famille': 'autre',
                'condition': 'refrigere',
                'date_ouverture': fields.Datetime.now(),
                'operateur_id': self.portal_user.id,
            })

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
