from odoo import models, fields, api


class HaccpReassort(models.TransientModel):
    _name = 'haccp.reassort'
    _description = 'Calculateur de point de réassort'

    stock_actuel = fields.Float(string='Stock actuel (unités)', required=True, digits=(10, 2))
    conso_journaliere = fields.Float(string='Consommation journalière (unités/jour)', required=True, digits=(10, 2))
    delai_livraison = fields.Integer(string='Délai de livraison (jours)', required=True)
    stock_securite = fields.Float(string='Stock de sécurité (unités)', digits=(10, 2))
    point_commande = fields.Float(string='Point de commande', compute='_compute_reassort', digits=(10, 2))
    jours_restants = fields.Float(string='Jours avant point de commande', compute='_compute_reassort', digits=(10, 1))
    statut = fields.Char(string='Statut', compute='_compute_reassort')

    @api.depends('stock_actuel', 'conso_journaliere', 'delai_livraison', 'stock_securite')
    def _compute_reassort(self):
        for rec in self:
            pc = rec.conso_journaliere * rec.delai_livraison + rec.stock_securite
            rec.point_commande = pc
            rec.jours_restants = (
                (rec.stock_actuel - pc) / rec.conso_journaliere
                if rec.conso_journaliere > 0 else 0.0
            )
            rec.statut = '✗ COMMANDER MAINTENANT' if rec.stock_actuel <= pc else '✓ OK'
