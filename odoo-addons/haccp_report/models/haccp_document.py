import base64
import hashlib
import logging

import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

MANIFEST_URL = 'https://aifluencedigital.com/haccp/manifest.json'


class HaccpDocument(models.Model):
    _name = 'haccp.document'
    _description = 'Document HACCP'
    _order = 'category, name'

    name = fields.Char(string='Nom', required=True)
    category = fields.Selection([
        ('releves', 'Relevés & traçabilité'),
        ('affiches', 'Affiches de sensibilisation'),
        ('reglementation', 'Réglementation'),
        ('fiches_pratiques', 'Fiches pratiques'),
    ], string='Catégorie', required=True)
    description = fields.Text(string='Description')
    source_url = fields.Char(string='URL source')
    attachment_id = fields.Many2one('ir.attachment', string='Fichier PDF', ondelete='set null')
    date_sync = fields.Datetime(string='Dernière synchronisation')
    file_hash = fields.Char(string='Hash MD5')

    statut = fields.Char(string='Statut', compute='_compute_statut')

    @api.depends('attachment_id')
    def _compute_statut(self):
        for rec in self:
            rec.statut = '✓ Téléchargé' if rec.attachment_id else '⬇ Non téléchargé'

    @api.model
    def action_sync_documents(self):
        try:
            resp = requests.get(MANIFEST_URL, timeout=10)
            resp.raise_for_status()
            manifest = resp.json()
        except Exception as exc:
            raise UserError(_('Impossible de récupérer le manifest : %s') % str(exc))

        added = updated = unchanged = 0
        for entry in manifest.get('documents', []):
            doc = self.search([('source_url', '=', entry['url'])], limit=1)
            remote_hash = entry.get('hash', '')

            if not doc:
                doc = self.create({
                    'name': entry['name'],
                    'category': entry['category'],
                    'description': entry.get('description', ''),
                    'source_url': entry['url'],
                })

            if doc.file_hash == remote_hash and doc.attachment_id:
                unchanged += 1
                continue

            try:
                pdf_resp = requests.get(entry['url'], timeout=30)
                pdf_resp.raise_for_status()
                pdf_data = pdf_resp.content
            except Exception as exc:
                _logger.warning('Échec téléchargement %s : %s', entry['url'], exc)
                continue

            local_hash = hashlib.md5(pdf_data).hexdigest()
            filename = entry['url'].rstrip('/').split('/')[-1]
            encoded = base64.b64encode(pdf_data).decode()

            if doc.attachment_id:
                doc.attachment_id.write({'datas': encoded, 'name': filename})
                updated += 1
            else:
                attachment = self.env['ir.attachment'].create({
                    'name': filename,
                    'datas': encoded,
                    'res_model': 'haccp.document',
                    'res_id': doc.id,
                    'mimetype': 'application/pdf',
                })
                doc.attachment_id = attachment
                added += 1

            doc.write({
                'file_hash': local_hash,
                'date_sync': fields.Datetime.now(),
                'name': entry['name'],
                'category': entry['category'],
                'description': entry.get('description', ''),
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Synchronisation terminée'),
                'message': _(
                    '%d ajouté(s), %d mis à jour, %d inchangé(s)'
                ) % (added, updated, unchanged),
                'type': 'success',
                'sticky': False,
            },
        }
