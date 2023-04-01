# Copyright VeHoSoft - Vertical & Horizontal Software (http://www.vehosoft.com)
# Code by: Francisco Rodriguez (frodriguez@vehosoft.com).

from odoo import api, fields, models
import json
import logging
_logger = logging.getLogger(__name__)
try:
    import zeep
except ImportError:  # pragma: no cover
    _logger.debug('Cannot import zeep')

class FacturaToolAccount(models.Model):
	_name = 'facturatool.account'
	_description = 'Cuenta FacturaTool'
	rfc = fields.Char(string='RFC', size=13, index=True,
					   required=True)
	username = fields.Char(string='Email', size=80, index=True,
					   required=True)
	password = fields.Char(string='Password', size=120, index=True,
					   required=True)
	wsdl = fields.Char(string='WSDL', size=200, required=True, default='http://ws.facturatool.com/index.php?wsdl')
	validate = fields.Boolean(string='Validada', default=False, readonly=True)
	company_id = fields.Many2one('res.company', string='Compañia', store=True, required=True, default=lambda self: self.env.company)

	def action_validate(self):
		client = zeep.Client(self.wsdl)
		params = {
			'Rfc': self.rfc,
			'Usuario': self.username,
			'Password': self.password,
			'TransID': ''
		}
		_logger.debug('===== action_validate validarCuenta params = %r',params)
		result = client.service.validarCuenta(params=params)
		_logger.debug('===== action_validate validarCuenta result = %r',result)
		ws_res = json.loads(result)
		_logger.debug('===== action_validate validarCuenta ws_res = %r',ws_res)

		if ws_res['success'] == True:
			self.write({
				'validate': True
			})
		
		return ws_res


class FacturaToolSerie(models.Model):
	_name = 'facturatool.serie'
	_description = 'Serie FacturaTool'
	name = fields.Char(string='Nombre', size=15, index=True,
					   required=True)
	factura = fields.Boolean(string='Factura', default=True )
	pago = fields.Boolean(string='Complemento de Pago', default=False )
	nomina = fields.Boolean(string='Recibo de Nomina', default=False )
	active = fields.Boolean(string='Activo', default=True )
	company_id = fields.Many2one('res.company', string='Compañia', store=True, required=True, default=lambda self: self.env.company)

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

class SatRegimenFiscal(models.Model):
	_name = 'sat.regimen.fiscal'
	_description = 'Regimen Fiscal'

	def name_get(self):
		resp = []
		for regimen in self:
			name = str(regimen.code) + ' - ' + str(regimen.name)
			resp.append((regimen.id, name))
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
