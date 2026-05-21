from odoo import api, fields, models
from odoo.tools.translate import _


class HaccpReport(models.Model):
    _name = 'haccp.report'
    _description = 'Rapport HACCP DDPP'
    _order = 'date_start desc'

    name = fields.Char(
        string='Référence',
        compute='_compute_name',
        store=True,
    )
    date_start = fields.Date(string='Date de début', required=True)
    date_end = fields.Date(string='Date de fin', required=True)
    responsible_id = fields.Many2one(
        'res.users',
        string='Responsable qualité',
        required=True,
        default=lambda self: self.env.user,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company,
    )
    state = fields.Selection(
        [('draft', 'Brouillon'), ('generated', 'Généré')],
        string='État',
        default='draft',
        required=True,
    )
    check_count = fields.Integer(
        string='Nb mesures',
        compute='_compute_counts',
        readonly=True,
    )
    alert_count = fields.Integer(
        string='Nb alertes',
        compute='_compute_counts',
        readonly=True,
    )

    @api.depends('date_start', 'date_end')
    def _compute_name(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                start = rec.date_start.strftime('%d/%m/%Y')
                end = rec.date_end.strftime('%d/%m/%Y')
                rec.name = f'Rapport HACCP DDPP – {start} → {end}'
            else:
                rec.name = _('Nouveau rapport HACCP')

    def _get_date_domain_dt(self):
        """Return (date_start_dt, date_end_dt) as datetimes for domain filters."""
        self.ensure_one()
        date_start_dt = fields.Datetime.to_datetime(self.date_start)
        date_end_dt = fields.Datetime.to_datetime(self.date_end).replace(
            hour=23, minute=59, second=59  # NOTE: UTC-only deployment assumed
        )
        return date_start_dt, date_end_dt

    @api.depends('date_start', 'date_end')
    def _compute_counts(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                start_dt, end_dt = rec._get_date_domain_dt()
                rec.check_count = self.env['quality.check'].search_count([
                    ('create_date', '>=', start_dt),
                    ('create_date', '<=', end_dt),
                ])
                rec.alert_count = self.env['quality.alert'].search_count([
                    ('create_date', '>=', start_dt),
                    ('create_date', '<=', end_dt),
                ])
            else:
                rec.check_count = 0
                rec.alert_count = 0

    def action_print_report(self):
        self.ensure_one()
        result = self.env.ref('haccp_report.action_report_haccp_ddpp').report_action(self)
        self.write({'state': 'generated'})
        return result

    def action_view_checks(self):
        self.ensure_one()
        start_dt, end_dt = self._get_date_domain_dt()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Contrôles qualité',
            'res_model': 'quality.check',
            'view_mode': 'list,form',
            'domain': [
                ('create_date', '>=', fields.Datetime.to_string(start_dt)),
                ('create_date', '<=', fields.Datetime.to_string(end_dt)),
            ],
        }

    def action_view_alerts(self):
        self.ensure_one()
        start_dt, end_dt = self._get_date_domain_dt()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Alertes qualité',
            'res_model': 'quality.alert',
            'view_mode': 'list,form',
            'domain': [
                ('create_date', '>=', fields.Datetime.to_string(start_dt)),
                ('create_date', '<=', fields.Datetime.to_string(end_dt)),
            ],
        }
