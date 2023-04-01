# Copyright VeHoSoft - Vertical & Horizontal Software (http://www.vehosoft.com)
# Code by: Francisco Rodriguez (frodriguez@vehosoft.com).

from odoo import api, fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    razon_social = fields.Char(string='Razón Social', size=120)
    regimen_fiscal = fields.Many2one('sat.regimen.fiscal', string="Régimen Fiscal", help='Régimen Fiscal de tu cliente')
    cfdi_uso = fields.Many2one('sat.cfdi.uso', string="Uso del CFDI", help='Define el Uso del CFDI por defecto de tu cliente')