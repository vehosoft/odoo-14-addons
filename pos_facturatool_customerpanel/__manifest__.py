# Copyright VeHoSoft - Vertical & Horizontal Software
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
	'name': 'Portal de Clientes FacturaTool POS',
	'summary': 'Permite sincronizar pedidos de Punto de Venta a Portal de Clientes FacturaTool',
	'version': '14.0.1.0.1',
	"category": "Point Of Sale",
	'author': 'VeHoSoft',
	'website': 'http://www.vehosoft.com',
	'license': 'AGPL-3',
	'depends': [
		'facturatool_cfdi','point_of_sale'
	],
	'data': [
		'data/ir_cron_data.xml',
		"views/pos_templates.xml",
		"views/facturatool_views.xml",
	],
	'qweb': [
		'static/src/xml/OrderReceipt.xml'
	],
	'application': False,
	'installable': True,
	"external_dependencies": {
	},
}
