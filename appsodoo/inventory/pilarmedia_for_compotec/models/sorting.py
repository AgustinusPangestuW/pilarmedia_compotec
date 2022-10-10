from odoo import models, fields, api, _
from .employee_custom import _get_domain_user

class Sorting(models.Model):
    _name = 'sorting'

    name = fields.Char(string='Sorting Name', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    sequence = fields.Integer(string='Sequence', default=10)
    date = fields.Date(string='Tanggal', default=fields.Date.today(), required=True)
    sorting_line = fields.One2many('sorting.line', 'sorting_line_id', string='Sorting Line', copy=True, auto_join=True)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            seq_date = None
            if 'date_order' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'sorting', sequence_date=seq_date) or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('sorting', sequence_date=seq_date) or _('New')

        return super().create(vals)  


class SortingLines(models.Model):
    _name = "sorting.line"
    _description = "Sorting Line"
    _rec_name = "user"

    sorting_line_id = fields.Many2one(
        'sorting',
        string='Sorting Reference', 
        required=True, 
        ondelete='cascade', 
        index=True, 
        copy=False
    )
    user = fields.Many2one('employee.custom', string='Nama', domain=_get_domain_user)
    ok = fields.Integer(string='OK')
    pinched = fields.Integer(string='Terjepit')
    dusty = fields.Integer(string='Debu')
    another = fields.Integer(string='Lain - Lain')
          
