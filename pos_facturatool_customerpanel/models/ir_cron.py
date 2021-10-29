# Copyright VeHoSoft - Vertical & Horizontal Software (http://www.vehosoft.com)
# Code by: Francisco Rodriguez (frodriguez@vehosoft.com).

from odoo import api, fields, exceptions, models

class ir_cron(models.Model):
    _inherit = "ir.cron"
    facturatool_count = fields.Integer(default=0, help="FacturaTool Count")