# Copyright VeHoSoft - Vertical & Horizontal Software (http://www.vehosoft.com)
# Code by: Francisco Rodriguez (frodriguez@vehosoft.com).
import time
import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class AccountMoveCfdiEgresoWizard(models.TransientModel):
    _name = "account.move.cfdi.egreso.wizard"
    _description = "Timbrar CFDI de Egreso"

    @api.model
    def _default_cfdi_uso(self):
        return self.env['sat.cfdi.uso'].search([('code','=','G02')], limit=1)
    
    @api.model
    def _default_cfdi_fecha(self):
        return fields.Date.context_today(self)

    cfdi_uso = fields.Many2one('sat.cfdi.uso', string="Uso del CFDI", required=True, default=_default_cfdi_uso)
    cfdi_fecha = fields.Date(string='Fecha de emision', copy=False, required=True, default=_default_cfdi_fecha)
    cfdi_hora = fields.Float('Hora de emision')
    cfdi_serie = fields.Many2one('facturatool.serie', string="Serie", required=True,domain="[('company_id', '=', company_id)]")
    cfdi_tipo = fields.Selection([('DescBon', 'Descuento o Bonificación'), ('Devolucion', 'Devolución')], string='Tipo de Egreso', default='Devolucion')
    cfdi_forma_pago = fields.Many2one('sat.forma.pago', string="Forma de Pago", required=True)
    cfdi_descripcion = fields.Char(string='Descripcion del Egreso', required=True, default='Devolucion')
    company_id = fields.Many2one('res.company', string="Compañia", required=True, readonly=True, default=lambda self: self._context.get('default_company_id'))

    @api.onchange('cfdi_tipo')
    def _onchange_cfdi_tipo(self):
        res = {}
        if self.cfdi_tipo == 'DescBon':
            self.cfdi_forma_pago = self.env['sat.forma.pago'].search([('code','=','15')], limit=1)
            if self.cfdi_descripcion == 'Devolucion':
                self.cfdi_descripcion = 'Descuento o Bonificación'
        if self.cfdi_tipo == 'Devolucion':
            if self.cfdi_descripcion == 'Descuento o Bonificación':
                self.cfdi_descripcion = 'Devolucion'
        return res

    def action_timbrar_cfdi(self):
        invoices = self.env['account.move'].browse(self._context.get('active_ids', []))
        _logger.debug('===== action_timbrar_cfdi invoices = %r',invoices)
        for invoice in invoices:
            _logger.debug('===== action_timbrar_cfdi invoice = %r',invoice.name)
            tipo_relacion = '03'
            if self.cfdi_tipo == 'DescBon':
                tipo_relacion = '01'
            invoice.write({
                'cfdi_uso':self.cfdi_uso.id,
                'cfdi_fecha':self.cfdi_fecha,
                'cfdi_hora':self.cfdi_hora,
                'cfdi_serie':self.cfdi_serie.id,
                'cfdi_metodo_pago':'PUE',
                'cfdi_forma_pago':self.cfdi_forma_pago.id,
                'cfdi_tipo_relacion': tipo_relacion,
                'payment_reference': self.cfdi_descripcion
            })
            invoice.action_timbrar_cfdi_egreso()
