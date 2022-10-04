from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class Cleaning(models.Model):
    _name = 'cleaning'
    _rec_name = "user"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name')
    sequence = fields.Integer(string='Sequence')
    datetime = fields.Datetime(string="Tanggal dan Waktu", default=datetime.now())
    user = fields.Many2one('employee.custom', string='Nama User', required=True)
    product = fields.Many2one('product.product', string='Product', domain=[('active', '=', True)], required=True)
    res_ok = fields.Integer(string='Hasil OK')
    res_ng = fields.Integer(string='Hasil NG') 
    rework = fields.Char(string='Rework')
    description = fields.Text(string='Description')
    state = fields.Selection([
        ("draft","Draft"),
        ("submit","Submited"), 
        ('cancel', "Canceled")], string='State', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True)
    custom_css = fields.Html(string='CSS', sanitize=False, compute='_compute_css', store=False)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            seq_date = None
            if 'date_order' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'cleaning', sequence_date=seq_date) or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('cleaning', sequence_date=seq_date) or _('New')

        vals['company_id'] = self.env.company.id
        vals['state'] = 'draft'

        return super().create(vals)  

    def action_submit(self):
        self.state = "submit"

    def write(self, vals):  
        # if self.state in ['submit']:
        #     raise ValidationError(_("You Cannot Edit %s as it is in %s State" % (self.name, self.state)))

        vals = super().write(vals)

        return vals
        
    def action_cancel(self):
        self.state = "cancel"

    def action_draft(self):
        self.state = "draft"

    def unlink(self):
        if self.state == 'submit':
            raise ValidationError(_("You Cannot Delete %s as it is in %s State" % (self.name, self.state)))
        return super().unlink()

    def remove(self):
        if self.state not in ['draft', 'cancel']:
            raise ValidationError(_("You Cannot Delete %s as it is in %s State" % (self.name, (self.state))))
        return super().remove()