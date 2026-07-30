from unittest.mock import patch

from odoo import fields
from odoo.tests.common import TransactionCase

from odoo.addons.base.models.ir_actions_report import IrActionsReport

REPORT_NAME = 'haccp_report.report_haccp_ddpp'


class TestHaccpReportDocumentsLink(TransactionCase):

    def _create_report(self):
        return self.env['haccp.report'].create({
            'date_start': fields.Date.today(),
            'date_end': fields.Date.today(),
            'responsible_id': self.env.user.id,
        })

    def _print_and_download(self, report):
        """Simule le cycle réel côté utilisateur : le bouton "Imprimer"
        déclenche action_print_report() (qui renvoie juste la description de
        l'action de rapport et supprime l'éventuel attachment existant),
        puis le client web télécharge effectivement le PDF — c'est cette
        seconde étape, gérée côté serveur par
        ir.actions.report._render_qweb_pdf(), qui rend réellement le PDF et
        crée l'ir.attachment (cf. le champ "attachment" de
        report/report_action.xml). `force_report_rendering` neutralise le
        fallback HTML qu'Odoo utilise par défaut en environnement de test,
        pour forcer ici un vrai rendu PDF comme en production."""
        report.action_print_report()
        self.env['ir.actions.report'].with_context(
            force_report_rendering=True
        )._render_qweb_pdf(REPORT_NAME, report.ids)

    def test_impression_cree_un_documents_document_dans_le_bon_dossier(self):
        report = self._create_report()
        self._print_and_download(report)

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
        report = self._create_report()
        self._print_and_download(report)
        self._print_and_download(report)

        docs = self.env['documents.document'].search([
            ('res_model', '=', 'haccp.report'),
            ('res_id', '=', report.id),
        ])
        self.assertEqual(len(docs), 1)

    def test_un_seul_rendu_pdf_par_cycle_impression_telechargement(self):
        """Garde-fou anti-régression : un cycle impression + téléchargement
        ne doit déclencher qu'un seul rendu PDF (_render_qweb_pdf). Une
        implémentation qui forcerait un rendu synchrone supplémentaire dans
        action_print_report() (comme une version antérieure de ce module le
        faisait) ferait passer ce compteur à 2, sans que la simple
        vérification du nombre de documents.document/ir.attachment ne le
        révèle (le rendu forcé et le rendu du téléchargement produisent un
        attachment de même nom, donc pas de doublon détectable côté
        attachment)."""
        report = self._create_report()

        with patch.object(
            IrActionsReport, '_render_qweb_pdf',
            autospec=True, wraps=IrActionsReport._render_qweb_pdf,
        ) as mocked_render:
            self._print_and_download(report)

        self.assertEqual(mocked_render.call_count, 1)
