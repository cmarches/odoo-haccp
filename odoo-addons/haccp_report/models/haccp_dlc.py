from datetime import date as date_cls, timedelta
from odoo import models, fields, api

_DLC_TABLE = {
    ('viande_crue', 'refrigere'): 3,
    ('viande_crue', 'congele'): 90,
    ('viande_crue', 'ambiant'): 0,
    ('poisson', 'refrigere'): 2,
    ('poisson', 'congele'): 90,
    ('poisson', 'ambiant'): 0,
    ('charcuterie', 'refrigere'): 5,
    ('charcuterie', 'congele'): 90,
    ('charcuterie', 'ambiant'): 30,
    ('laitier', 'refrigere'): 7,
    ('laitier', 'congele'): 30,
    ('laitier', 'ambiant'): 0,
    ('plat_cuisine', 'refrigere'): 3,
    ('plat_cuisine', 'congele'): 90,
    ('plat_cuisine', 'ambiant'): 0,
    ('legumes', 'refrigere'): 5,
    ('legumes', 'congele'): 180,
    ('legumes', 'ambiant'): 7,
    ('autre', 'refrigere'): 3,
    ('autre', 'congele'): 90,
    ('autre', 'ambiant'): 7,
}


class HaccpDlc(models.TransientModel):
    _name = 'haccp.dlc'
    _description = 'Calculateur DLC / DLUO'

    famille = fields.Selection([
        ('viande_crue', 'Viande crue'),
        ('poisson', 'Poisson'),
        ('charcuterie', 'Charcuterie'),
        ('laitier', 'Produit laitier'),
        ('plat_cuisine', 'Plat cuisiné'),
        ('legumes', 'Légumes'),
        ('autre', 'Autre'),
    ], string='Famille', required=True)

    condition = fields.Selection([
        ('refrigere', 'Réfrigéré (+4°C)'),
        ('congele', 'Congelé (-18°C)'),
        ('ambiant', 'Ambiant'),
    ], string='Condition de conservation', required=True)

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
            duree = _DLC_TABLE.get((rec.famille, rec.condition), 0)
            rec.duree_jours = duree
            if not rec.date_fabrication or not rec.famille or not rec.condition:
                rec.date_limite = False
                rec.statut = ''
                continue
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
