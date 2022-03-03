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
import time
_logger = logging.getLogger(__name__)

try:
    import zeep
except ImportError:  # pragma: no cover
    _logger.debug('Cannot import zeep')

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    cfdi_hora_pago = fields.Float('Hora de pago', default=0.00)
    cfdi_hora_pago_str = fields.Char('Hora de Pago Texto',compute='_cfdi_hora_pago_str')
    
    def _cfdi_hora_pago_str(self):
        for record in self:
            float_time = str(record.cfdi_hora_pago)
            float_time = float_time.split('.')
            hours =  float_time[0]
            mins = int(float_time[1])
            mins =int( (mins * 60) / 10 )
            mins = str(mins)
            if len(hours) == 1:
                hours = '0' + hours
            if len(mins) > 1:
                mins = mins[0:2]
            else:
                mins = mins + '0'
            record.cfdi_hora_pago_str = hours +':'+ mins
    
    def action_wizard_timbrar_pago_cfdi(self):
        compose_form = self.env.ref('facturatool_pago.view_account_payment_wizard__timbrar_cfdi_form', raise_if_not_found=False)
        ctx = dict(
            default_model='account.payment',
            default_res_id=self.id,
            default_company_id=self.company_id.id,
        )
        _logger.debug('===== action_wizard_timbrar_pago_cfdi ctx = %r',ctx)
        return {
            'name': 'Generar CFDI con Complemento de Pago',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.payment.cfdi.wizard',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    def action_timbrar_pago_cfdi(self):
        status = False
        payments = self.filtered(lambda inv: inv.cfdi_state == 'draft')
        ft_account = self.env['facturatool.account'].search([('rfc','!=',''),('company_id','=',payments[0].company_id.id)], limit=1)
        if ft_account.rfc == False:
            msg = 'Error #8001: Necesita configurar su cuenta FacturaTool en "Contabilidad/Configuracion/Facturacion Electronica/Cuenta FacturaTool" para la empresa: '+payments[0].company_id.name
            raise UserError(msg)

        wsdl = 'http://ws.facturatool.com/index.php?wsdl'
        client = zeep.Client(wsdl)

        for payment in payments:
            _logger.debug('===== action_timbrar_pago_cfdi payment = %r',payment)
            if payment.partner_id.is_company == True:
                razon_social = payment.partner_id.razon_social
            else:
                razon_social = payment.partner_id.name

            receptor = {
    			'Rfc': payment.partner_id.vat,
    			'Nombre': razon_social,
    			'UsoCFDI': '000',
    		}

            facturas = []
            iline = 0
            _logger.debug('===== action_timbrar_pago_cfdi payment.reconciled_invoice_ids = %r',payment.reconciled_invoice_ids)
            for line in payment.reconciled_invoice_ids:
                invoice_payments = line._get_reconciled_info_JSON_values()
                _logger.debug('===== action_timbrar_pago_cfdi line = %r',line)
                _logger.debug('===== action_timbrar_pago_cfdi payment.id = %r',payment.id)
                _logger.debug('===== action_timbrar_pago_cfdi invoice_payments = %r',invoice_payments)
                for invoice_payment in invoice_payments:
                    if invoice_payment['account_payment_id'] == payment.id:
                        factura = {
                            'IdDocumento': line.cfdi_uuid,
                            'Serie': line.cfdi_serie.name,
                            'Folio': line.cfdi_folio,
                            'MonedaDR': 'MXN',#line.currency_id.name, hasta que se implemente timbrado para monedas distintas a MXN
                            'NumParcialidad': line.cfdi_parcialidad + 1,
                            'ImpSaldoAnt': line.cfdi_residual,
                            'ImpPagado': invoice_payment['amount'],#Provisional corregir
                            'ImpSaldoInsoluto': line.cfdi_residual - invoice_payment['amount'],#Provisional corregir
                        }
                        facturas[iline:iline]=[factura]
                        iline = iline + 1

            params = {
    			'Rfc': ft_account.rfc,
    			'Usuario': ft_account.username,
    			'Password': ft_account.password,
    			'FormaDePago': payment.cfdi_forma_pago.code,
    			'Serie': payment.cfdi_serie.name,
    			'Fecha': payment.cfdi_fecha,
    			'Hora': payment.cfdi_hora_str,
    			'FechaPago': payment.date,
    			'HoraPago': payment.cfdi_hora_pago_str,
    			'Moneda': 'MXN',#factura.currency_id.name, hasta que se implemente timbrado para monedas distintas a MXN
    			'LugarExpedicion': payment.company_id.zip,
    			'Receptor': receptor,
    			'DoctoRelacionados': facturas,
    			'Monto': payment.amount,
    			'IdExterno': payment.name+'_'+str(payment.id),
    		}
            #if payment.partner_id.email:
            #    params['EnviarEMail'] = 1
            #    params['EMail'] = payment.partner_id.email

            _logger.debug('===== action_timbrar_pago_cfdi params = %r',params)
            result = client.service.crearComplementoPago(params=params)
            _logger.debug('===== action_timbrar_pago_cfdi result = %r',result)
            ws_res = json.loads(result)
            _logger.debug('===== action_timbrar_pago_cfdi ws_res = %r',ws_res)

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
                cadena_orginal = '||1.0|'+ws_res['uuid']+'|'+ws_res['fecha_timbrado']+'|'+payment.cfdi_serie.name+str(ws_res['folio'])+'|'+sello_digital+'|'+serie_sat+'||'

                payment.write({
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
                filename+=payment.cfdi_serie.name.strip().upper()
                filename+=ws_res['folio'].strip()

                try:
                    self.env['ir.attachment'].create({
                        'name': filename + ".xml",
                        'type': 'binary',
                        'datas': base64.encodebytes(ws_res['xml'].encode()),
                        'res_model': 'account.payment',
                        'res_id': payment.id
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

    def action_cancel_pago_cfdi(self):
        wsdl = 'http://ws.facturatool.com/index.php?wsdl'
        client = zeep.Client(wsdl)
        for payment in self:
            ft_account = self.env['facturatool.account'].search([('rfc','!=',''),('company_id','=',payment.company_id.id)], limit=1)
            if ft_account.rfc == False:
                msg = 'Error #8001: Necesita configurar su cuenta FacturaTool en "Contabilidad/Configuracion/Facturacion Electronica/Cuenta FacturaTool" para la empresa: '+payment.company_id.name
                raise UserError(msg)
            #Solicitud al WS
            params = {
    			'Rfc': ft_account.rfc,
    			'Usuario': ft_account.username,
    			'Password': ft_account.password,
    			'TransID': payment.cfdi_trans_id
            }
            _logger.debug('===== action_cancel_pago_cfdi params = %r',params)
            #result = client.service.cancelarCFDIPago(params=params)
            #_logger.debug('===== action_cancel_pago_cfdi result = %r',result)
            #ws_res = json.loads(result)
            #_logger.debug('===== action_cancel_pago_cfdi ws_res = %r',ws_res)
            time.sleep( 5 )
            ws_res = {
                'success': True,
                'state': 'cancel',
            }
            status = False
            if ws_res['success'] == True:
                status = True

                payment.write({
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

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'
    hora_pago = fields.Float(string="Hora de pago",required=True, store=True, readonly=False, default=0.00)

    def _create_payment_vals_from_wizard(self):
        payment_vals = super(AccountPaymentRegister, self)._create_payment_vals_from_wizard()
        payment_vals['cfdi_hora_pago'] = self.hora_pago
        return payment_vals

class AccountMove(models.Model):
    _inherit = 'account.move'

    cfdi_residual = fields.Float('Importe pendiente CFDI',compute='_cfdi_residual')
    cfdi_parcialidad = fields.Integer('Parcialidades CFDI',compute='_cfdi_parcialidad')

    def _cfdi_residual(self):
        for move in self:
            if move.state == 'posted' and move.is_invoice(include_receipts=True):
                payments = move._get_reconciled_info_JSON_values()
                cfdi_residual = move.amount_total
                for payment in payments:
                    _logger.debug('===== _cfdi_residual payment = %r',payment)
                    payment_rec = self.env['account.payment'].browse(payment['account_payment_id'])
                    _logger.debug('===== _cfdi_residual payment_rec = %r',payment_rec)
                    _logger.debug('===== _cfdi_residual payment_rec.cfdi_state = %r',payment_rec.cfdi_state)
                    if payment_rec.cfdi_state == 'done':
                        cfdi_residual = cfdi_residual -  payment['amount']
                move.cfdi_residual = cfdi_residual
            else:
                move.cfdi_residual = 0.00
    
    def _cfdi_parcialidad(self):
        for move in self:
            if move.state == 'posted' and move.is_invoice(include_receipts=True):
                payments = move._get_reconciled_info_JSON_values()
                cfdi_parcialidad = 0
                for payment in payments:
                    payment_rec = self.env['account.payment'].browse(payment['account_payment_id'])
                    if payment_rec.cfdi_state == 'done':
                        cfdi_parcialidad = cfdi_parcialidad +  1
                move.cfdi_parcialidad = cfdi_parcialidad
            else:
                move.cfdi_parcialidad = 0