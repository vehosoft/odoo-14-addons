# Copyright VeHoSoft - Vertical & Horizontal Software (http://www.vehosoft.com)
# Code by: Francisco Rodriguez (frodriguez@vehosoft.com).
import time
import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class AccountPaymentCfdiWizard(models.TransientModel):
    _name = "account.payment.cfdi.wizard"
    _description = "Timbrar Complemento de Pago"
    
    @api.model
    def _default_cfdi_fecha(self):
        return fields.Date.context_today(self)
    
    @api.model
    def _default_cfdi_forma_pago(self):
        payment = self.env['account.payment'].browse(self._context.get('active_id'))
        _logger.debug('===== _default_cfdi_forma_pago payment name = %r',payment.name)
        _logger.debug('===== _default_cfdi_forma_pago journal name = %r',payment.journal_id.name)
        _logger.debug('===== _default_cfdi_forma_pago journal type = %r',payment.journal_id.type)
        if payment.journal_id.type == 'bank':
            forma_pago_code = '03'
        else:
            forma_pago_code = '99'
        
        return self.env['sat.forma.pago'].search([('code','=',forma_pago_code)], limit=1)

    cfdi_fecha = fields.Date(string='Fecha de emision', copy=False, required=True, default=_default_cfdi_fecha)
    cfdi_hora = fields.Float('Hora de emision')
    cfdi_serie = fields.Many2one('facturatool.serie', string="Serie", required=True,domain="[('company_id', '=', company_id)]")
    cfdi_forma_pago = fields.Many2one('sat.forma.pago', string="Forma de Pago", required=True, default=_default_cfdi_forma_pago)
    company_id = fields.Many2one('res.company', string="Compañia", required=True, readonly=True, default=lambda self: self._context.get('default_company_id'))

    def action_timbrar_cfdi(self):
        payments = self.env['account.payment'].browse(self._context.get('active_ids', []))
        _logger.debug('===== action_timbrar_cfdi payments = %r',payments)
        for payment in payments:
            _logger.debug('===== action_timbrar_cfdi payment = %r',payment.name)
            payment.write({
                'cfdi_fecha':self.cfdi_fecha,
                'cfdi_hora':self.cfdi_hora,
                'cfdi_serie':self.cfdi_serie.id,
                'cfdi_forma_pago':self.cfdi_forma_pago.id
            })
            payment.action_timbrar_pago_cfdi()
