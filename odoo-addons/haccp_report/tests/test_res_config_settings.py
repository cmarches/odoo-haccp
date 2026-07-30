from odoo.tests.common import TransactionCase


class TestResConfigSettings(TransactionCase):
    # NB : on utilise `.new({...})` plutôt que `.create({...})` pour instancier
    # res.config.settings. Sur cet environnement de dev partagé, un défaut
    # d'enregistrement préexistant et sans rapport avec ce module (le champ
    # `default_picking_policy` apporté par sale_stock n'est pas fusionné dans
    # le modèle res.config.settings alors que la colonne NOT NULL existe déjà
    # en base) fait échouer tout `.create({})` sur ce modèle avec une
    # NotNullViolation. `.new()` construit un enregistrement en mémoire (sans
    # INSERT SQL) et suffit pour exercer nos propres champs.
    #
    # NB2 : on appelle `.set_values()` plutôt que `.execute()`. `execute()`
    # englobe aussi l'installation/désinstallation en cascade des modules
    # liés aux cases à cocher "module_*" (ex. Digitalisation des relevés
    # bancaires), qui sur cette base contiennent des valeurs calculées sans
    # rapport avec notre configuration et déclenchent une tentative
    # d'installation réelle de module — un effet de bord dangereux sur un
    # serveur de dev partagé. `set_values()` est justement la méthode que la
    # documentation d'Odoo recommande d'appeler/surcharger pour ce cas
    # (`execute()` ne fait qu'appeler `set_values()` puis gérer les modules).

    def test_parametre_desactive_par_defaut(self):
        settings = self.env['res.config.settings'].new({})
        self.assertFalse(settings.haccp_use_native_expiry)

    def test_activation_ecrit_le_parametre(self):
        settings = self.env['res.config.settings'].new({
            'haccp_use_native_expiry': True,
        })
        settings.set_values()
        value = self.env['ir.config_parameter'].sudo().get_param(
            'haccp_report.use_native_expiry'
        )
        self.assertEqual(value, 'True')

    def test_indicateur_product_expiry_installe(self):
        settings = self.env['res.config.settings'].new({})
        expected = 'expiration_date' in self.env['stock.lot']._fields
        self.assertEqual(settings.haccp_product_expiry_installed, expected)
