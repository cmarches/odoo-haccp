from odoo import fields
from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestHaccpPortalController(HttpCase):

    def setUp(self):
        super().setUp()
        self.kitchen_user = self.env['res.users'].create({
            'name': 'Cuisinier Test',
            'login': 'cuisinier.controller@example.com',
            'password': 'cuisinier123',
            'group_ids': [(6, 0, [
                self.env.ref('base.group_portal').id,
                self.env.ref('haccp_report.group_haccp_kitchen').id,
            ])],
        })
        self.plain_portal_user = self.env['res.users'].create({
            'name': 'Portail sans cuisine',
            'login': 'portail.simple@example.com',
            'password': 'portail123',
            'group_ids': [(6, 0, [self.env.ref('base.group_portal').id])],
        })

    def test_formulaire_refuse_sans_groupe_cuisine(self):
        self.authenticate('portail.simple@example.com', 'portail123')
        response = self.url_open('/haccp/etiquette/nouvelle')
        self.assertEqual(response.status_code, 403)

    def test_carte_etiquette_dlc_visible_sur_accueil_portail_cuisine(self):
        self.authenticate('cuisinier.controller@example.com', 'cuisinier123')
        response = self.url_open('/my')
        self.assertIn('Étiquettes DLC', response.text)
        self.assertIn('/haccp/etiquette/nouvelle', response.text)

    def test_carte_etiquette_dlc_invisible_pour_portail_sans_groupe(self):
        self.authenticate('portail.simple@example.com', 'portail123')
        response = self.url_open('/my')
        self.assertNotIn('Étiquettes DLC', response.text)

    def test_creation_force_operateur_depuis_session(self):
        self.authenticate('cuisinier.controller@example.com', 'cuisinier123')
        autre_utilisateur = self.env['res.users'].create({
            'name': 'Un Autre',
            'login': 'un.autre@example.com',
        })
        self.url_open('/haccp/etiquette/nouvelle', data={
            'csrf_token': self._get_csrf_token(),
            'product_name': 'Test création',
            'famille': 'autre',
            'condition': 'refrigere',
            'date_ouverture': fields.Datetime.now(),
            'operateur_id': autre_utilisateur.id,  # tentative d'usurpation
        })
        record = self.env['haccp.dlc.ouverture'].search(
            [('product_name', '=', 'Test création')], limit=1
        )
        self.assertTrue(record)
        self.assertEqual(record.operateur_id, self.kitchen_user)

    def test_fiche_publique_lisible_sans_connexion(self):
        record = self.env['haccp.dlc.ouverture'].create({
            'product_name': 'Fiche publique',
            'famille': 'autre',
            'condition': 'refrigere',
            'date_ouverture': fields.Datetime.now(),
            'operateur_id': self.kitchen_user.id,
        })
        response = self.url_open(record.access_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Fiche publique', response.text)

    def test_token_invalide_renvoie_404(self):
        record = self.env['haccp.dlc.ouverture'].create({
            'product_name': 'Test 404',
            'famille': 'autre',
            'condition': 'refrigere',
            'date_ouverture': fields.Datetime.now(),
            'operateur_id': self.kitchen_user.id,
        })
        response = self.url_open('/haccp/etiquette/%s/mauvais-token' % record.id)
        self.assertEqual(response.status_code, 404)

    def test_cloture_refusee_sans_connexion(self):
        record = self.env['haccp.dlc.ouverture'].create({
            'product_name': 'Test clôture',
            'famille': 'autre',
            'condition': 'refrigere',
            'date_ouverture': fields.Datetime.now(),
            'operateur_id': self.kitchen_user.id,
        })
        response = self.url_open(
            '%s/cloturer' % record.access_url, data={'statut': 'termine'},
            allow_redirects=False,
        )
        # Sans session, auth='user' redirige vers /web/login (303) plutôt que
        # de traiter la clôture. Si on suivait la redirection, url_open
        # atterrirait sur la page de login (200) et masquerait le vrai
        # code de statut renvoyé par la route elle-même : allow_redirects=False
        # permet d'observer directement la réponse de la route protégée.
        self.assertNotEqual(response.status_code, 200)
        self.assertEqual(record.statut, 'ouvert')

    def test_date_ouverture_invalide_ne_plante_pas_la_soumission(self):
        self.authenticate('cuisinier.controller@example.com', 'cuisinier123')
        response = self.url_open('/haccp/etiquette/nouvelle', data={
            'csrf_token': self._get_csrf_token(),
            'product_name': 'Test date invalide',
            'famille': 'autre',
            'condition': 'refrigere',
            'date_ouverture': 'pas-une-date',
            'operateur_id': self.kitchen_user.id,
        })
        self.assertNotEqual(response.status_code, 500)

    def test_cloture_avec_statut_invalide_ne_modifie_rien(self):
        self.authenticate('cuisinier.controller@example.com', 'cuisinier123')
        record = self.env['haccp.dlc.ouverture'].create({
            'product_name': 'Test statut invalide',
            'famille': 'autre',
            'condition': 'refrigere',
            'date_ouverture': fields.Datetime.now(),
            'operateur_id': self.kitchen_user.id,
        })
        response = self.url_open(
            '%s/cloturer' % record.access_url,
            data={'csrf_token': self._get_csrf_token(), 'statut': 'bidon'},
        )
        self.assertNotEqual(response.status_code, 500)
        self.assertEqual(record.statut, 'ouvert')

    def _get_csrf_token(self):
        response = self.url_open('/haccp/etiquette/nouvelle')
        import re
        match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
        return match.group(1) if match else ''
