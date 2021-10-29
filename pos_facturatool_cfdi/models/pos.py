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
import qrcode
import io

class PosConfig(models.Model):
    _inherit = 'pos.config'

    cfdi_serie = fields.Many2one('facturatool.serie', string="Serie CFDI")

class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    cfdi_metodo_pago = fields.Selection([('PUE', 'Pago en una sola exhibicion'), ('PPD', 'Pago en parcialidades o diferido')], string='Metodo de Pago CFDI', default='PUE')
    cfdi_forma_pago = fields.Many2one('sat.forma.pago', string="Forma de Pago CFDI")

    @api.onchange('cfdi_metodo_pago')
    def _onchange_cfdi_metodo_pago(self):
        res = {}
        if self.cfdi_metodo_pago == 'PPD':
            fp_pd = self.env['sat.forma.pago'].search([('code','=','99')], limit=1)
            self.cfdi_forma_pago = fp_pd
        return res

class PosOrder(models.Model):
    _inherit = 'pos.order'
    cfdi_uso = fields.Many2one('sat.cfdi.uso', string="Uso del CFDI", readonly=True)

    @api.model
    def _order_fields(self, ui_order):
        vals = order_id = super()._order_fields(ui_order)
        cfdi_uso = False
        if 'uso_cfdi' in ui_order and ui_order['uso_cfdi']!='':
            cfdi_uso_exist = self.env['sat.cfdi.uso'].search([('code','=',ui_order['uso_cfdi'])], limit=1)
            if cfdi_uso_exist:
                cfdi_uso = cfdi_uso_exist.id
        vals['cfdi_uso'] = cfdi_uso
        _logger.debug('===== _order_fields vals = %r',vals)
        return vals
    
    def action_pos_order_invoice(self):
        try:
            resp = super().action_pos_order_invoice()
            _logger.debug('===== action_pos_order_invoice resp = %r',resp)
            for order in self:
                resp_cfdi = order.account_move.action_timbrar_cfdi()
                _logger.debug('===== action_pos_order_invoice resp_cfdi = %r',resp_cfdi)
            return resp
        except Exception as e:
            return {}
            pass
    
    def _prepare_invoice_line(self, order_line):
        vals = super()._prepare_invoice_line(order_line)
        vals['clave_sat'] = order_line.product_id.clave_sat.id or False
        _logger.debug('===== _prepare_invoice_line vals = %r',vals)
        return vals
    
    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()

        timezone = pytz.timezone(self._context.get('tz') or self.env.user.tz or 'UTC')
        date_order = self.date_order.astimezone(timezone)
        
        hora = float(date_order.strftime("%H"))
        #minuto = float(date_order.strftime("%M")) - 10.00 #Se le restan 10 minutos
        #minuto = minuto / 60.00
        #_logger.debug('===== _prepare_invoice_vals minuto = %r',minuto)

        #if int( (minuto * 60) * 10 ) > 60:
        #    minuto = minuto - 0.1
        minuto = 0.00

        cfdi_forma_pago = self.env['sat.forma.pago'].search([('code','=','99')], limit=1).id
        cfdi_metodo_pago = 'PUE'
        payment_amount = 0.00
        for payment in self.payment_ids:
            if payment.amount > payment_amount:
                _logger.debug('===== _prepare_invoice_vals payment.payment_method_id.cfdi_metodo_pago = %r',payment.payment_method_id.cfdi_metodo_pago)
                cfdi_metodo_pago = payment.payment_method_id.cfdi_metodo_pago
                cfdi_forma_pago = payment.payment_method_id.cfdi_forma_pago.id or False
                payment_amount = payment.amount
        
        cfdi_uso = self.cfdi_uso.id
        if cfdi_uso == False:
            cfdi_uso = self.partner_id.cfdi_uso.id
        vals['cfdi_uso'] = cfdi_uso
        vals['cfdi_fecha'] = date_order.strftime("%Y-%m-%d")
        vals['cfdi_hora'] = hora + minuto
        vals['cfdi_serie'] = self.session_id.config_id.cfdi_serie.id or False
        vals['cfdi_metodo_pago'] = cfdi_metodo_pago
        vals['cfdi_forma_pago'] = cfdi_forma_pago
        _logger.debug('===== _prepare_invoice_vals vals = %r',vals)
        return vals
    
    @api.model
    def create_from_ui(self, orders, draft=False):
        rec_orders = super().create_from_ui(orders, draft)
        new_rec_orders = []
        for rec_order in rec_orders:
            order = self.env['pos.order'].search_read(domain = [('id', '=', int(rec_order['id']))], fields = ['id', 'name', 'pos_reference','account_move'])[0]
            _logger.debug('===== create_from_ui order = %r',order)
            if order['account_move']:
                fields_invoice = ['id', 'name', 'cfdi_fecha_timbrado','cfdi_serie','cfdi_folio','cfdi_metodo_pago','cfdi_forma_pago','cfdi_uuid','cfdi_serie_csd','cfdi_serie_sat','cfdi_sello_digital','cfdi_sello_sat','cfdi_cadena_original']
                _logger.debug('===== create_from_ui order[account_move][0] = %r',order['account_move'][0])
                invoice = self.env['account.move'].search_read(domain = [('id', '=', int(order['account_move'][0]))], fields = fields_invoice)[0]
                order['account_move'] = invoice
            _logger.debug('===== create_from_ui order = %r',order)
            new_rec_orders.append(order)
        return new_rec_orders
    
    @api.model
    def get_invoice_data(self, order_ids):
        _logger.debug('===== get_invoice_data order_ids = %r',order_ids)
        orders = []
        for order_id in order_ids:
            order = self.env['pos.order'].search_read(domain = [('id', '=', int(order_id))], fields = ['id', 'name', 'pos_reference','account_move'])[0]
            _logger.debug('===== get_invoice_data order = %r',order)
            if order['account_move']:
                fields_invoice = ['id', 'name', 'cfdi_fecha_timbrado','cfdi_serie','cfdi_folio','cfdi_metodo_pago','cfdi_forma_pago','cfdi_uuid','cfdi_serie_csd','cfdi_serie_sat','cfdi_sello_digital','cfdi_sello_sat','cfdi_cadena_original']
                _logger.debug('===== get_invoice_data order[account_move][0] = %r',order['account_move'][0])
                invoice = self.env['account.move'].browse(int(order['account_move'][0]))
                _logger.debug('===== get_invoice_data invoice = %r',invoice)
                _logger.debug('===== get_invoice_data invoice.state = %r',invoice.cfdi_state)
                if invoice and invoice.cfdi_state == 'done':
                    order['account_move'] = {
                        'cfdi_fecha_timbrado':invoice.cfdi_fecha_timbrado,
                        'cfdi_serie':invoice.cfdi_serie.name,
                        'cfdi_folio':invoice.cfdi_folio,
                        'cfdi_metodo_pago':invoice.cfdi_metodo_pago,
                        'cfdi_forma_pago':invoice.cfdi_forma_pago.code+' - '+invoice.cfdi_forma_pago.name,
                        'cfdi_uuid':invoice.cfdi_uuid,
                        'cfdi_serie_csd':invoice.cfdi_serie_csd,
                        'cfdi_serie_sat':invoice.cfdi_serie_sat,
                        'cfdi_sello_digital':invoice.cfdi_sello_digital,
                        'cfdi_sello_sat':invoice.cfdi_sello_sat,
                        'cfdi_cadena_original':invoice.cfdi_cadena_original
                    }
                    order['account_move']['qr'] = self.make_base64_qr_code('https://verificacfdi.facturaelectronica.sat.gob.mx/default.aspx?id='+invoice[0]['cfdi_uuid']+'&re='+invoice.company_id.vat+'&rr='+invoice.partner_id.vat)
                else:
                    order['account_move'] = False
            _logger.debug('===== get_invoice_data order = %r',order)
            orders.append(order)
        return orders
    
    def make_base64_qr_code(self,data):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=4,
            border=4,
        )

        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image()

        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return img_str
    
    def action_receipt_to_customer(self, name, client, ticket):
        _logger.debug('===== action_receipt_to_customer self = %r',self)
        _logger.debug('===== action_receipt_to_customer name = %r',name)
        _logger.debug('===== action_receipt_to_customer client = %r',client)
        _logger.debug('===== action_receipt_to_customer self.mapped(account_move) = %r',self.mapped('account_move'))
        _logger.debug('===== action_receipt_to_customer self.ids[0] = %r',self.ids[0])
        _logger.debug('===== action_receipt_to_customer self.account_move = %r',self.account_move)

        if not self:
            return False
        if not client.get('email'):
            return False

        if self.mapped('account_move') and self.account_move.cfdi_state == 'done':
            message = "<p>Estimado %s,<br/>Esta es su factura %s %s (con referencia: %s). </p>" % (client['name'],self.account_move.cfdi_serie.name, self.account_move.cfdi_folio, name)
            filename = 'Ticket-' + name + '.jpg'
            receipt = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': ticket,
                'res_model': 'pos.order',
                'res_id': self.ids[0],
                'store_fname': filename,
                'mimetype': 'image/jpeg',
            })
            mail_values = {
                'subject': '%s - Factura %s %s (con referencia: %s)' % (self.account_move.company_id.name,self.account_move.cfdi_serie.name, self.account_move.cfdi_folio,name),
                'body_html': message,
                'author_id': self.env.user.partner_id.id,
                'email_from': self.env.company.email or self.env.user.email_formatted,
                'email_to': client['email'],
                'attachment_ids': [(4, receipt.id)],
            }
            ## PDF CFDI
            report = self.env.ref('point_of_sale.pos_invoice_report')._render_qweb_pdf(self.ids[0])
            filename = self.account_move.company_id.name +'_'+ self.account_move.cfdi_serie.name +''+ self.account_move.cfdi_folio
            attachment_pdf = self.env['ir.attachment'].create({
                'name': filename + '.pdf',
                'type': 'binary',
                'datas': base64.b64encode(report[0]),
                'store_fname': filename + '.pdf',
                'res_model': 'pos.order',
                'res_id': self.ids[0],
                'mimetype': 'application/x-pdf'
            })
            mail_values['attachment_ids'] += [(4, attachment_pdf.id)]
            ## XML CFDI
            attachment_xml = self.env['ir.attachment'].create({
                'name': filename + '.xml',
                'type': 'binary',
                'datas': base64.b64encode(self.account_move.cfdi_xml.encode('utf8')),
                'store_fname': filename + '.xml',
                'res_model': 'pos.order',
                'res_id': self.ids[0],
                'mimetype': 'application/x-pdf'
            })
            mail_values['attachment_ids'] += [(4, attachment_xml.id)]

            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.send()
        else:
            super().action_receipt_to_customer(name, client, ticket)