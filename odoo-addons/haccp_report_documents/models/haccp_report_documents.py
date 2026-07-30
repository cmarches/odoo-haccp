from odoo import api, models


class HaccpReport(models.Model):
    _inherit = 'haccp.report'

    def _sync_documents_document(self):
        """Classe (ou met à jour) le PDF du rapport dans le dossier
        Documents "Rapports HACCP". Appelée par IrAttachment.create() dès
        qu'un ir.attachment lié à ce rapport apparaît — voir plus bas."""
        self.ensure_one()
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'haccp.report'),
            ('res_id', '=', self.id),
        ], limit=1)
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


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model_create_multi
    def create(self, vals_list):
        """Rattache réactivement au dossier Documents "Rapports HACCP" tout
        ir.attachment créé pour un haccp.report.

        On ne peut pas s'appuyer sur haccp.report.action_print_report() pour
        déclencher ce rattachement : cette méthode (héritée, non modifiable
        ici) ne fait que renvoyer la description de l'action de rapport au
        client web — le rendu PDF effectif et la création de l'ir.attachment
        (via le champ "attachment" de report/report_action.xml) n'ont lieu
        que plus tard, lors de la requête HTTP de téléchargement déclenchée
        par le navigateur (cf. ir.actions.report._render_qweb_pdf). Réagir
        ici sur la création de l'attachment, plutôt que de forcer un rendu
        PDF synchrone dans action_print_report(), évite un rendu PDF en
        double (un pour classer dans Documents, un pour le téléchargement
        réel) tout en couvrant les deux cas."""
        attachments = super().create(vals_list)
        for attachment in attachments:
            if attachment.res_model == 'haccp.report' and attachment.res_id:
                report = self.env['haccp.report'].browse(attachment.res_id)
                report._sync_documents_document()
        return attachments
