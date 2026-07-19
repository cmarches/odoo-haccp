from datetime import date as date_cls, timedelta
from odoo import models, fields, api
from .haccp_dlc_table import DLC_TABLE, DLC_FAMILLE_SELECTION, DLC_CONDITION_SELECTION


class HaccpDlc(models.TransientModel):
    _name = 'haccp.dlc'
    _description = 'Calculateur DLC / DLUO'

    famille = fields.Selection(DLC_FAMILLE_SELECTION, string='Famille', required=True)
    condition = fields.Selection(DLC_CONDITION_SELECTION, string='Condition de conservation', required=True)

    date_fabrication = fields.Date(
        string='Date de fabrication / ouverture', required=True,
        default=fields.Date.today,
    )

    duree_jours = fields.Integer(string='Durée (jours)', compute='_compute_dlc')
    date_limite = fields.Date(string='Date limite', compute='_compute_dlc')
    statut = fields.Char(string='Statut', compute='_compute_dlc')

    @api.depends('famille', 'condition', 'date_fabrication')
    def _compute_dlc(self):
        today = date_cls.today()
        for rec in self:
            if not rec.date_fabrication or not rec.famille or not rec.condition:
                rec.duree_jours = 0
                rec.date_limite = False
                rec.statut = ''
                continue
            duree = DLC_TABLE.get((rec.famille, rec.condition), 0)
            rec.duree_jours = duree
            if duree == 0:
                rec.date_limite = False
                rec.statut = '⚠ Conservation non recommandée à cette température'
                continue
            limite = rec.date_fabrication + timedelta(days=duree)
            rec.date_limite = limite
            jours = (limite - today).days
            if jours < 0:
                rec.statut = '✗ Expiré'
            elif jours <= 2:
                rec.statut = f'⚠ Expire bientôt (≤2j) — {jours}j restant(s)'
            else:
                rec.statut = f'✓ Valide — {jours} jours restants'
