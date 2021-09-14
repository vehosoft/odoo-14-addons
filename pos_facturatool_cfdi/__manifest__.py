# Copyright VeHoSoft - Vertical & Horizontal Software
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
	'name': 'Facturación Electrónica POS - FacturaTool',
	'summary': 'Permite emitir Facturas CFDI v3.3 desde Punto de Venta',
	'version': '14.0.1.0.1',
	"category": "Point Of Sale",
	'author': 'VeHoSoft',
	'website': 'http://www.vehosoft.com',
	'license': 'AGPL-3',
	'depends': [
		'facturatool_cfdi',
	],
	'data': [
		'views/report_invoice.xml',
	],
	'qweb': [

	],
	'application': False,
	'installable': True,
	"external_dependencies": {
	},
}
