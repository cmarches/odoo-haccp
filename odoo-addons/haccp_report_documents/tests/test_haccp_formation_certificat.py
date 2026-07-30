from psycopg2.errors import NotNullViolation

from odoo import fields
from odoo.tests.common import TransactionCase


class TestHaccpFormationCertificat(TransactionCase):

    def setUp(self):
        super().setUp()
        attachment = self.env['ir.attachment'].create({
            'name': 'certificat-test.pdf',
            'datas': 'dGVzdA==',
            'mimetype': 'application/pdf',
        })
        self.document = self.env['documents.document'].create({
            'attachment_id': attachment.id,
            'folder_id': self.env.ref(
                'haccp_report_documents.documents_folder_haccp_formations'
            ).id,
        })

    def test_creation_certificat(self):
        rec = self.env['haccp.formation.certificat'].create({
            'employe_id': self.env.user.id,
            'type_formation': 'haccp_initiale',
            'date_formation': fields.Date.today(),
            'document_id': self.document.id,
        })
        self.assertTrue(rec)
        self.assertEqual(rec.employe_id, self.env.user)

    def test_type_formation_requis(self):
        with self.assertRaises(NotNullViolation):
            self.env['haccp.formation.certificat'].create({
                'employe_id': self.env.user.id,
                'date_formation': fields.Date.today(),
                'document_id': self.document.id,
            })
