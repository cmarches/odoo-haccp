from odoo.tests.common import TransactionCase


class TestResConfigSettings(TransactionCase):

    def test_parametre_desactive_par_defaut(self):
        # Ne pas dépendre de l'état ambiant du paramètre global (une
        # activation manuelle antérieure sur une base partagée peut l'avoir
        # laissé à True de façon persistante) : on le force explicitement.
        self.env['ir.config_parameter'].sudo().set_param(
            'haccp_report.use_native_expiry', 'False'
        )
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

    def test_url_manifest_pre_remplie_par_defaut(self):
        # Le data file (noupdate) fixe cette valeur à l'installation ; sur
        # une base partagée, un admin a pu la changer entre-temps -- on ne
        # teste donc pas "la valeur vaut exactement X" mais "un champ non
        # vide est affiché", ce qui suffit à couvrir l'intention (l'admin
        # voit toujours quelque chose, pas un champ vide au premier accès).
        settings = self.env['res.config.settings'].create({})
        self.assertTrue(settings.haccp_manifest_url)

    def test_modification_url_manifest_ecrit_le_parametre(self):
        settings = self.env['res.config.settings'].create({
            'haccp_manifest_url': 'https://staging.example.com/manifest.json',
        })
        settings.execute()
        value = self.env['ir.config_parameter'].sudo().get_param(
            'haccp_report.manifest_url'
        )
        self.assertEqual(value, 'https://staging.example.com/manifest.json')
