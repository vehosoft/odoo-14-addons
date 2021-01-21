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

    cfdi_uso = fields.Many2one('sat.cfdi.uso', string="Uso del CFDI", required=True, default=_default_cfdi_uso)
    cfdi_fecha = fields.Date(string='Fecha de emision', copy=False, required=True, default=_default_cfdi_fecha)
    cfdi_hora = fields.Float('Hora de emision')
    cfdi_serie = fields.Many2one('facturatool.serie', string="Serie", required=True)
    cfdi_metodo_pago = fields.Selection([('PUE', 'Pago en una sola exhibicion'), ('PPD', 'Pago en parcialidades o diferido')], string='Metodo de Pago', default='PUE', required=True)
    cfdi_forma_pago = fields.Many2one('sat.forma.pago', string="Forma de Pago", required=True)

    def action_timbrar_cfdi(self):
        invoices = self.env['account.move'].browse(self._context.get('active_ids', []))
        _logger.debug('===== action_timbrar_cfdi invoices = %r',invoices)
        for invoice in invoices:
            _logger.debug('===== action_timbrar_cfdi invoice = %r',invoice.name)
            invoice.write({
                'cfdi_uso':self.cfdi_uso.id,
                'invoice_date':self.cfdi_fecha,
                'cfdi_hora':self.cfdi_hora,
                'cfdi_serie':self.cfdi_serie.id,
                'cfdi_metodo_pago':self.cfdi_metodo_pago,
                'cfdi_forma_pago':self.cfdi_forma_pago.id
            })
            #for line in invoice.invoice_line_ids:
            #    line.clave_sat = line.product_id.clave_sat.id
            #    line.number_ident = line.product_id.number_ident
            invoice.action_timbrar_cfdi()
