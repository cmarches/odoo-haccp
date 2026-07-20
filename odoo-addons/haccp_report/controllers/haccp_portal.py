import logging
from datetime import timedelta

from odoo import fields, http, _
from odoo.http import request
from werkzeug.exceptions import Forbidden, NotFound

from odoo.addons.haccp_report.models.haccp_dlc_table import (
    DLC_TABLE, DLC_FAMILLE_SELECTION, DLC_CONDITION_SELECTION,
)
from odoo.addons.haccp_report.models.zpl_printer import build_zpl, send_zpl

_logger = logging.getLogger(__name__)


def _parse_product_id(value):
    """Convertit product_id en int, ou False si absent/non numérique
    (une requête forgée pourrait envoyer une valeur non numérique)."""
    try:
        return int(value) if value else False
    except ValueError:
        return False


class HaccpPortalController(http.Controller):

    def _check_kitchen_group(self):
        if request.env.user._is_public() or not request.env.user.has_group(
            'haccp_report.group_haccp_kitchen'
        ):
            raise Forbidden()

    def _get_record_or_404(self, ouverture_id, access_token):
        record = request.env['haccp.dlc.ouverture'].sudo().browse(ouverture_id)
        if not record.exists() or not record.access_token or record.access_token != access_token:
            raise NotFound()
        return record

    @http.route('/haccp/etiquette/nouvelle', type='http', auth='user', methods=['GET'], csrf=False)
    def haccp_etiquette_form(self, error=None, **kwargs):
        self._check_kitchen_group()
        products = request.env['product.template'].sudo().search(
            [('categ_id.name', '=', 'Alimentaire')], limit=200
        )
        famille = kwargs.get('famille') or 'autre'
        condition = kwargs.get('condition') or 'refrigere'
        duree_jours = DLC_TABLE.get((famille, condition), 0)
        date_ouverture = kwargs.get('date_ouverture') or fields.Date.today().isoformat()
        try:
            parsed_date = fields.Date.from_string(date_ouverture)
        except ValueError:
            date_ouverture = fields.Date.today().isoformat()
            parsed_date = fields.Date.today()
        date_limite = None
        if duree_jours:
            date_limite = (parsed_date + timedelta(days=duree_jours)).isoformat()

        return request.render('haccp_report.portal_etiquette_form', {
            'products': products,
            'famille_options': DLC_FAMILLE_SELECTION,
            'condition_options': DLC_CONDITION_SELECTION,
            'famille': famille,
            'condition': condition,
            'date_ouverture': date_ouverture,
            'product_name': kwargs.get('product_name', ''),
            'selected_product_id': _parse_product_id(kwargs.get('product_id')),
            'duree_jours': duree_jours,
            'date_limite': date_limite,
            'user_name': request.env.user.name,
            'error': error,
            'csrf_token': request.csrf_token(),
        })

    @http.route('/haccp/etiquette/nouvelle', type='http', auth='user', methods=['POST'], csrf=True)
    def haccp_etiquette_submit(self, **post):
        self._check_kitchen_group()

        product_id = _parse_product_id(post.get('product_id'))
        product_name = post.get('product_name') or ''
        if product_id:
            product_name = request.env['product.template'].sudo().browse(product_id).name

        if not product_name or not post.get('famille') or not post.get('condition'):
            return self.haccp_etiquette_form(
                error=_('Merci de renseigner le produit, la famille et la condition.'),
                **post,
            )

        record = request.env['haccp.dlc.ouverture'].sudo().create({
            'product_id': product_id,
            'product_name': product_name,
            'famille': post['famille'],
            'condition': post['condition'],
            'date_ouverture': post.get('date_ouverture') or fields.Datetime.now(),
            'operateur_id': request.env.user.id,
        })

        return self._print_and_render(record)

    def _print_and_render(self, record):
        printer_ip = request.env['ir.config_parameter'].sudo().get_param(
            'haccp_report.zebra_printer_ip'
        )
        portal_url = request.httprequest.host_url.rstrip('/') + record.access_url
        zpl = build_zpl(
            reference=record.reference,
            product_name=record.product_name,
            date_ouverture=record.date_ouverture,
            operateur_name=record.operateur_id.name,
            date_limite=record.date_limite,
            duree_jours=record.duree_jours,
            condition_label=dict(DLC_CONDITION_SELECTION).get(record.condition, record.condition),
            portal_url=portal_url,
        )
        ok, error = send_zpl(zpl, printer_ip)
        if not ok:
            _logger.warning('Échec impression étiquette %s : %s', record.reference, error)
        return request.render('haccp_report.portal_etiquette_confirmation', {
            'record': record, 'print_ok': ok, 'print_error': error,
            'csrf_token': request.csrf_token(),
        })

    @http.route(
        '/haccp/etiquette/<int:ouverture_id>/<string:access_token>/reessayer',
        type='http', auth='user', methods=['POST'], csrf=True,
    )
    def haccp_etiquette_reessayer(self, ouverture_id, access_token, **post):
        self._check_kitchen_group()
        record = self._get_record_or_404(ouverture_id, access_token)
        return self._print_and_render(record)

    @http.route(
        '/haccp/etiquette/<int:ouverture_id>/<string:access_token>',
        type='http', auth='public', methods=['GET'],
    )
    def haccp_etiquette_view(self, ouverture_id, access_token, **kwargs):
        record = self._get_record_or_404(ouverture_id, access_token)
        can_close = (
            not request.env.user._is_public()
            and request.env.user.has_group('haccp_report.group_haccp_kitchen')
        )
        return request.render('haccp_report.portal_etiquette_view', {
            'record': record,
            'can_close': can_close,
            'csrf_token': request.csrf_token(),
        })

    @http.route(
        '/haccp/etiquette/<int:ouverture_id>/<string:access_token>/cloturer',
        type='http', auth='user', methods=['POST'], csrf=True,
    )
    def haccp_etiquette_cloturer(self, ouverture_id, access_token, statut=None, **post):
        self._check_kitchen_group()
        record = self._get_record_or_404(ouverture_id, access_token)
        if statut in ('termine', 'jete'):
            record.action_cloturer(statut)
        return request.redirect(record.access_url)
