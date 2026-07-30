from odoo.tests.common import TransactionCase


class TestResConfigSettings(TransactionCase):

    def test_parametre_desactive_par_defaut(self):
        settings = self.env['res.config.settings'].create({})
        self.assertFalse(settings.haccp_use_native_expiry)

    def test_activation_ecrit_le_parametre(self):
        settings = self.env['res.config.settings'].create({
            'haccp_use_native_expiry': True,
        })
        settings.execute()
        value = self.env['ir.config_parameter'].sudo().get_param(
            'haccp_report.use_native_expiry'
        )
        self.assertEqual(value, 'True')

    def test_indicateur_product_expiry_installe(self):
        settings = self.env['res.config.settings'].create({})
        expected = 'expiration_date' in self.env['stock.lot']._fields
        self.assertEqual(settings.haccp_product_expiry_installed, expected)
