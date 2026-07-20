from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .haccp_dlc_table import DLC_TABLE, DLC_FAMILLE_SELECTION, DLC_CONDITION_SELECTION


class HaccpDlcOuverture(models.Model):
    _name = 'haccp.dlc.ouverture'
    _description = 'Ouverture DLC secondaire (étiquette cuisine)'
    _inherit = ['portal.mixin', 'mail.thread']
    _order = 'date_ouverture desc'

    reference = fields.Char(
        string='Référence', required=True, copy=False, readonly=True, default='Nouveau'
    )
    product_id = fields.Many2one('product.template', string='Produit (catalogue)')
    product_name = fields.Char(string='Nom du produit', required=True)
    famille = fields.Selection(DLC_FAMILLE_SELECTION, string='Famille', required=True)
    condition = fields.Selection(
        DLC_CONDITION_SELECTION, string='Condition de conservation', required=True
    )
    date_ouverture = fields.Datetime(
        string="Date d'ouverture", required=True, default=fields.Datetime.now
    )
    operateur_id = fields.Many2one(
        'res.users', string='Opérateur', required=True, readonly=True
    )
    duree_jours = fields.Integer(string='Durée (jours)', compute='_compute_dlc', store=True)
    date_limite = fields.Date(string='Date limite', compute='_compute_dlc', store=True)
    statut = fields.Selection([
        ('ouvert', 'Ouvert'),
        ('termine', 'Terminé'),
        ('jete', 'Jeté'),
    ], string='Statut', default='ouvert', required=True, readonly=True)
    date_cloture = fields.Datetime(string='Date de clôture', readonly=True)
    est_expire = fields.Boolean(string='Expiré', compute='_compute_est_expire')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', 'Nouveau') == 'Nouveau':
                vals['reference'] = (
                    self.env['ir.sequence'].next_by_code('haccp.dlc.ouverture') or 'Nouveau'
                )
        records = super().create(vals_list)
        for record in records:
            record._portal_ensure_token()
        return records

    @api.depends('famille', 'condition', 'date_ouverture')
    def _compute_dlc(self):
        for rec in self:
            duree = DLC_TABLE.get((rec.famille, rec.condition), 0)
            rec.duree_jours = duree
            if rec.date_ouverture and duree:
                rec.date_limite = rec.date_ouverture.date() + timedelta(days=duree)
            else:
                rec.date_limite = False

    @api.depends('statut', 'date_limite')
    def _compute_est_expire(self):
        today = fields.Date.today()
        for rec in self:
            rec.est_expire = bool(
                rec.statut == 'ouvert' and rec.date_limite and rec.date_limite < today
            )

    def action_cloturer(self, statut):
        self.ensure_one()
        if statut not in ('termine', 'jete'):
            raise ValueError('statut de clôture invalide : %s' % statut)
        if self.statut != 'ouvert':
            raise UserError(_('Cette étiquette est déjà clôturée.'))
        self.write({'statut': statut, 'date_cloture': fields.Datetime.now()})

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
            rec.access_url = '/haccp/etiquette/%s/%s' % (rec.id, rec.access_token or '')
