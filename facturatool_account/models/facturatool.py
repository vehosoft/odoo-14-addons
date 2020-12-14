# Copyright VeHoSoft - Vertical & Horizontal Software (http://www.vehosoft.com)
# Code by: Francisco Rodriguez (frodriguez@vehosoft.com).

from odoo import api, fields, models


class FacturaToolAccount(models.Model):
	_name = 'facturatool.account'
	_description = 'Cuenta FacturaTool'
	rfc = fields.Char(string='RFC', size=13, index=True,
					   required=True)
	username = fields.Char(string='Email', size=60, index=True,
					   required=True)
	password = fields.Char(string='Password', size=60, index=True,
					   required=True)
	validate = fields.Boolean(string='Validada', default=False, readonly=True)


class FacturaToolSerie(models.Model):
	_name = 'facturatool.serie'
	_description = 'Serie FacturaTool'
	name = fields.Char(string='Nombre', size=15, index=True,
					   required=True)
	factura = fields.Boolean(string='Factura', default=True )
	pago = fields.Boolean(string='Complemento de Pago', default=False )
	nomina = fields.Boolean(string='Recibo de Nomina', default=False )

class SatCFDIUso(models.Model):
	_name = 'sat.cfdi.uso'
	_description = 'Uso del CFDI'

	def name_get(self):
		resp = []
		for uso in self:
			name = str(uso.code) + ' - ' + str(uso.name)
			resp.append((uso.id, name))
		return resp

	code = fields.Char(string='Clave', size=3, index=True,required=True)
	name = fields.Char(string='Descripcion', size=80, index=True,required=True)

class SatFormaPago(models.Model):
	_name = 'sat.forma.pago'
	_description = 'Forma de Pago'

	def name_get(self):
		resp = []
		for uso in self:
			name = str(uso.code) + ' - ' + str(uso.name)
			resp.append((uso.id, name))
		return resp

	code = fields.Char(string='Clave', size=3, index=True,required=True)
	name = fields.Char(string='Descripcion', size=80, index=True,required=True)

class BaseDocumentLayout(models.TransientModel):
	_inherit = 'base.document.layout'
	street = fields.Char(related='company_id.street', readonly=True)
	street2 = fields.Char(related='company_id.street2', readonly=True)
	city = fields.Char(related='company_id.city', readonly=True)
	zip = fields.Char(related='company_id.zip', readonly=True)
	state_id = fields.Many2one(related="company_id.state_id", readonly=True)
	company_registry = fields.Char(related='company_id.company_registry', readonly=True)
