# Copyright VeHoSoft - Vertical & Horizontal Software
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
	'name': 'Facturación Electrónica CFDI Egreso v3.3 FacturaTool',
	'summary': 'Permite emitir Facturas CFDI de Egreso v3.3 validas para el SAT',
	'version': '14.0.1.0.1',
	'category': 'Invoicing Management',
	'author': 'VeHoSoft',
	'website': 'http://www.vehosoft.com',
	'license': 'AGPL-3',
	'depends': [
		'sale','facturatool_account', 'facturatool_cfdi',
	],
	'data': [
		'security/ir.model.access.csv',
		'data/data_catalogos_sat.xml',
		'views/account_views.xml',
		'wizard/account_move_timbrar_views.xml',
		#'views/report_invoice.xml',
	],
	'qweb': [

	],
	'application': False,
	'installable': True,
	"external_dependencies": {
		"python": ["zeep"],
	},
}
