from odoo import fields
from odoo.tests.common import TransactionCase


class TestHaccpReportDocumentsLink(TransactionCase):

    def test_impression_cree_un_documents_document_dans_le_bon_dossier(self):
        report = self.env['haccp.report'].create({
            'date_start': fields.Date.today(),
            'date_end': fields.Date.today(),
            'responsible_id': self.env.user.id,
        })
        report.action_print_report()

        doc = self.env['documents.document'].search([
            ('res_model', '=', 'haccp.report'),
            ('res_id', '=', report.id),
        ])
        self.assertEqual(len(doc), 1)
        rapports_folder = self.env.ref(
            'haccp_report_documents.documents_folder_haccp_rapports'
        )
        self.assertEqual(doc.folder_id, rapports_folder)
        self.assertTrue(doc.attachment_id)

    def test_reimpression_ne_duplique_pas_le_documents_document(self):
        report = self.env['haccp.report'].create({
            'date_start': fields.Date.today(),
            'date_end': fields.Date.today(),
            'responsible_id': self.env.user.id,
        })
        report.action_print_report()
        report.action_print_report()

        docs = self.env['documents.document'].search([
            ('res_model', '=', 'haccp.report'),
            ('res_id', '=', report.id),
        ])
        self.assertEqual(len(docs), 1)
