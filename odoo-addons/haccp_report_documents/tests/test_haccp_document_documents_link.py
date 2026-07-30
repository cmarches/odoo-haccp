import base64
from unittest.mock import patch, MagicMock

from odoo.tests.common import TransactionCase


class TestHaccpDocumentDocumentsLink(TransactionCase):

    def setUp(self):
        super().setUp()
        self.manager = self.env['res.users'].create({
            'name': 'Manager Test Bibliothèque',
            'login': 'manager.bib.test@example.com',
            'group_ids': [(6, 0, [self.env.ref('quality.group_quality_manager').id])],
        })

    def test_sync_cree_un_documents_document_dans_le_bon_dossier(self):
        fake_manifest = MagicMock()
        fake_manifest.raise_for_status = lambda: None
        fake_manifest.json.return_value = {'documents': [{
            'name': 'test-doc', 'category': 'affiches', 'description': 'Test',
            'url': 'http://example.com/test.pdf', 'hash': 'abc123',
        }]}
        fake_pdf = MagicMock()
        fake_pdf.raise_for_status = lambda: None
        fake_pdf.content = b'%PDF-1.4 fake content'

        with patch('requests.get', side_effect=[fake_manifest, fake_pdf]):
            self.env['haccp.document'].with_user(self.manager).action_sync_documents()

        haccp_doc = self.env['haccp.document'].search([('name', '=', 'test-doc')])
        self.assertTrue(haccp_doc)

        documents_doc = self.env['documents.document'].search([
            ('res_model', '=', 'haccp.document'),
            ('res_id', '=', haccp_doc.id),
        ])
        self.assertEqual(len(documents_doc), 1)
        bibliotheque_folder = self.env.ref(
            'haccp_report_documents.documents_folder_haccp_bibliotheque'
        )
        self.assertEqual(documents_doc.folder_id, bibliotheque_folder)
