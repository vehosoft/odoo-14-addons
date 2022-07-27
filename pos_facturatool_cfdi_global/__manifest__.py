# Copyright VeHoSoft - Vertical & Horizontal Software
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
	'name': 'Factura Global POS - FacturaTool',
	'summary': 'Permite emitir Facturas Globales CFDI v3.3 de Pedidos del Punto de Venta',
	'version': '14.0.1.0.1',
	"category": "Point Of Sale",
	'author': 'VeHoSoft',
	'website': 'http://www.vehosoft.com',
	'license': 'AGPL-3',
	'depends': [
		'account','pos_facturatool_cfdi','pos_facturatool_customerpanel'
	],
	'data': [
		"security/ir.model.access.csv",
		"wizard/cfdi_global.xml",
		"views/cfdi_global_views.xml",
		"views/pos_views.xml",
		"views/account_views.xml",
	],
	'qweb': [
	],
	'application': False,
	'installable': True,
	"external_dependencies": {
	},
}
