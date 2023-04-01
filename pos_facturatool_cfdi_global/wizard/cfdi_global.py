# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import datetime
import logging
_logger = logging.getLogger(__name__)

class CFDIGlobal(models.TransientModel):
    _name = 'cfdi.global.wizard'
    _description = 'CFDI Global of POS Orders'

    start_date = fields.Datetime(required=True, default=fields.Datetime.now)
    end_date = fields.Datetime(required=True, default=fields.Datetime.now)
    partner_id = fields.Many2one('res.partner', string='Cliente', domain=[('vat','=','XAXX010101000')], required=True, copy=False)
    payment_method_ids = fields.Many2many('pos.payment.method', 'pos_payment_methods',
        default=lambda s: s.env['pos.payment.method'].search([]))
    pos_order_ids = fields.Many2many('pos.order', 'pos_orders')

    @api.onchange('start_date')
    def _onchange_start_date(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            self.end_date = self.start_date

    @api.onchange('end_date')
    def _onchange_end_date(self):
        if self.end_date and self.end_date < self.start_date:
            self.start_date = self.end_date

    def load_orders(self):
        order_filters = [('date_order','>=',self.start_date),('date_order','<=',self.end_date),('cfdi_global','=',False),('cfdi_ticket_state','!=','done'),('state','in',['paid','done']),('amount_total','>',0.00)]
        orders = self.env['pos.order'].search(order_filters)
        method_ids = []
        for method in self.payment_method_ids:
            method_ids.append(method.id)
        order_ids = []
        for order in orders:
            _logger.debug('===== load_orders order.name = %r',order.name)
            if 'refund_order_ids' in order and len(order.refund_order_ids) > 0:
                continue
            for payment in order.payment_ids:
                if payment.payment_method_id.id in method_ids:
                    order_ids.append(order.id)
                    continue
        
        self.write({'pos_order_ids':[(6,0,order_ids)]})
        
        return {
            'view_mode': 'form',
            'view_id': False,
            'res_model': self._name,
            'res_id': self.id,
            'context': dict(self._context, active_ids=self.ids),
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def create_invoice(self):
        invoice_lines_obj={}
        invoice_lines=[]
        for order in self.pos_order_ids:
            for line in order.lines:
                index_line = str(line.product_id.id)+':'+str(line.price_unit)
                tax_ids = []
                for tax in line.tax_ids:
                    index_line += ':'+str(tax.id)
                    tax_ids.append(tax.id)

                if index_line in invoice_lines_obj:
                    invoice_lines_obj[index_line]['quantity'] += line.qty
                else:
                    invoice_lines_obj[index_line] = {
                        'product_id': line.product_id.id,
                        'name': line.full_product_name,
                        'product_uom_id': line.product_uom_id.id,
                        'price_unit': line.price_unit,
                        'quantity': line.qty,
                        'clave_sat': line.product_id.clave_sat.id or False,
                        #'tax_ids': [(6, 0, tax_ids)],
                    }
                    if len(tax_ids) > 0:
                        invoice_lines_obj[index_line]['tax_ids'] = [(6, 0, tax_ids)]
        for line_index in invoice_lines_obj:
            invoice_lines.append((0, None, invoice_lines_obj[line_index]))

        _logger.debug('===== create_invoice invoice_lines = %r',invoice_lines)
        invoice_data = {
            'partner_id': self.partner_id.id,
            'move_type': 'out_invoice',
            'cfdi_metodo_pago': 'PUE',
            'cfdi_forma_pago': self.payment_method_ids[0].cfdi_forma_pago,
            'payment_reference': 'Factura Golbal',# de '+str(self.start_date)+' a '.str(self.end_date),
            'ref': 'Factura Golbal',# de '+str(self.start_date)+' a '.str(self.end_date),
            'cfdi_global': True,
            'invoice_line_ids': invoice_lines,
        }
        _logger.debug('===== create_invoice invoice_data = %r',invoice_data)
        new_invoice = self.env['account.move'].sudo().with_context(default_move_type='out_invoice').create(invoice_data)
        if new_invoice:
            for order in self.pos_order_ids:
                order.write({
                    'cfdi_global': True,
                    'cfdi_global_id': new_invoice.id,
                    #'cfdi_ticket_state':'done',
                    #'cfdi_ticket_calls': 0,
                })
        #new_invoice = self.env['account.move'].sudo().with_company(self.company_id).with_context(default_move_type='out_invoice').create()
        _logger.debug('===== create_invoice new_invoice = %r',new_invoice)
        return {
            'name': 'Factura Global',
            'view_mode': 'form',
            'view_id': self.env.ref('account.view_move_form').id,
            'res_model': 'account.move',
            'context': "{'move_type':'out_invoice'}",
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': new_invoice.id or False,
        }