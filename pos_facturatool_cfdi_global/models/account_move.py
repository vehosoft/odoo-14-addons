# Copyright VeHoSoft - Vertical & Horizontal Software (http://www.vehosoft.com)
# Code by: Francisco Rodriguez (frodriguez@vehosoft.com).

from odoo import api, fields, exceptions, models, tools, _
import json
import logging
_logger = logging.getLogger(__name__)
try:
    import zeep
except ImportError:  # pragma: no cover
    _logger.debug('Cannot import zeep')

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    def _compute_cfdi_pos_order_count(self):
        for invoice in self:
            invoice.cfdi_pos_order_count = len(invoice.cfdi_pos_order_ids)

    cfdi_global = fields.Boolean(string="Factura Global", default=False ,readonly=True, copy=False)
    cfdi_pos_order_ids = fields.One2many('pos.order', 'cfdi_global_id', string='Pedidos Facturados', copy=True, readonly=True,
        states={'draft': [('readonly', False)]})
    cfdi_pos_order_count = fields.Integer(compute='_compute_cfdi_pos_order_count', string='# Pedidos Facturados')

    def action_timbrar_cfdi(self):
        invoices = self.filtered(lambda inv: inv.cfdi_state == 'draft')
        res = super(AccountMove, self).action_timbrar_cfdi()
        _logger.debug('===== action_timbrar_cfdi invoices = %r',invoices)
        ft_account = self.env['facturatool.account'].search([('rfc','!=',''),('company_id','=',invoices[0].company_id.id)], limit=1)
        client = False
        if ft_account.rfc != False and ft_account.rfc != '':
            wsdl = 'http://ws.facturatool.com/index.php?wsdl'
            client = zeep.Client(wsdl)

        for invoice in invoices:
            if invoice.cfdi_state == 'done' and invoice.cfdi_global == True:
                for pos_order in invoice.cfdi_pos_order_ids:
                    pos_order.write({
                        'cfdi_ticket_state':'done',
                        'cfdi_ticket_calls': 0,
                        'cfdi_factura_id': invoice.cfdi_trans_id,
                    })
                    if client:
                        params = {
                            'Rfc': ft_account.rfc,
                            'Usuario': ft_account.username,
                            'Password': ft_account.password,
                            'TransID': pos_order.cfdi_ticket_id,
                            'State': 'global',
                            'FacturaID': invoice.cfdi_trans_id,
                        }
                        _logger.debug('===== action_timbrar_cfdi actualizarTicket params = %r',params)
                        result = client.service.actualizarTicket(params=params)
                        _logger.debug('===== action_timbrar_cfdi actualizarTicket result = %r',result)
                        ws_res = json.loads(result)
                        _logger.debug('===== action_timbrar_cfdi actualizarTicket ws_res = %r',ws_res)
        return res