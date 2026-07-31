from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    haccp_use_native_expiry = fields.Boolean(
        string="Utiliser la DLC native Odoo (product_expiry)",
        config_parameter='haccp_report.use_native_expiry',
    )
    haccp_product_expiry_installed = fields.Boolean(
        string="Module product_expiry installé",
        compute='_compute_haccp_product_expiry_installed',
    )
    haccp_manifest_url = fields.Char(
        string="URL du manifeste de la bibliothèque HACCP",
        config_parameter='haccp_report.manifest_url',
    )

    def _compute_haccp_product_expiry_installed(self):
        installed = 'expiration_date' in self.env['stock.lot']._fields
        for rec in self:
            rec.haccp_product_expiry_installed = installed
