from odoo import api, models


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

        self._ensure_access(gerants.mapped('partner_id'), rapports)
        self._ensure_access(gerants.mapped('partner_id'), bibliotheque)
        self._ensure_access(gerants.mapped('partner_id'), formations)
        self._ensure_access(cuisiniers.mapped('partner_id'), bibliotheque)
        self._ensure_access(cuisiniers.mapped('partner_id'), formations)

    def _ensure_access(self, partners, document):
        Access = self.env['documents.access']
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
