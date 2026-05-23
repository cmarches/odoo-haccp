from odoo import models, fields, api

_RATIO_VALUES = {'10': 10, '20': 20, '50': 50, '100': 100}


class HaccpDilution(models.TransientModel):
    _name = 'haccp.dilution'
    _description = 'Convertisseur de dilution produit nettoyant'

    volume_total = fields.Float(string='Volume total souhaité (litres)', required=True, digits=(10, 3))
    ratio = fields.Selection([
        ('10', '1:10'), ('20', '1:20'), ('50', '1:50'), ('100', '1:100'), ('custom', 'Personnalisé'),
    ], string='Ratio de dilution', required=True, default='10')
    ratio_custom = fields.Integer(string='Ratio personnalisé (1:N)')
    volume_produit_ml = fields.Float(string='Volume produit pur (ml)', compute='_compute_dilution', digits=(10, 1))
    volume_eau_l = fields.Float(string='Volume eau (litres)', compute='_compute_dilution', digits=(10, 3))

    @api.depends('volume_total', 'ratio', 'ratio_custom')
    def _compute_dilution(self):
        for rec in self:
            ratio_n = rec.ratio_custom if rec.ratio == 'custom' else _RATIO_VALUES.get(rec.ratio, 0)
            if rec.volume_total > 0 and ratio_n > 0:
                vol_produit_l = rec.volume_total / (ratio_n + 1)
                rec.volume_produit_ml = vol_produit_l * 1000
                rec.volume_eau_l = rec.volume_total - vol_produit_l
            else:
                rec.volume_produit_ml = 0.0
                rec.volume_eau_l = 0.0
