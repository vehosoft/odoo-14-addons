# Copyright VeHoSoft - Vertical & Horizontal Software (http://www.vehosoft.com)
# Code by: Francisco Rodriguez (frodriguez@vehosoft.com).

from odoo import api, fields, exceptions, models, tools, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
from lxml import etree
import json
import qrcode
import base64
import tempfile
import logging
_logger = logging.getLogger(__name__)
from datetime import datetime
import pytz

try:
    import zeep
except ImportError:  # pragma: no cover
    _logger.debug('Cannot import zeep')

class PosOrder(models.Model):
    _inherit = 'pos.order'
    cfdi_ticket_state = fields.Selection([('pending', 'Pendiente'), ('sync', 'Registrado'), ('done', 'Timbrado')], string='Status del Ticket CFDI', default='pending', copy=False, readonly=True)
    cfdi_ticket_codigo = fields.Char(string='Ticke Codigo', size=15, default= '', copy=False, readonly=True)
    cfdi_ticket_id = fields.Char(string='FacturaTool TickeID', size=30, copy=False, readonly=True)
    cfdi_ticket_calls = fields.Integer(string="Intentos de Creacion del Ticket", default=0 ,readonly=True)
    cfdi_ticket_call_error = fields.Char(string="Error WS FacturaTool", size=120, default='' ,readonly=True)
    cfdi_factura_id = fields.Char(string='FacturaTool FacturaID', size=30, copy=False, readonly=True)
    #cfdi_factura_global = fields.Boolean(string="Factura Global", default=False ,readonly=True)

    #def action_pos_order_invoice(self):
    #    moves = self.env['account.move']
    #    wsdl = 'http://ws.facturatool.com/index.php?wsdl'
    #    client = zeep.Client(wsdl)
    #    for order in self:
    #        #Si el Pedido esta sincronizado al Portal de Cliente
    #        if order.cfdi_ticket_state == 'sync':
    #            ft_account = self.env['facturatool.account'].search([('rfc','!=',''),('company_id','=',order.company_id.id)], limit=1)
    #            params = {
    #                'Rfc': ft_account.rfc,
    #                'Usuario': ft_account.username,
    #                'Password': ft_account.password,
    #                'TransID': order.cfdi_ticket_id
    #            }
    #            _logger.debug('===== action_pos_order_invoice statusTicket params = %r',params)
    #            result = client.service.statusTicket(params=params)
    #            _logger.debug('===== action_pos_order_invoice statusTicket result = %r',result)
    #            ws_res = json.loads(result)
    #            _logger.debug('===== action_pos_order_invoice statusTicket ws_res = %r',ws_res)
    #            if ws_res['success'] == True:
    #                #Si el Pedido ya fue timbrado en el Portal de Cliente
    #                if ws_res['state'] == 'done':
    #                    order.write({
    #                        'cfdi_ticket_state': 'done',
    #                        'cfdi_factura_id': ws_res['factura_id']
    #                    })
    #                    msg = 'El pedido '+order.name+' ya ha sido facturado desde el Poral de Clientes'
    #                    raise Warning(msg)
    #                    return {'msg': msg,'status': False}
    #    
    #    resp = super().action_pos_order_invoice()
    #    _logger.debug('===== action_pos_order_invoice resp = %r',resp)
    #    for order in self:
    #        #Si el Pedido esta sincronizado al Portal de Cliente y se Timbra el CFDI desde Odoo
    #        if order.cfdi_ticket_state == 'sync' and order.account_move and order.account_move.cfdi_state == 'done':
    #            #Actualiza el status del Pedido
    #            order.write({
    #                'cfdi_ticket_state': 'done',
    #                'cfdi_factura_id': order.account_move.cfdi_trans_id
    #            })
    #            #Actualiza el status del Ticket en el Portal de Clientes
    #            ft_account = self.env['facturatool.account'].search([('rfc','!=',''),('company_id','=',order.company_id.id)], limit=1)
    #            params = {
    #                'Rfc': ft_account.rfc,
    #                'Usuario': ft_account.username,
    #                'Password': ft_account.password,
    #                'TransID': order.cfdi_ticket_id,
    #                'State': 'done',
    #                'FacturaID': order.account_move.cfdi_trans_id
    #            }
    #            _logger.debug('===== action_pos_order_invoice actualizarTicket params = %r',params)
    #            result = client.service.actualizarTicket(params=params)
    #            _logger.debug('===== action_pos_order_invoice actualizarTicket result = %r',result)
    #            ws_res = json.loads(result)
    #            _logger.debug('===== action_pos_order_invoice actualizarTicket ws_res = %r',ws_res)
    #    return resp

    @api.model
    def _order_fields(self, ui_order):
        vals = order_id = super()._order_fields(ui_order)
        cfdi_ticket_codigo = ''
        if 'cfdi_ticket_codigo' in ui_order:
            cfdi_ticket_codigo = ui_order['cfdi_ticket_codigo']
        vals['cfdi_ticket_codigo'] = cfdi_ticket_codigo
        _logger.debug('===== _order_fields vals = %r',vals)
        return vals

    def action_send_order_to_facturatool(self):
        wsdl = 'http://ws.facturatool.com/index.php?wsdl'
        client = zeep.Client(wsdl)
        for pos_order in self:
            ft_account = self.env['facturatool.account'].search([('rfc','!=',''),('company_id','=',pos_order.company_id.id)], limit=1)
            if ft_account.rfc != False:
                _logger.debug('===== action_send_order_to_facturatool pos_order.name = %r',pos_order.name)
                
                conceptos = []
                taxes = []
                iline = 0
                itax = 0
                discount=0.00
                for line in pos_order.lines:
                    _logger.debug('===== action_send_order_to_facturatool line.display_name = %r',line.display_name)
                    _logger.debug('===== action_send_order_to_facturatool line.tax_ids = %r',line.tax_ids)
                    _logger.debug('===== action_send_order_to_facturatool line.tax_ids_after_fiscal_position = %r',line.tax_ids_after_fiscal_position)
                    tax_include_on_price = False
                    for tax in line.tax_ids:
                        factor_tax = 1.00
                        if tax.amount < 0.00:
                            factor_tax = -1.00
                        if tax.amount_type=='percent' and tax.type_tax_sat != False:
                            tax_obj = {
                                'Nombre': tax.name,
                                'Tipo': tax.type_tax_sat,
                                'Impuesto': tax.clave_sat,
                                'Base': line.price_subtotal,
                                'TipoFactor': tax.tipo_factor_sat,
                                'TasaOCuota': (float(tax.amount)/100.00) * factor_tax,
                                'Importe': float(line.price_subtotal) * (float(tax.amount)/100.00) * factor_tax,
                                'indexConcepto': iline
                            }
                            taxes[itax:itax]=[tax_obj]
                        itax = itax + 1
                        if tax.price_include:
                            tax_include_on_price = True
                    ValorUnitario = line.price_unit
                    if tax_include_on_price:
                        ValorUnitario = float(line.price_subtotal) / float(line.qty)
                    
                    concepto = {
                        'ClaveProdServ': line.product_id.clave_sat.code,
                        'Cantidad': line.qty,
                        'Descripcion': line.display_name,
                        'ClaveUnidad': line.product_uom_id.clave_sat,
                        'Unidad': line.product_uom_id.name,
                        'ValorUnitario': ValorUnitario,
                        'Importe': line.price_subtotal,
                        'indexConcepto': iline
                    }
                    
                    #if line.discount > 0:
                    #    discount = discount + line.discount
                    #    concepto['Descuento'] = line.discount

                    conceptos[iline:iline]=[concepto]
                    iline = iline + 1
                
                #Obtener la forma de pago
                cfdi_forma_pago = '99'
                payment_amount = 0.00
                for payment in pos_order.payment_ids:
                    if payment.amount > payment_amount:
                        cfdi_forma_pago = payment.payment_method_id.cfdi_forma_pago.code or cfdi_forma_pago
                        payment_amount = payment.amount
                
                params = {
                    'Rfc': ft_account.rfc,
                    'Usuario': ft_account.username,
                    'Password': ft_account.password,
                    'Fecha': pos_order.date_order.strftime("%Y-%m-%d %H:%M"),
                    'Codigo': pos_order.cfdi_ticket_codigo,
                    'FormaPago': cfdi_forma_pago,
                    'Conceptos': conceptos,
                    'Moneda': 'MXN',#pos_order.currency_id.name, hasta que se implemente timbrado para monedas distintas a MXN
                    'SubTotal': float(pos_order.amount_total) - float(pos_order.amount_tax),
                    'Total': pos_order.amount_total,
                    'LugarExpedicion': pos_order.company_id.zip,
                    'IdExterno': pos_order.name+'_'+str(pos_order.id),
                }
                #if discount > 0.00:
                #    params['Descuento'] =  discount
                if len(taxes) > 0:
                    params['Impuestos'] =  taxes
                
                _logger.debug('===== action_send_order_to_facturatool crearTicket params = %r',params)
                result = client.service.crearTicket(params=params)
                _logger.debug('===== action_send_order_to_facturatool crearTicket result = %r',result)
                ws_res = json.loads(result)
                _logger.debug('===== action_send_order_to_facturatool crearTicket ws_res = %r',ws_res)

                if ws_res['success'] == True:
                    pos_order.write({
                        'cfdi_ticket_state':'sync',
                        'cfdi_ticket_id':ws_res['trans_id'],
                        'cfdi_ticket_calls': 0 #pos_order.cfdi_ticket_calls + 1,
                    })
                else:
                    if ws_res['error'] is None:
                        error = "Servicio temporalmente fuera de servicio"
                    else:
                        error = 'Error #' + str(ws_res['errno']) + ': ' + ws_res['error']
                    pos_order.write({
                        'cfdi_ticket_calls': pos_order.cfdi_ticket_calls + 1,
                        'cfdi_ticket_call_error': error
                    })

    def cron_send_pos_orders_to_facturatool(self):
        wsdl = 'http://ws.facturatool.com/index.php?wsdl'
        client = zeep.Client(wsdl)
        ft_accounts = {}

        cron_obj = self.env['ir.cron'].search([('name','=','Send POS Orders to FacturaTool Customer Panel')])[0]
        _logger.debug('===== cron_send_pos_orders_to_facturatool cron_obj.facturatool_count = %r',cron_obj.facturatool_count)
        #cron_obj = self.env['ir.cron'].browse(int(cron_id))
        last_order_id = cron_obj.facturatool_count
        _logger.debug('===== cron_send_pos_orders_to_facturatool last_order_id = %r',last_order_id)

        pos_orders = self.env['pos.order'].search([('id','>',last_order_id),('cfdi_ticket_codigo','!=',''),('cfdi_ticket_state','=','pending')], limit=30, order='id asc')
        _logger.debug('===== cron_send_pos_orders_to_facturatool len(pos_orders) = %r',len(pos_orders))

        for pos_order in pos_orders:
            if pos_order.company_id.id in ft_accounts:
                ft_account = ft_accounts[pos_order.company_id.id]
            else:
                ft_account = self.env['facturatool.account'].search([('rfc','!=',''),('company_id','=',pos_order.company_id.id)], limit=1)
                ft_accounts[pos_order.company_id.id] = ft_account
            
            _logger.debug('===== cron_send_pos_orders_to_facturatool ft_account = %r',ft_account)
            _logger.debug('===== cron_send_pos_orders_to_facturatool pos_order.account_move = %r', pos_order.account_move.cfdi_state)
            
            if ft_account.rfc != False and pos_order.account_move.cfdi_state != 'done':
                _logger.debug('===== cron_send_pos_orders_to_facturatool pos_order.name = %r',pos_order.name)
                
                conceptos = []
                taxes = []
                iline = 0
                itax = 0
                discount=0
                for line in pos_order.lines:
                    _logger.debug('===== cron_send_pos_orders_to_facturatool line.display_name = %r',line.display_name)
                    _logger.debug('===== cron_send_pos_orders_to_facturatool line.tax_ids = %r',line.tax_ids)
                    _logger.debug('===== cron_send_pos_orders_to_facturatool line.tax_ids_after_fiscal_position = %r',line.tax_ids_after_fiscal_position)
                    tax_include_on_price = False
                    for tax in line.tax_ids:
                        factor_tax = 1.00
                        if tax.amount < 0.00:
                            factor_tax = -1.00
                        if tax.amount_type=='percent' and tax.type_tax_sat != False:
                            tax_obj = {
                                'Nombre': tax.name,
                                'Tipo': tax.type_tax_sat,
                                'Impuesto': tax.clave_sat,
                                'Base': line.price_subtotal,
                                'TipoFactor': tax.tipo_factor_sat,
                                'TasaOCuota': (float(tax.amount)/100.00) * factor_tax,
                                'Importe': float(line.price_subtotal) * (float(tax.amount)/100.00) * factor_tax,
                                'indexConcepto': iline
                            }
                            taxes[itax:itax]=[tax_obj]
                        itax = itax + 1
                        if tax.price_include:
                            tax_include_on_price = True
                    ValorUnitario = line.price_unit
                    if tax_include_on_price:
                        ValorUnitario = float(line.price_subtotal) / float(line.qty)
                    
                    concepto = {
                        'ClaveProdServ': line.product_id.clave_sat.code,
                        'Cantidad': line.qty,
                        'Descripcion': line.display_name,
                        'ClaveUnidad': line.product_uom_id.clave_sat,
                        'Unidad': line.product_uom_id.name,
                        'ValorUnitario': ValorUnitario,
                        'Importe': line.price_subtotal,
                        'indexConcepto': iline
                    }
                    
                    #if line.discount > 0:
                    #    discount = discount + line.discount
                    #    concepto['Descuento'] = line.discount

                    conceptos[iline:iline]=[concepto]
                    iline = iline + 1
                
                #Obtener la forma de pago
                cfdi_forma_pago = '99'
                payment_amount = 0.00
                for payment in pos_order.payment_ids:
                    if payment.amount > payment_amount:
                        cfdi_forma_pago = payment.payment_method_id.cfdi_forma_pago.code or cfdi_forma_pago
                        payment_amount = payment.amount
                
                params = {
                    'Rfc': ft_account.rfc,
                    'Usuario': ft_account.username,
                    'Password': ft_account.password,
                    'Fecha': pos_order.date_order.strftime("%Y-%m-%d %H:%M"),
                    'Codigo': pos_order.cfdi_ticket_codigo,
                    'FormaPago': cfdi_forma_pago,
                    'Conceptos': conceptos,
                    'Moneda': 'MXN',#pos_order.currency_id.name, hasta que se implemente timbrado para monedas distintas a MXN
                    'SubTotal': float(pos_order.amount_total) - float(pos_order.amount_tax),
                    'Total': pos_order.amount_total,
                    'LugarExpedicion': pos_order.company_id.zip,
                    'IdExterno': pos_order.name+'_'+str(pos_order.id),
                }
                if len(taxes) > 0:
                    params['Impuestos'] =  taxes
                
                _logger.debug('===== cron_send_pos_orders_to_facturatool crearTicket params = %r',params)
                result = client.service.crearTicket(params=params)
                _logger.debug('===== cron_send_pos_orders_to_facturatool crearTicket result = %r',result)
                ws_res = json.loads(result)
                _logger.debug('===== cron_send_pos_orders_to_facturatool crearTicket ws_res = %r',ws_res)

                if ws_res['success'] == True:
                    pos_order.write({
                        'cfdi_ticket_state':'sync',
                        'cfdi_ticket_id':ws_res['trans_id'],
                        'cfdi_ticket_calls':0 #pos_order.cfdi_ticket_calls + 1,
                    })
                else:
                    if ws_res['error'] is None:
                        error = "Servicio temporalmente fuera de servicio"
                    else:
                        error = 'Error #' + str(ws_res['errno']) + ': ' + ws_res['error']
                    pos_order.write({
                        'cfdi_ticket_calls': pos_order.cfdi_ticket_calls + 1,
                        'cfdi_ticket_call_error': error
                    })
                
                #Incremente last_order_id aunque la sincronizacion falle
                if pos_order.id > last_order_id:
                    last_order_id = pos_order.id

            elif pos_order.account_move.cfdi_state == 'done':
                pos_order.write({
                    'cfdi_ticket_state':'done',
                    'cfdi_ticket_calls': 0,
                    'cfdi_factura_id': pos_order.account_move.cfdi_trans_id
                })

        _logger.debug('===== cron_send_pos_orders_to_facturatool NEW last_order_id = %r',last_order_id)
        #Si el nuevo last_order_id es mayor al inicial
        if last_order_id > cron_obj.facturatool_count:
            cron_obj.write({
                'facturatool_count': last_order_id
            })
        
    def cron_resend_pos_orders_to_facturatool(self):
        wsdl = 'http://ws.facturatool.com/index.php?wsdl'
        client = zeep.Client(wsdl)
        ft_accounts = {}

        pos_orders = self.env['pos.order'].search([('cfdi_ticket_codigo','!=',''),('cfdi_ticket_state','=','pending'),('cfdi_ticket_calls','<=',5)], limit=30, order='id desc')
        _logger.debug('===== cron_resend_pos_orders_to_facturatool len(pos_orders) = %r',len(pos_orders))

        for pos_order in pos_orders:
            if pos_order.company_id.id in ft_accounts:
                ft_account = ft_accounts[pos_order.company_id.id]
            else:
                ft_account = self.env['facturatool.account'].search([('rfc','!=',''),('company_id','=',pos_order.company_id.id)], limit=1)
                ft_accounts[pos_order.company_id.id] = ft_account
            
            #_logger.debug('===== cron_resend_pos_orders_to_facturatool ft_account = %r',ft_account)
            _logger.debug('===== cron_resend_pos_orders_to_facturatool pos_order.account_move = %r', pos_order.account_move.cfdi_state)
            
            if ft_account.rfc != False and pos_order.account_move.cfdi_state != 'done':
                _logger.debug('===== cron_resend_pos_orders_to_facturatool pos_order.name = %r',pos_order.name)
                
                conceptos = []
                taxes = []
                iline = 0
                itax = 0
                discount=0
                for line in pos_order.lines:
                    _logger.debug('===== cron_resend_pos_orders_to_facturatool line.display_name = %r',line.display_name)
                    _logger.debug('===== cron_resend_pos_orders_to_facturatool line.tax_ids = %r',line.tax_ids)
                    _logger.debug('===== cron_resend_pos_orders_to_facturatool line.tax_ids_after_fiscal_position = %r',line.tax_ids_after_fiscal_position)
                    tax_include_on_price = False
                    for tax in line.tax_ids:
                        factor_tax = 1.00
                        if tax.amount < 0.00:
                            factor_tax = -1.00
                        if tax.amount_type=='percent' and tax.type_tax_sat != False:
                            tax_obj = {
                                'Nombre': tax.name,
                                'Tipo': tax.type_tax_sat,
                                'Impuesto': tax.clave_sat,
                                'Base': line.price_subtotal,
                                'TipoFactor': tax.tipo_factor_sat,
                                'TasaOCuota': (float(tax.amount)/100.00) * factor_tax,
                                'Importe': float(line.price_subtotal) * (float(tax.amount)/100.00) * factor_tax,
                                'indexConcepto': iline
                            }
                            taxes[itax:itax]=[tax_obj]
                        itax = itax + 1
                        if tax.price_include:
                            tax_include_on_price = True
                    ValorUnitario = line.price_unit
                    if tax_include_on_price:
                        ValorUnitario = float(line.price_subtotal) / float(line.qty)
                    
                    concepto = {
                        'ClaveProdServ': line.product_id.clave_sat.code,
                        'Cantidad': line.qty,
                        'Descripcion': line.display_name,
                        'ClaveUnidad': line.product_uom_id.clave_sat,
                        'Unidad': line.product_uom_id.name,
                        'ValorUnitario': ValorUnitario,
                        'Importe': line.price_subtotal,
                        'indexConcepto': iline
                    }
                    
                    #if line.discount > 0:
                    #    discount = discount + line.discount
                    #    concepto['Descuento'] = line.discount

                    conceptos[iline:iline]=[concepto]
                    iline = iline + 1
                
                #Obtener la forma de pago
                cfdi_forma_pago = '99'
                payment_amount = 0.00
                for payment in pos_order.payment_ids:
                    if payment.amount > payment_amount:
                        cfdi_forma_pago = payment.payment_method_id.cfdi_forma_pago.code or cfdi_forma_pago
                        payment_amount = payment.amount
                
                params = {
                    'Rfc': ft_account.rfc,
                    'Usuario': ft_account.username,
                    'Password': ft_account.password,
                    'Fecha': pos_order.date_order.strftime("%Y-%m-%d %H:%M"),
                    'Codigo': pos_order.cfdi_ticket_codigo,
                    'FormaPago': cfdi_forma_pago,
                    'Conceptos': conceptos,
                    'Moneda': 'MXN',#pos_order.currency_id.name, hasta que se implemente timbrado para monedas distintas a MXN
                    'SubTotal': float(pos_order.amount_total) - float(pos_order.amount_tax),
                    'Total': pos_order.amount_total,
                    'LugarExpedicion': pos_order.company_id.zip,
                    'IdExterno': pos_order.name+'_'+str(pos_order.id),
                }
                if len(taxes) > 0:
                    params['Impuestos'] =  taxes
                
                _logger.debug('===== cron_resend_pos_orders_to_facturatool crearTicket params = %r',params)
                result = client.service.crearTicket(params=params)
                _logger.debug('===== cron_resend_pos_orders_to_facturatool crearTicket result = %r',result)
                ws_res = json.loads(result)
                _logger.debug('===== cron_resend_pos_orders_to_facturatool crearTicket ws_res = %r',ws_res)

                if ws_res['success'] == True:
                    pos_order.write({
                        'cfdi_ticket_state':'sync',
                        'cfdi_ticket_id':ws_res['trans_id'],
                        'cfdi_ticket_calls':0 #pos_order.cfdi_ticket_calls + 1,
                    })
                else:
                    if ws_res['error'] is None:
                        error = "Servicio temporalmente fuera de servicio"
                    else:
                        error = 'Error #' + str(ws_res['errno']) + ': ' + ws_res['error']
                    pos_order.write({
                        'cfdi_ticket_calls': pos_order.cfdi_ticket_calls + 1,
                        'cfdi_ticket_call_error': error
                    })

            elif pos_order.account_move.cfdi_state == 'done':
                pos_order.write({
                    'cfdi_ticket_state':'done',
                    'cfdi_ticket_calls': 0,
                    'cfdi_factura_id': pos_order.account_move.cfdi_trans_id
                })
    
    def cron_update_pos_orders_vs_facturatool(self):
        wsdl = 'http://ws.facturatool.com/index.php?wsdl'
        client = zeep.Client(wsdl)
        ft_accounts = {}

        cron_obj = self.env['ir.cron'].search([('name','=','Update POS Orders vs FacturaTool Customer Panel')])[0]
        _logger.debug('===== cron_update_pos_orders_vs_facturatool cron_obj.facturatool_count = %r',cron_obj.facturatool_count)
        last_order_id = cron_obj.facturatool_count
        _logger.debug('===== cron_update_pos_orders_vs_facturatool last_order_id = %r',last_order_id)

        pos_orders = self.env['pos.order'].search([('cfdi_ticket_state','=','sync')], limit=50, order='cfdi_ticket_calls asc')
        _logger.debug('===== cron_update_pos_orders_vs_facturatool len(pos_orders) = %r',len(pos_orders))

        for pos_order in pos_orders:
            if pos_order.company_id.id in ft_accounts:
                ft_account = ft_accounts[pos_order.company_id.id]
            else:
                ft_account = self.env['facturatool.account'].search([('rfc','!=',''),('company_id','=',pos_order.company_id.id)], limit=1)
                ft_accounts[pos_order.company_id.id] = ft_account
            
            _logger.debug('===== cron_update_pos_orders_vs_facturatool ft_account = %r',ft_account)
            _logger.debug('===== cron_update_pos_orders_vs_facturatool pos_order.account_move = %r', pos_order.account_move.cfdi_state)
            
            if ft_account.rfc != False and pos_order.account_move.cfdi_state != 'done':
                _logger.debug('===== cron_update_pos_orders_vs_facturatool pos_order.name = %r',pos_order.name)
                
                params = {
                    'Rfc': ft_account.rfc,
                    'Usuario': ft_account.username,
                    'Password': ft_account.password,
                    'TransID': pos_order.cfdi_ticket_id,
                }
                _logger.debug('===== cron_update_pos_orders_vs_facturatool statusTicket params = %r',params)
                result = client.service.statusTicket(params=params)
                _logger.debug('===== cron_update_pos_orders_vs_facturatool statusTicket result = %r',result)
                ws_res = json.loads(result)
                _logger.debug('===== cron_update_pos_orders_vs_facturatool statusTicket ws_res = %r',ws_res)

                if ws_res['success'] == True:
                    #Si el ticket ya fue timbrado por el cliente
                    if ws_res['state'] == 'done':
                        pos_order.write({
                            'cfdi_ticket_state':'done',
                            'cfdi_ticket_calls': 0,
                            'cfdi_factura_id': ws_res['factura_id'],
                        })
                    else:
                        pos_order.write({
                            'cfdi_ticket_calls': pos_order.cfdi_ticket_calls + 1
                        })
                else:
                    if ws_res['error'] is None:
                        error = "Servicio temporalmente fuera de servicio"
                    else:
                        error = 'Error #' + str(ws_res['errno']) + ': ' + ws_res['error']
                    pos_order.write({
                        'cfdi_ticket_calls': pos_order.cfdi_ticket_calls + 1,
                        'cfdi_ticket_call_error': error
                    })
            elif pos_order.account_move.cfdi_state == 'done':
                pos_order.write({
                    'cfdi_ticket_state':'done',
                    'cfdi_ticket_calls': 0,
                    'cfdi_factura_id': pos_order.account_move.cfdi_trans_id
                })

        _logger.debug('===== cron_send_pos_orders_to_facturatool NEW last_order_id = %r',last_order_id)