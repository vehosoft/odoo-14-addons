# Copyright VeHoSoft - Vertical & Horizontal Software (http://www.vehosoft.com)
# Code by: Francisco Rodriguez (frodriguez@vehosoft.com).
import time
import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class AccountMoveCfdiWizard(models.TransientModel):
    _name = "account.move.cfdi.wizard"
    _description = "Timbrar CFDI"

    @api.model
    def _default_cfdi_uso(self):
        invoice = self.env['account.move'].browse(self._context.get('active_id'))
        return invoice.partner_id.cfdi_uso
    
    @api.model
    def _default_cfdi_fecha(self):
        return fields.Date.context_today(self)
    
    @api.model
    def _default_cfdi_metodo_pago(self):
        invoice = self.env['account.move'].browse(self._context.get('active_id'))
        if invoice.cfdi_metodo_pago:
            return invoice.cfdi_metodo_pago
        elif invoice.payment_state == 'paid':
            return 'PUE'
        else:
            return 'PPD'
    
    @api.model
    def _default_cfdi_forma_pago(self):
        invoice = self.env['account.move'].browse(self._context.get('active_id'))
        _logger.debug('===== _default_cfdi_forma_pago default_company_id = %r',self._context.get('default_company_id'))
        if invoice.cfdi_forma_pago:
            return invoice.cfdi_forma_pago
        elif invoice.payment_state == 'paid':
            forma_pago_code = '01'
            payments = invoice._get_reconciled_info_JSON_values()
            if len(payments) > 0:
                payment = self.env['account.payment'].browse(int(payments[0]['account_payment_id']))
                _logger.debug('===== _default_cfdi_forma_pago payment name = %r',payment.name)
                _logger.debug('===== _default_cfdi_forma_pago journal name = %r',payment.journal_id.name)
                _logger.debug('===== _default_cfdi_forma_pago journal type = %r',payment.journal_id.type)
                if payment.journal_id.type == 'bank':
                    forma_pago_code = '03'
            
            return self.env['sat.forma.pago'].search([('code','=',forma_pago_code)], limit=1)
        else:
            return self.env['sat.forma.pago'].search([('code','=','99')], limit=1)

    cfdi_uso = fields.Many2one('sat.cfdi.uso', string="Uso del CFDI", required=True, default=_default_cfdi_uso)
    cfdi_fecha = fields.Date(string='Fecha de emision', copy=False, required=True, default=_default_cfdi_fecha)
    cfdi_hora = fields.Float('Hora de emision')
    cfdi_serie = fields.Many2one('facturatool.serie', string="Serie", required=True,domain="[('company_id', '=', company_id)]")
    cfdi_metodo_pago = fields.Selection([('PUE', 'Pago en una sola exhibicion'), ('PPD', 'Pago en parcialidades o diferido')], string='Metodo de Pago', default=_default_cfdi_metodo_pago, required=True)
    cfdi_forma_pago = fields.Many2one('sat.forma.pago', string="Forma de Pago", required=True, default=_default_cfdi_forma_pago)
    company_id = fields.Many2one('res.company', string="Compañia", required=True, readonly=True, default=lambda self: self._context.get('default_company_id'))

    @api.onchange('cfdi_metodo_pago')
    def _onchange_cfdi_metodo_pago(self):
        res = {}
        if self.cfdi_metodo_pago == 'PPD':
            self.cfdi_forma_pago = self.env['sat.forma.pago'].search([('code','=','99')], limit=1)
        return res

    def action_timbrar_cfdi(self):
        invoices = self.env['account.move'].browse(self._context.get('active_ids', []))
        _logger.debug('===== action_timbrar_cfdi invoices = %r',invoices)
        for invoice in invoices:
            _logger.debug('===== action_timbrar_cfdi invoice = %r',invoice.name)
            invoice.write({
                'cfdi_uso':self.cfdi_uso.id,
                'cfdi_fecha':self.cfdi_fecha,
                'cfdi_hora':self.cfdi_hora,
                'cfdi_serie':self.cfdi_serie.id,
                'cfdi_metodo_pago':self.cfdi_metodo_pago,
                'cfdi_forma_pago':self.cfdi_forma_pago.id
            })
            #for line in invoice.invoice_line_ids:
            #    line.clave_sat = line.product_id.clave_sat.id
            #    line.number_ident = line.product_id.number_ident
            invoice.action_timbrar_cfdi()
