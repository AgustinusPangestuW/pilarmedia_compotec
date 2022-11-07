from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from .employee_custom import _get_domain_user
from .inherit_models_model import inheritModel

class Cleaning(inheritModel):
    _name = 'cleaning'
    _rec_name = "user"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    READONLY_STATES = {
        'submit': [('readonly', True)],
        'cancel': [('readonly', True)],
    }
    list_state = [("draft","Draft"), ("submit","Submited"), ('cancel', "Canceled")]
    readonly_fields = ["name", "datetime", "user", "product", "res_ok", "res_ng", "rework", "description"]

    name = fields.Char(string='Name', copy=False, states=READONLY_STATES)
    sequence = fields.Integer(string='Sequence')
    datetime = fields.Datetime(string="Tanggal dan Waktu", default=datetime.now(), states=READONLY_STATES)
    user = fields.Many2one('employee.custom', string='Nama User', required=True, domain=_get_domain_user, states=READONLY_STATES)
    product = fields.Many2one('product.product', string='Product', domain=[('active', '=', True)], required=True, states=READONLY_STATES)
    res_ok = fields.Integer(string='Hasil OK', states=READONLY_STATES)
    res_ng = fields.Integer(string='Hasil NG', states=READONLY_STATES) 
    rework = fields.Char(string='Rework', states=READONLY_STATES)
    description = fields.Text(string='Description', states=READONLY_STATES)
    state = fields.Selection(list_state, string='State', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, states=READONLY_STATES)
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

    def validate_change_state(self, vals):
        # change state Draft / None -> Submit -> Cancel 
        # Change state Cancel -> Draft
        state_before = {
            "submit": ['', 'draft'],
            "cancel": ['submit']
        }

        if vals.get('state'):
            new_state = vals.get('state')
            name_cur_state = [s[1] for s in self.list_state if s[0] == self.state] or [""]
            for i in state_before:
                if new_state == i and self.state not in state_before[i]:
                    raise ValidationError(_("Current state must be %s when update state into %s, state document %s is %s" % (
                        "(" + ", ".join(state_before[i]) +")",
                        new_state,
                        self.name,
                        name_cur_state[0]
                    )))

    def validate_change_value_in_restrict_field(self, vals):
        readonly_status = False
        for i in vals:
            if i in self.readonly_fields:
                readonly_status = True

        if self.state in ['submit', 'cancel'] and readonly_status:
            name_cur_state = [s[1] for s in self.list_state if s[0] == self.state] or [""]
            raise ValidationError(_("You Cannot Edit %s as it is in %s State" % (self.name, name_cur_state[0])))

    def write(self, vals):  
        self.validate_change_value_in_restrict_field(vals)
        self.validate_change_state(vals)
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