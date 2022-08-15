# Copyright VeHoSoft - Vertical & Horizontal Software (http://www.vehosoft.com)
# Code by: Francisco Rodriguez (frodriguez@vehosoft.com).

from odoo import api, fields, exceptions, models, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
from lxml import etree
import json
import qrcode
import base64
import tempfile
import logging
_logger = logging.getLogger(__name__)

try:
    import zeep
except ImportError:  # pragma: no cover
    _logger.debug('Cannot import zeep')
    
class AccountMove(models.Model):
    _inherit = 'account.move'

    cfdi_tipo_relacion = fields.Selection([
        ('01', 'Nota de crédito de los documentos relacionados'), 
        ('02', 'Nota de débito de los documentos relacionados'), 
        ('03', 'Devolución de mercancía sobre facturas o traslados previos'),
        ('04', 'Sustitución de los CFDI previos'),
        ('07', 'CFDI por aplicación de anticipo')
    ], string='Tipo de Relacion CFDIs')
    cfdi_relacionados = fields.Char(string='CFDI Relacionados',compute='_cfdi_relacionados')

    def _cfdi_relacionados(self):
        for invoice in self:
            invoice_relacionados = invoice._get_reconciled_info_JSON_values()
            invoice_rel_text = ''
            if invoice.cfdi_state == 'done' and invoice.move_type == 'out_refund':
                for invoice_rel in invoice_relacionados:
                    invoice_rel_rec = self.env['account.move'].browse(int(invoice_rel['move_id']))
                    invoice_rel_text += invoice_rel_rec.cfdi_uuid + ' '
            invoice.cfdi_relacionados = invoice_rel_text

    
    def action_wizard_timbrar_cfdi_egreso(self):
        compose_form = self.env.ref('facturatool_egreso.view_account_move_wizard__timbrar_cfdi_egreso_form', raise_if_not_found=False)
        ctx = dict(
            default_model='account.move',
            default_res_id=self.id,
            default_company_id=self.company_id.id,
        )
        _logger.debug('===== action_wizard_timbrar_cfdi ctx = %r',ctx)
        payments = self._get_reconciled_info_JSON_values()
        _logger.debug('===== action_wizard_timbrar_cfdi payments = %r',payments)
        return {
            'name': 'Generar CFDI de Egreso',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.move.cfdi.egreso.wizard',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }
     
    def action_timbrar_cfdi_egreso(self):
        status = False
        invoices = self.filtered(lambda inv: inv.cfdi_state == 'draft')
        ft_account = self.env['facturatool.account'].search([('rfc','!=',''),('company_id','=',invoices[0].company_id.id)], limit=1)
        if ft_account.rfc == False:
            msg = 'Error #8001: Necesita configurar su cuenta FacturaTool en "Contabilidad/Configuracion/Facturacion Electronica/Cuenta FacturaTool" para la empresa: '+invoices[0].company_id.name
            raise UserError(msg)

        wsdl = 'http://ws.facturatool.com/index.php?wsdl'
        client = zeep.Client(wsdl)

        for invoice in invoices:
            if invoice.partner_id.is_company == True:
                razon_social = invoice.partner_id.razon_social
            else:
                razon_social = invoice.partner_id.name

            
            invoice_relacionados = invoice._get_reconciled_info_JSON_values()
            _logger.debug('===== action_timbrar_cfdi invoice = %r',invoice)
            _logger.debug('===== action_timbrar_cfdi invoice.id = %r',invoice.id)
            _logger.debug('===== action_timbrar_cfdi invoice_relacionados = %r',invoice_relacionados)
            
            CfdiRelacionados = []
            for invoice_rel in invoice_relacionados:
                invoice_rel_rec = self.env['account.move'].browse(int(invoice_rel['move_id']))
                if invoice_rel_rec.move_type == 'out_invoice' and invoice_rel_rec.cfdi_state=='done':
                    CfdiRelacionados.append({
                        'UUID': invoice_rel_rec.cfdi_uuid,
                        'TipoRelacion': invoice.cfdi_tipo_relacion
                    })
                else:
                    msg = 'Error: El CFDI relacionado ' + invoice.name + ' no es valido o no se encuentra timbrado.'
                    raise UserError(msg)
                    return {'params': {},'status': status}

            receptor = {
    			'Rfc': invoice.partner_id.vat,
    			'Nombre': razon_social,
    			'UsoCFDI': invoice.cfdi_uso.code,
    		}

            conceptos = []
            taxes = []
            iline = 0
            itax = 0
            discount=0
            for line in invoice.invoice_line_ids:
                tax_include_on_price = False
                for tax in line.tax_ids:
                    factor_tax = 1.00
                    if tax.amount < 0.00:
                        factor_tax = -1.00
                    if tax.amount_type=='percent' and tax.type_tax_sat != False:
                        tax_obj = {
                            'Nombre': tax.name,
                            'Tipo': tax.type_tax_sat,
                            'Impuesto': tax.clave_sat,
                            'Base': line.price_subtotal,
                            'TipoFactor': tax.tipo_factor_sat,
                            'TasaOCuota': (float(tax.amount)/100.00) * factor_tax,
                            'Importe': float(line.price_subtotal) * (float(tax.amount)/100.00) * factor_tax,
                            'indexConcepto': iline
    					}
                        taxes[itax:itax]=[tax_obj]
                    itax = itax + 1
                    if tax.price_include:
                        tax_include_on_price = True
                ValorUnitario = line.price_unit
                if tax_include_on_price:
                    ValorUnitario = float(line.price_subtotal) / float(line.quantity)
                concepto = {
    				#'ClaveProdServ': line.clave_sat.code,
    				'ClaveProdServ': line.clave_sat.code,
    				'Cantidad': line.quantity,
    				'Descripcion': line.name,
    				'ClaveUnidad': line.product_uom_id.clave_sat,
    				'Unidad': line.product_uom_id.name,
    				'ValorUnitario': ValorUnitario,
    				'Importe': line.price_subtotal,
    				#'Redondeo': 'weikov',
                    'indexConcepto': iline
    			}
                if line.number_ident != '' and line.number_ident != False:
                    concepto['NoIdentificacion'] = line.number_ident
                if line.discount > 0:
                    discount = discount + line.discount
                    concepto['Descuento'] = line.discount
                
                if line.display_type != 'line_section':
                    conceptos[iline:iline]=[concepto]
                    iline = iline + 1


            params = {
    			'Rfc': ft_account.rfc,
    			'Usuario': ft_account.username,
    			'Password': ft_account.password,
    			'Serie': invoice.cfdi_serie.name,
    			'Fecha': invoice.cfdi_fecha,
    			'Hora': invoice.cfdi_hora_str,
    			'FormaPago': invoice.cfdi_forma_pago.code,
    			'Moneda': 'MXN',#factura.currency_id.name, hasta que se implemente timbrado para monedas distintas a MXN
    			'LugarExpedicion': invoice.company_id.zip,
    			'Receptor': receptor,
    			'Descripcion': invoice.payment_reference,
                'Conceptos': conceptos,
    			'SubTotal': invoice.amount_total,#invoice.amount_untaxed,
    			'Total': invoice.amount_total,
                'CfdiRelacionados': CfdiRelacionados,
    			'IdExterno': invoice.name+'_'+str(invoice.id),
    		}
            if len(taxes) > 0:
                params['Impuestos'] =  taxes

            _logger.debug('===== action_timbrar_cfdi params = %r',params)
            result = client.service.crearCFDIEgreso(params=params)
            _logger.debug('===== action_timbrar_cfdi result = %r',result)
            ws_res = json.loads(result)
            _logger.debug('===== action_timbrar_cfdi ws_res = %r',ws_res)

            if ws_res['success'] == True:
                status = True

                cfdi = etree.fromstring(ws_res['xml'].encode('utf-8'))
                ns = {'c':'http://www.sat.gob.mx/cfd/3','d':'http://www.sat.gob.mx/TimbreFiscalDigital'}
                nodoT=cfdi.xpath('c:Complemento ', namespaces=ns)
                sello_digital = cfdi.get("Sello")
                serie_csd = cfdi.get("NoCertificado")

                for nodo in nodoT:
                    nodoAux=nodo.xpath('d:TimbreFiscalDigital', namespaces=ns)
                    uuid=nodoAux[0].get("UUID")
                    serie_sat = nodoAux[0].get("NoCertificadoSAT")
                    sello_sat = nodoAux[0].get("SelloSAT")
                cadena_orginal = '||1.0|'+ws_res['uuid']+'|'+ws_res['fecha_timbrado']+'|'+invoice.cfdi_serie.name+str(ws_res['folio'])+'|'+sello_digital+'|'+serie_sat+'||'

                
                invoice.write({
    				'cfdi_state':'done',
    				'cfdi_trans_id':ws_res['trans_id'],
    				'cfdi_folio':ws_res['folio'],
    				'cfdi_uuid':ws_res['uuid'],
    				'cfdi_fecha_timbrado':ws_res['fecha_timbrado'],
    				'cfdi_xml':ws_res['xml'],
    				'cfdi_sello_sat':sello_sat,
    				'cfdi_serie_sat':serie_sat,
    				'cfdi_sello_digital':sello_digital,
    				'cfdi_serie_csd':serie_csd,
    				'cfdi_cadena_original':str(cadena_orginal),
    			})

                filename=ft_account.rfc+'_'
                filename+=invoice.cfdi_serie.name.strip().upper()
                filename+=ws_res['folio'].strip()

                try:
                    self.env['ir.attachment'].create({
                        'name': filename + ".xml",
                        'type': 'binary',
                        'datas': base64.encodebytes(ws_res['xml'].encode()),
                        'res_model': 'account.move',
                        'res_id': invoice.id
                    })
                except:
                    pass

            else:
                if ws_res['error'] is None:
                    error = "Servicio temporalmente fuera de servicio"
                else:
                    error = ws_res['error']
                msg = 'Error #' + str(ws_res['errno']) + ': ' + error
                raise UserError(msg)

        return {'params': params,'status': status}

    def action_cancel_cfdi_egreso(self):
        wsdl = 'http://ws.facturatool.com/index.php?wsdl'
        client = zeep.Client(wsdl)
        for invoice in self:
            ft_account = self.env['facturatool.account'].search([('rfc','!=',''),('company_id','=',invoice.company_id.id)], limit=1)
            if ft_account.rfc == False:
                msg = 'Error #8001: Necesita configurar su cuenta FacturaTool en "Contabilidad/Configuracion/Facturacion Electronica/Cuenta FacturaTool" para la empresa: '+invoice.company_id.name
                raise UserError(msg)
            #Solicitud al WS
            params = {
    			'Rfc': ft_account.rfc,
    			'Usuario': ft_account.username,
    			'Password': ft_account.password,
    			'TransID': invoice.cfdi_trans_id
            }
            _logger.debug('===== action_cancel_cfdi params = %r',params)
            result = client.service.cancelarCFDI(params=params)
            _logger.debug('===== action_cancel_cfdi result = %r',result)
            ws_res = json.loads(result)
            _logger.debug('===== action_cancel_cfdi ws_res = %r',ws_res)

            status = False
            if ws_res['success'] == True:
                status = True

                invoice.write({
    				'cfdi_state':ws_res['state']
    			})
                msg = 'Cancelacion exitosa.'
                if ws_res['state'] == 'canceling': #Mostrar mensaje: 
                    msg = 'Cancelacion en proceso, espere hasta 72 horas para conocer el resultado de la cancelacion'

            else:
                if ws_res['error'] is None:
                    error = "Servicio temporalmente fuera de servicio"
                else:
                    error = ws_res['error']
                msg = 'Error #' + str(ws_res['errno']) + ': ' + error
                raise UserError(msg)
            
        return {'message': msg, 'params': params, 'status': status}