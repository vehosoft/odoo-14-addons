# Copyright VeHoSoft - Vertical & Horizontal Software (http://www.vehosoft.com)
# Code by: Francisco Rodriguez (frodriguez@vehosoft.com).

from odoo import api, fields, exceptions, models, tools, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
from lxml import etree
import json
import qrcode
import base64
import tempfile
import logging
_logger = logging.getLogger(__name__)
from datetime import datetime
import pytz
import qrcode
import io

class PosOrder(models.Model):
    _inherit = 'pos.order'
    cfdi_global = fields.Boolean(string="Factura Global", default=False ,readonly=True, copy=False)
    cfdi_global_id = fields.Many2one('account.move', string='Factura Global', readonly=True, copy=False)