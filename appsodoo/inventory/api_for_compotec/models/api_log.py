from odoo import models, fields, api, _

class ApiLog(models.Model):
    _name = 'api.log'

    name = fields.Char(string='API LOG Name', select=True, copy=False, default='New')
    datetime = fields.Datetime(string='Datetime', readonly=True)
    method = fields.Char(string='Method Name', readonly=True)
    sucess = fields.Boolean(string='Sucess', readonly=True)
    request = fields.Text(string='Request', readonly=True)
    result = fields.Text(string='Result', readonly=True)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            seq_date = None
            if 'date_order' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'api_log', sequence_date=seq_date) or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('api_log', sequence_date=seq_date) or _('New')

        return super(ApiLog, self).create(vals)    