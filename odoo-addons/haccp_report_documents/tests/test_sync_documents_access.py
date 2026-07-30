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
