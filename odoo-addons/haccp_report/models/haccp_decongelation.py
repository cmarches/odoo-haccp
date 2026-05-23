from datetime import timedelta
from odoo import models, fields, api

_HEURES_PAR_KG = {'viande_entiere': 24, 'volaille': 20, 'poisson': 12, 'viande_hachee': 8}
_DUREE_MIN = 2.0


class HaccpDecongelation(models.TransientModel):
    _name = 'haccp.decongelation'
    _description = 'Calculateur de décongélation'

    famille = fields.Selection([
        ('viande_entiere', 'Viande entière'), ('volaille', 'Volaille'),
        ('poisson', 'Poisson'), ('viande_hachee', 'Viande hachée'),
    ], string="Type d'aliment", required=True)
    poids_kg = fields.Float(string='Poids (kg)', required=True, digits=(10, 3))
    debut_decongelation = fields.Datetime(string='Début de décongélation', required=True, default=fields.Datetime.now)
    duree_heures = fields.Float(string='Durée estimée (heures)', compute='_compute_decongelation', digits=(10, 1))
    fin_decongelation = fields.Datetime(string='Fin de décongélation estimée', compute='_compute_decongelation')
    dlc_secondaire = fields.Date(string='DLC secondaire (après décongélation)', compute='_compute_decongelation')

    @api.depends('famille', 'poids_kg', 'debut_decongelation')
    def _compute_decongelation(self):
        for rec in self:
            if not rec.famille or not rec.poids_kg or not rec.debut_decongelation:
                rec.duree_heures = 0.0
                rec.fin_decongelation = False
                rec.dlc_secondaire = False
                continue
            h_par_kg = _HEURES_PAR_KG.get(rec.famille, 24)
            duree = max(rec.poids_kg * h_par_kg, _DUREE_MIN)
            rec.duree_heures = duree
            fin = rec.debut_decongelation + timedelta(hours=duree)
            rec.fin_decongelation = fin
            rec.dlc_secondaire = fin.date() + timedelta(days=1)
