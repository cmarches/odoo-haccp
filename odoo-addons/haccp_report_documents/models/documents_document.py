from odoo import _, api, models


class DocumentsDocument(models.Model):
    _inherit = 'documents.document'

    @api.model
    def action_sync_haccp_portal_access(self):
        """Donne (ou confirme) l'accès en lecture des utilisateurs portail
        HACCP (gérant, cuisine) aux dossiers Documents HACCP concernés.
        Idempotent : ne duplique pas un accès déjà existant. Action manuelle
        — pas de déclenchement automatique à l'ajout d'un utilisateur au
        groupe (cf. spec, section 4)."""
        rapports = self.env.ref('haccp_report_documents.documents_folder_haccp_rapports')
        bibliotheque = self.env.ref('haccp_report_documents.documents_folder_haccp_bibliotheque')
        formations = self.env.ref('haccp_report_documents.documents_folder_haccp_formations')

        gerants = self.env.ref('haccp_report_documents.group_haccp_gerant').user_ids
        cuisiniers = self.env.ref('haccp_report.group_haccp_kitchen').user_ids

        created = 0
        created += self._ensure_access(gerants.mapped('partner_id'), rapports)
        created += self._ensure_access(gerants.mapped('partner_id'), bibliotheque)
        created += self._ensure_access(gerants.mapped('partner_id'), formations)
        created += self._ensure_access(cuisiniers.mapped('partner_id'), bibliotheque)
        created += self._ensure_access(cuisiniers.mapped('partner_id'), formations)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Synchronisation terminée'),
                'message': _('%d nouvel(aux) accès créé(s).') % created,
                'type': 'success',
                'sticky': False,
            },
        }

    def _ensure_access(self, partners, document):
        Access = self.env['documents.access']
        created = 0
        for partner in partners:
            existing = Access.search([
                ('document_id', '=', document.id),
                ('partner_id', '=', partner.id),
            ], limit=1)
            if not existing:
                Access.create({
                    'document_id': document.id,
                    'partner_id': partner.id,
                    'role': 'view',
                })
                created += 1
        return created
