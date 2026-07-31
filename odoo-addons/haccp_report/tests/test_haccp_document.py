import base64
import hashlib
from unittest.mock import MagicMock, patch
from odoo.tests.common import TransactionCase


class TestHaccpDocumentModel(TransactionCase):

    def test_create_document(self):
        doc = self.env['haccp.document'].create({
            'name': 'Fiche test',
            'category': 'releves',
            'source_url': 'https://example.com/test.pdf',
        })
        self.assertEqual(doc.name, 'Fiche test')
        self.assertEqual(doc.category, 'releves')

    def test_statut_non_telecharge(self):
        doc = self.env['haccp.document'].create({
            'name': 'Fiche test',
            'category': 'releves',
        })
        self.assertEqual(doc.statut, '⬇ Non téléchargé')

    def test_statut_telecharge(self):
        attachment = self.env['ir.attachment'].create({
            'name': 'test.pdf',
            'datas': base64.b64encode(b'%PDF-1.4').decode(),
            'mimetype': 'application/pdf',
        })
        doc = self.env['haccp.document'].create({
            'name': 'Fiche test',
            'category': 'releves',
            'attachment_id': attachment.id,
        })
        self.assertEqual(doc.statut, '✓ Téléchargé')


class TestHaccpDocumentManifestUrl(TransactionCase):

    def test_sync_utilise_url_par_defaut_si_non_configuree(self):
        # Ne pas dépendre de l'état ambiant du paramètre (cf. piège déjà
        # rencontré avec haccp_report.use_native_expiry sur une base
        # partagée) : on le retire explicitement avant de tester le défaut.
        self.env['ir.config_parameter'].sudo().set_param(
            'haccp_report.manifest_url', False
        )
        with patch('odoo.addons.haccp_report.models.haccp_document.requests.get') as mock_get:
            mock_manifest = MagicMock()
            mock_manifest.json.return_value = {'documents': []}
            mock_manifest.raise_for_status.return_value = None
            mock_get.return_value = mock_manifest
            self.env['haccp.document'].action_sync_documents()
        mock_get.assert_called_once_with(
            'https://haccp.aifluencedigital.com/documents/manifest.json', timeout=10
        )

    def test_sync_utilise_url_configuree_si_presente(self):
        self.env['ir.config_parameter'].sudo().set_param(
            'haccp_report.manifest_url', 'https://staging.example.com/manifest.json'
        )
        with patch('odoo.addons.haccp_report.models.haccp_document.requests.get') as mock_get:
            mock_manifest = MagicMock()
            mock_manifest.json.return_value = {'documents': []}
            mock_manifest.raise_for_status.return_value = None
            mock_get.return_value = mock_manifest
            self.env['haccp.document'].action_sync_documents()
        mock_get.assert_called_once_with(
            'https://staging.example.com/manifest.json', timeout=10
        )


class TestHaccpDocumentSync(TransactionCase):

    def _make_mock_responses(self, manifest, pdf_content=b'%PDF-1.4 test'):
        mock_manifest = MagicMock()
        mock_manifest.json.return_value = manifest
        mock_manifest.raise_for_status.return_value = None
        mock_pdf = MagicMock()
        mock_pdf.content = pdf_content
        mock_pdf.raise_for_status.return_value = None
        return [mock_manifest, mock_pdf]

    def test_sync_creates_new_document(self):
        manifest = {'documents': [{
            'name': 'Fiche températures',
            'category': 'releves',
            'description': 'Test',
            'url': 'https://example.com/fiche-temp.pdf',
            'hash': 'abc123',
        }]}
        with patch('odoo.addons.haccp_report.models.haccp_document.requests.get') as mock_get:
            mock_get.side_effect = self._make_mock_responses(manifest)
            self.env['haccp.document'].action_sync_documents()
        doc = self.env['haccp.document'].search([
            ('source_url', '=', 'https://example.com/fiche-temp.pdf')
        ])
        self.assertEqual(len(doc), 1)
        self.assertEqual(doc.name, 'Fiche températures')
        self.assertTrue(doc.attachment_id)
        self.assertEqual(doc.statut, '✓ Téléchargé')

    def test_sync_unchanged_skips_download(self):
        pdf_content = b'%PDF-1.4 test'
        file_hash = hashlib.md5(pdf_content).hexdigest()
        attachment = self.env['ir.attachment'].create({
            'name': 'existing.pdf',
            'datas': base64.b64encode(pdf_content).decode(),
            'mimetype': 'application/pdf',
        })
        self.env['haccp.document'].create({
            'name': 'Doc existant',
            'category': 'releves',
            'source_url': 'https://example.com/existing.pdf',
            'file_hash': file_hash,
            'attachment_id': attachment.id,
        })
        manifest = {'documents': [{
            'name': 'Doc existant',
            'category': 'releves',
            'description': '',
            'url': 'https://example.com/existing.pdf',
            'hash': file_hash,
        }]}
        with patch('odoo.addons.haccp_report.models.haccp_document.requests.get') as mock_get:
            mock_manifest = MagicMock()
            mock_manifest.json.return_value = manifest
            mock_manifest.raise_for_status.return_value = None
            mock_get.return_value = mock_manifest
            self.env['haccp.document'].action_sync_documents()
        self.assertEqual(mock_get.call_count, 1)

    def test_sync_updates_changed_document(self):
        old_pdf = b'%PDF-1.4 old'
        new_pdf = b'%PDF-1.4 new'
        new_hash = hashlib.md5(new_pdf).hexdigest()
        attachment = self.env['ir.attachment'].create({
            'name': 'doc.pdf',
            'datas': base64.b64encode(old_pdf).decode(),
            'mimetype': 'application/pdf',
        })
        doc = self.env['haccp.document'].create({
            'name': 'Doc',
            'category': 'releves',
            'source_url': 'https://example.com/doc.pdf',
            'file_hash': hashlib.md5(old_pdf).hexdigest(),
            'attachment_id': attachment.id,
        })
        manifest = {'documents': [{
            'name': 'Doc',
            'category': 'releves',
            'description': '',
            'url': 'https://example.com/doc.pdf',
            'hash': new_hash,
        }]}
        with patch('odoo.addons.haccp_report.models.haccp_document.requests.get') as mock_get:
            mock_get.side_effect = self._make_mock_responses(manifest, new_pdf)
            self.env['haccp.document'].action_sync_documents()
        doc.invalidate_recordset()
        self.assertEqual(doc.file_hash, new_hash)
