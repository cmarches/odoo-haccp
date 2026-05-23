from datetime import timedelta
from odoo import models, fields, api


class HaccpRefroidissement(models.TransientModel):
    _name = 'haccp.refroidissement'
    _description = 'Minuteur de refroidissement HACCP'

    heure_debut = fields.Datetime(
        string='Heure de début du refroidissement',
        required=True,
        default=fields.Datetime.now,
    )
    heure_limite = fields.Datetime(
        string='Heure limite (+2h max)',
        compute='_compute_refroidissement',
    )
    heure_mi_parcours = fields.Datetime(
        string='Mi-parcours (+1h, objectif ≤21°C)',
        compute='_compute_refroidissement',
    )
    statut = fields.Char(string='Statut', compute='_compute_refroidissement')

    @api.depends('heure_debut')
    def _compute_refroidissement(self):
        for rec in self:
            if not rec.heure_debut:
                rec.heure_limite = False
                rec.heure_mi_parcours = False
                rec.statut = ''
                continue
            rec.heure_limite = rec.heure_debut + timedelta(hours=2)
            rec.heure_mi_parcours = rec.heure_debut + timedelta(hours=1)
            now = fields.Datetime.now()
            rec.statut = '⏳ EN COURS' if now < rec.heure_limite else '✗ FENÊTRE DÉPASSÉE'
