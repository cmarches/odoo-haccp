from odoo.tests.common import TransactionCase


class TestSyncDocumentsAccess(TransactionCase):

    def setUp(self):
        super().setUp()
        self.gerant = self.env['res.users'].create({
            'name': 'Gérant Test',
            'login': 'gerant.sync.test@example.com',
            'group_ids': [(6, 0, [
                self.env.ref('base.group_portal').id,
                self.env.ref('haccp_report_documents.group_haccp_gerant').id,
            ])],
        })
        self.cuisinier = self.env['res.users'].create({
            'name': 'Cuisinier Sync Test',
            'login': 'cuisinier.sync.test@example.com',
            'group_ids': [(6, 0, [
                self.env.ref('base.group_portal').id,
                self.env.ref('haccp_report.group_haccp_kitchen').id,
            ])],
        })

    def test_sync_donne_acces_gerant_aux_trois_dossiers(self):
        self.env['documents.document'].action_sync_haccp_portal_access()
        rapports = self.env.ref('haccp_report_documents.documents_folder_haccp_rapports')
        bibliotheque = self.env.ref('haccp_report_documents.documents_folder_haccp_bibliotheque')
        formations = self.env.ref('haccp_report_documents.documents_folder_haccp_formations')
        for dossier in (rapports, bibliotheque, formations):
            acces = self.env['documents.access'].search([
                ('document_id', '=', dossier.id),
                ('partner_id', '=', self.gerant.partner_id.id),
            ])
            self.assertEqual(len(acces), 1)
            self.assertEqual(acces.role, 'view')

    def test_sync_donne_acces_cuisine_uniquement_bibliotheque_et_formations(self):
        self.env['documents.document'].action_sync_haccp_portal_access()
        bibliotheque = self.env.ref('haccp_report_documents.documents_folder_haccp_bibliotheque')
        formations = self.env.ref('haccp_report_documents.documents_folder_haccp_formations')
        rapports = self.env.ref('haccp_report_documents.documents_folder_haccp_rapports')
        for dossier in (bibliotheque, formations):
            acces = self.env['documents.access'].search([
                ('document_id', '=', dossier.id),
                ('partner_id', '=', self.cuisinier.partner_id.id),
            ])
            self.assertEqual(len(acces), 1)
        acces_rapports = self.env['documents.access'].search([
            ('document_id', '=', rapports.id),
            ('partner_id', '=', self.cuisinier.partner_id.id),
        ])
        self.assertFalse(acces_rapports)

    def test_sync_est_idempotent(self):
        self.env['documents.document'].action_sync_haccp_portal_access()
        self.env['documents.document'].action_sync_haccp_portal_access()
        rapports = self.env.ref('haccp_report_documents.documents_folder_haccp_rapports')
        acces = self.env['documents.access'].search([
            ('document_id', '=', rapports.id),
            ('partner_id', '=', self.gerant.partner_id.id),
        ])
        self.assertEqual(len(acces), 1)

    def test_sync_retourne_notification_avec_compteur(self):
        # NB : le nombre exact d'accès créés au premier passage dépend des
        # utilisateurs déjà membres des groupes HACCP sur la base (au moins
        # ceux créés dans setUp, potentiellement d'autres sur une base
        # partagée) ; on ne fige donc pas de valeur absolue, seulement que
        # le premier passage crée bien des accès (> 0) et que le second,
        # idempotent, n'en crée plus aucun (0).
        result = self.env['documents.document'].action_sync_haccp_portal_access()
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['tag'], 'display_notification')
        self.assertEqual(result['params']['type'], 'success')
        premier_compteur = int(result['params']['message'].split()[0])
        # Au minimum les 3 accès du gérant + 2 de la cuisine créés dans ce test.
        self.assertGreaterEqual(premier_compteur, 5)

        # Un second passage ne crée plus rien : le compteur doit retomber à 0.
        result_second = self.env['documents.document'].action_sync_haccp_portal_access()
        self.assertIn('0', result_second['params']['message'])
        self.assertEqual(int(result_second['params']['message'].split()[0]), 0)
