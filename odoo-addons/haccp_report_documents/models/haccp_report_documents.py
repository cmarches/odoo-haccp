from odoo import models


class HaccpReport(models.Model):
    _inherit = 'haccp.report'

    def action_print_report(self):
        result = super().action_print_report()
        self._sync_documents_document()
        return result

    def _sync_documents_document(self):
        self.ensure_one()
        attachment = self._get_or_render_report_attachment()
        if not attachment:
            return
        folder = self.env.ref('haccp_report_documents.documents_folder_haccp_rapports')
        existing_doc = self.env['documents.document'].search([
            ('res_model', '=', 'haccp.report'),
            ('res_id', '=', self.id),
        ], limit=1)
        if existing_doc:
            existing_doc.write({'attachment_id': attachment.id, 'folder_id': folder.id})
        else:
            self.env['documents.document'].create({
                'attachment_id': attachment.id,
                'folder_id': folder.id,
                'res_model': 'haccp.report',
                'res_id': self.id,
            })

    def _get_or_render_report_attachment(self):
        """Retourne l'ir.attachment du PDF pour ce rapport, en le générant
        au besoin.

        action_print_report() (méthode héritée) ne fait que renvoyer la
        description de l'action de rapport au client web ; le rendu PDF et
        la création de l'ir.attachment (via le champ "attachment" de
        l'action de rapport) n'ont normalement lieu que lors de la requête
        HTTP de téléchargement déclenchée séparément par le navigateur —
        après le retour de cette méthode côté serveur. Pour classer le PDF
        dans Documents dès l'impression (sans dépendre de ce second aller-
        retour client), on déclenche ici le rendu explicitement si
        l'attachment n'existe pas encore. `force_report_rendering` neutralise
        le fallback HTML utilisé par Odoo en environnement de test."""
        self.ensure_one()
        domain = [
            ('res_model', '=', 'haccp.report'),
            ('res_id', '=', self.id),
        ]
        attachment = self.env['ir.attachment'].search(domain, limit=1)
        if attachment:
            return attachment
        report_action = self.env.ref('haccp_report.action_report_haccp_ddpp')
        self.env['ir.actions.report'].with_context(
            force_report_rendering=True
        )._render_qweb_pdf(report_action, self.ids)
        return self.env['ir.attachment'].search(domain, limit=1)
