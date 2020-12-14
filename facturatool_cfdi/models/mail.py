# Copyright VeHoSoft - Vertical & Horizontal Software (http://www.vehosoft.com)
# Code by: Francisco Rodriguez (frodriguez@vehosoft.com).

import base64
import logging


from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MailTemplate(models.Model):
    "Templates for sending email"
    _inherit = "mail.template"

    def generate_email(self, res_ids, fields):
        multi_mode = True
        if isinstance(res_ids, int):
            res_ids = [res_ids]
            multi_mode = False
        values = super(MailTemplate, self).generate_email(res_ids, fields)
        #_logger.debug('===== MailTemplate generate_email values = %r',values)
        if self.model == 'account.move':
            results = dict()
            for lang, (template, template_res_ids) in self._classify_per_lang(res_ids).items():
                for res_id in template_res_ids:
                    record = self.env[self.model].browse(res_id)
                    if record.cfdi_state == 'done':
                        if multi_mode:
                            attachments = values[res_id]['attachments']
                            report_name = record.company_id.vat + '_' + record.cfdi_serie.name + record.cfdi_folio + '.xml'
                            xml = base64.b64encode(record.cfdi_xml.encode('utf8'))
                            attachments.append((report_name, xml))
                            values[res_id].update( attachments=attachments)
        return values

