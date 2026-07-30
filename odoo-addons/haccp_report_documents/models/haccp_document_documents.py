from odoo import models


class HaccpDocument(models.Model):
    _inherit = 'haccp.document'

    def write(self, vals):
        result = super().write(vals)
        if 'attachment_id' in vals:
            for rec in self:
                rec._sync_documents_document()
        return result

    def _sync_documents_document(self):
        """Classe (ou met à jour) le PDF de ce document de la bibliothèque
        dans le dossier Documents "Bibliothèque de documents". Appelée
        depuis write() dès que attachment_id est modifié — voir plus haut.

        En sudo() : ce classement est une opération système déclenchée par
        action_sync_documents() (réservée aux responsables qualité, cf.
        haccp_report/models/haccp_document.py), indépendante des droits
        d'édition que l'utilisateur courant possède ou non sur le dossier
        Documents "Bibliothèque de documents" (règle d'accès
        documents_document_global_create_rule : il faut 'edit' sur le
        dossier pour y créer un documents.document)."""
        self.ensure_one()
        if not self.attachment_id:
            return
        Document = self.env['documents.document'].sudo()
        folder = self.env.ref('haccp_report_documents.documents_folder_haccp_bibliotheque')
        existing_doc = Document.search([
            ('res_model', '=', 'haccp.document'),
            ('res_id', '=', self.id),
        ], limit=1)
        if existing_doc:
            existing_doc.write({
                'attachment_id': self.attachment_id.id, 'folder_id': folder.id,
            })
        else:
            Document.create({
                'attachment_id': self.attachment_id.id,
                'folder_id': folder.id,
                'res_model': 'haccp.document',
                'res_id': self.id,
            })
