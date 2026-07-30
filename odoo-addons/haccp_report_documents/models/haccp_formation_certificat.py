from odoo import fields, models


class HaccpFormationCertificat(models.Model):
    _name = 'haccp.formation.certificat'
    _description = 'Justificatif de formation individuelle HACCP'
    _order = 'date_formation desc'

    employe_id = fields.Many2one('res.users', string='Employé', required=True)
    type_formation = fields.Selection([
        ('haccp_initiale', 'HACCP initiale'),
        ('recyclage_haccp', 'Recyclage HACCP'),
        ('allergenes', 'Allergènes'),
        ('hygiene_alimentaire', 'Hygiène alimentaire'),
        ('autre', 'Autre'),
    ], string='Type de formation', required=True)
    date_formation = fields.Date(string='Date de formation', required=True)
    document_id = fields.Many2one(
        'documents.document', string='Justificatif', required=True
    )
    commentaire = fields.Text(string='Commentaire')
