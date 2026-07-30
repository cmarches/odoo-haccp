from odoo.tests.common import TransactionCase


class TestDocumentsFolders(TransactionCase):

    def test_dossier_racine_haccp_existe(self):
        folder = self.env.ref('haccp_report_documents.documents_folder_haccp')
        self.assertEqual(folder.type, 'folder')
        self.assertFalse(folder.folder_id)

    def test_trois_sous_dossiers_rattaches_a_la_racine(self):
        racine = self.env.ref('haccp_report_documents.documents_folder_haccp')
        rapports = self.env.ref('haccp_report_documents.documents_folder_haccp_rapports')
        bibliotheque = self.env.ref('haccp_report_documents.documents_folder_haccp_bibliotheque')
        formations = self.env.ref('haccp_report_documents.documents_folder_haccp_formations')
        for sous_dossier in (rapports, bibliotheque, formations):
            self.assertEqual(sous_dossier.folder_id, racine)
            self.assertEqual(sous_dossier.type, 'folder')

    def test_groupe_gerant_implique_portail(self):
        groupe = self.env.ref('haccp_report_documents.group_haccp_gerant')
        portail = self.env.ref('base.group_portal')
        self.assertIn(portail, groupe.implied_ids)
