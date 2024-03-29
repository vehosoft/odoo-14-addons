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
		'facturatool_cfdi','point_of_sale'
	],
	'data': [
		'views/pos_views.xml',
		"views/pos_templates.xml"
	],
	'qweb': [
		"static/src/xml/PaymentScreen.xml",
		"static/src/xml/ClientDetailsEdit.xml",
		"static/src/xml/OrderReceipt.xml"
	],
	'application': False,
	'installable': True,
	"external_dependencies": {
	},
}
