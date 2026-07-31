import base64
import hashlib
import logging

import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

DEFAULT_MANIFEST_URL = 'https://haccp.aifluencedigital.com/documents/manifest.json'


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
    def _get_manifest_url(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'haccp_report.manifest_url', DEFAULT_MANIFEST_URL
        )

    @api.model
    def action_sync_documents(self):
        if not self.env.user.has_group('quality.group_quality_manager'):
            raise UserError(_('Cette action est réservée aux responsables qualité.'))
        manifest_url = self._get_manifest_url()
        try:
            resp = requests.get(manifest_url, timeout=10)
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

    @api.model
    def action_load_demo_data(self):
        if not self.env.user.has_group('quality.group_quality_manager'):
            raise UserError(_('Cette action est réservée aux responsables qualité.'))

        BASE = self._get_manifest_url().rsplit('/', 1)[0]
        DEMO_DOCS = [
            ('fiche-temperatures-positives', 'releves',
             'Traçabilité des températures frigos 0-5°C',
             f'{BASE}/AIFD-fiche-temperatures-positives.pdf'),
            ('fiche-temperatures-negatives', 'releves',
             'Traçabilité des températures congélateurs -18°C',
             f'{BASE}/AIFD-fiche-temperatures-negatives.pdf'),
            ('registre-allergenes', 'releves',
             'Déclaration et suivi des 14 allergènes majeurs',
             f'{BASE}/AIFD-registre-allergenes.pdf'),
            ('affiche-lavage-mains', 'affiches',
             'Protocole hygiène des mains en 7 étapes',
             f'{BASE}/AIFD-affiche-lavage-mains.pdf'),
            ('affiche-planches-decoupe', 'affiches',
             'Code couleur des planches selon la famille alimentaire',
             f'{BASE}/AIFD-affiche-planches-decoupe.pdf'),
            ('affiche-chaine-froid', 'affiches',
             'Températures réglementaires de conservation par famille',
             f'{BASE}/AIFD-affiche-chaine-froid.pdf'),
            ('affiche-tenue-hygiene', 'affiches',
             'Équipements de protection individuelle obligatoires en cuisine',
             f'{BASE}/AIFD-affiche-tenue-hygiene.pdf'),
            ('affiche-fiche-recette', 'affiches',
             'Modèle de fiche recette avec allergènes et CCP',
             f'{BASE}/AIFD-affiche-fiche-recette.pdf'),
            ('affiche-coupure-electrique', 'affiches',
             'Procédure en cas de coupure de courant sur les équipements frigorifiques',
             f'{BASE}/AIFD-affiche-coupure-electrique.pdf'),
            ('hygiene-3', 'fiches_pratiques',
             'Fiche pratique hygiène — nettoyage et désinfection',
             f'{BASE}/AIFD-hygiene-3.pdf'),
            ('hygiene-4', 'fiches_pratiques',
             'Fiche pratique hygiène — gestion des déchets',
             f'{BASE}/AIFD-hygiene-4.pdf'),
            ('hygiene-5', 'fiches_pratiques',
             'Fiche pratique hygiène — lutte contre les nuisibles',
             f'{BASE}/AIFD-hygiene-5.pdf'),
            ('plan-nettoyage', 'fiches_pratiques',
             'Plan de nettoyage et désinfection hebdomadaire',
             f'{BASE}/AIFD-plan-nettoyage.pdf'),
            ('plan-nettoyage-durable', 'fiches_pratiques',
             'Plan de nettoyage éco-responsable avec produits certifiés',
             f'{BASE}/AIFD-plan-nettoyage-durable.pdf'),
        ]

        created = 0
        for name, category, description, source_url in DEMO_DOCS:
            if not self.search([('name', '=', name)], limit=1):
                self.create({
                    'name': name,
                    'category': category,
                    'description': description,
                    'source_url': source_url,
                })
                created += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Données de démonstration'),
                'message': _('%d document(s) chargé(s). Cliquez "Mettre à jour les documents" dès que le site est prêt.') % created,
                'type': 'success' if created else 'warning',
                'sticky': False,
            },
        }
