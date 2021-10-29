# Copyright VeHoSoft - Vertical & Horizontal Software (http://www.vehosoft.com)
# Code by: Francisco Rodriguez (frodriguez@vehosoft.com).

from odoo import api, fields, exceptions, models, tools, _
import logging
_logger = logging.getLogger(__name__)


class FacturaToolAccount(models.Model):
    _inherit = 'facturatool.account'
    cfdi_portal = fields.Boolean(string="Portal de Clientes FacturaTool", default=False ,readonly=True)
    cfdi_portal_politica = fields.Char(string='Portal de Clientes Politica', size=30, copy=False, readonly=True)
    cfdi_portal_host = fields.Char(string='Portal de Clientes Host', size=200, copy=False, readonly=True)

    def action_validate(self):
        ws_res = super().action_validate()
        if ws_res['success'] == True:
            self.write({
                'cfdi_portal': ws_res['portal'],
                'cfdi_portal_politica': ws_res['portal_politica'],
                'cfdi_portal_host': ws_res['portal_host'],
            })
        return ws_res