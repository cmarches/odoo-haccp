from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .haccp_dlc_table import DLC_TABLE, DLC_FAMILLE_SELECTION, DLC_CONDITION_SELECTION


class HaccpDlcOuverture(models.Model):
    _name = 'haccp.dlc.ouverture'
    _description = 'Ouverture DLC secondaire (étiquette cuisine)'
    _inherit = ['portal.mixin', 'mail.thread']
    _order = 'date_ouverture desc'
    _rec_name = 'reference'

    reference = fields.Char(
        string='Référence', required=True, copy=False, readonly=True, default='Nouveau'
    )
    product_id = fields.Many2one('product.template', string='Produit (catalogue)')
    lot_id = fields.Many2one(
        'stock.lot', string='Lot Odoo', copy=False, readonly=True
    )
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
    date_limite_produit_origine = fields.Date(
        string='DLC produit (origine)', compute='_compute_dlc', store=True
    )
    statut = fields.Selection([
        ('ouvert', 'Ouvert'),
        ('termine', 'Terminé'),
        ('jete', 'Jeté'),
    ], string='Statut', default='ouvert', required=True, readonly=True, tracking=True)
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

    def _find_available_lots(self, product_template):
        return self.env['stock.lot'].search([
            ('product_id.product_tmpl_id', '=', product_template.id),
            ('product_qty', '>', 0),
        ])

    def _create_lot_for_product(self, product_template, name):
        variant = product_template.product_variant_id
        return self.env['stock.lot'].create({
            'name': name,
            'product_id': variant.id,
            'company_id': self.env.company.id,
        })

    def _resolve_lot(self, product_template):
        """Retourne un dict décrivant comment le lot a été résolu pour ce
        produit :
        - {'status': 'single', 'lot': <stock.lot>} : un seul lot disponible,
          sélectionné automatiquement.
        - {'status': 'ambiguous', 'candidates': <stock.lot recordset>} :
          plusieurs lots disponibles, l'appelant doit demander à l'utilisateur
          de choisir.
        - {'status': 'created', 'lot': <stock.lot>, 'reference': str} : aucun
          lot disponible, un nouveau lot a été créé avec pour nom la
          référence générée (à réutiliser telle quelle pour l'enregistrement
          haccp.dlc.ouverture, pour éviter toute divergence)."""
        lots = self._find_available_lots(product_template)
        if len(lots) == 1:
            return {'status': 'single', 'lot': lots}
        if len(lots) > 1:
            return {'status': 'ambiguous', 'candidates': lots}
        reference = self.env['ir.sequence'].next_by_code('haccp.dlc.ouverture') or 'Nouveau'
        lot = self._create_lot_for_product(product_template, reference)
        return {'status': 'created', 'lot': lot, 'reference': reference}

    # La dépendance porte volontairement sur `lot_id` et non sur
    # `lot_id.expiration_date` : ce dernier champ n'existe que si le module
    # optionnel `product_expiry` est installé, et référencer un champ
    # potentiellement inexistant dans `@api.depends` casserait le chargement
    # du module en son absence. Conséquence : modifier `expiration_date` sur
    # un lot déjà lié à un enregistrement existant ne recalculera PAS
    # rétroactivement `date_limite`/`date_limite_produit_origine` de cet
    # enregistrement — seule la création d'un nouvel enregistrement (ou une
    # nouvelle écriture sur `lot_id`/`famille`/`condition`/`date_ouverture`)
    # déclenche le recalcul.
    @api.depends('famille', 'condition', 'date_ouverture', 'lot_id')
    def _compute_dlc(self):
        use_native_expiry = self.env['ir.config_parameter'].sudo().get_param(
            'haccp_report.use_native_expiry'
        ) == 'True'
        lot_has_expiry_field = 'expiration_date' in self.env['stock.lot']._fields
        for rec in self:
            duree = DLC_TABLE.get((rec.famille, rec.condition), 0)
            rec.duree_jours = duree
            date_limite = False
            if rec.date_ouverture and duree:
                date_limite = rec.date_ouverture.date() + timedelta(days=duree)

            date_origine = False
            if use_native_expiry and rec.lot_id and lot_has_expiry_field:
                expiration_date = rec.lot_id.expiration_date
                if expiration_date:
                    date_origine = (
                        expiration_date.date()
                        if hasattr(expiration_date, 'date')
                        else expiration_date
                    )
                    if date_limite and date_limite > date_origine:
                        date_limite = date_origine

            rec.date_limite = date_limite
            rec.date_limite_produit_origine = date_origine

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
        self.message_post(body=_('Étiquette clôturée : %s') % dict(self._fields['statut'].selection)[statut])

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
            rec.access_url = '/haccp/etiquette/%s/%s' % (rec.id, rec.access_token or '')
