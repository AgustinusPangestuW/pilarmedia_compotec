from dbm import dumb
from email.policy import default
from odoo import models, fields, api, _
import json

class Shift(models.Model):
    _name = "shift"
    _description = "Shift"

    name = fields.Char(string='Shift name', required='1')
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default="1")
    shift_line = fields.One2many('shift.line', 'shift_id', 'Line')

    def name_get(self):
        return _show_description(self)


class ShiftLine(models.Model):
    _name = "shift.line"
    _description = "Shift Template"

    shift_id = fields.Many2one('shift', 'Shift Template ID')
    sequence = fields.Integer(string='Sequence')
    working_time = fields.Many2one('working.time', string='Working Time', domain=[('active', '=', True)], required=True)


class ShiftDeadline(models.Model):
    _name = "shift.deadline"
    _description = "Shift Deadline"

    name = fields.Char(string='Shift Deadline', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default="1")

    def name_get(self):
        return _show_description(self)


class WorkingTime(models.Model):
    _name = "working.time"
    _description = "Working Time"

    name = fields.Char(string='Working Time name', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default="1")

    def name_get(self):
        return _show_description(self)


class Wrapping(models.Model):
    _name = 'wrapping'
    _description = "Wrapping"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Wrapping Name', select=True, copy=False, default='New')
    sequence = fields.Integer(string='Sequence', default=10)
    shift = fields.Many2one('shift', string='Shift', required=True, domain="[('active', '=', '1')]")
    shift_active = fields.Boolean(string='Shift Active?', readonly=True, compute="_change_active_shift", store=False)
    date = fields.Date(string='Date', default=fields.Date.today(), required=True)
    keeper = fields.Many2one('employee.custom', string='Line Keeper', required=True)
    operator_absent_ids = fields.Many2many(
        comodel_name='employee.custom', 
        relation='employee_custom_wrapping_rel',
        string='Operator Tidak Masuk'
    )
    backup_ids = fields.Many2many(
        comodel_name='employee.custom', 
        relation='employee_custom_backup_rel',
        string='Backup'
    )
    leader = fields.Many2one('employee.custom', string='Leader')
    state = fields.Selection([
        ("draft","Draft"),
        ("submit","Submited"), 
        ('cancel', "Canceled")], string='State', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True)
    custom_css = fields.Html(string='CSS', sanitize=False, compute='_compute_css', store=False)
    count_mo = fields.Integer(string='Count MO', compute="_count_mo", store=True, readonly=True)
    wrapping_deadline_line = fields.One2many(
        'wrapping.deadline.line', 
        'wrapping_deadline_id', 
        string='Wrapping Deadline', 
        copy=True, 
        auto_join=True
    )

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            seq_date = None
            if 'date_order' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'wrapping', sequence_date=seq_date) or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('wrapping', sequence_date=seq_date) or _('New')

        vals['company_id'] = self.env.company.id
        vals['state'] = 'draft'

        return super(Wrapping, self).create(vals)         

    @api.onchange('wrapping_deadline_line')
    def _change_active_shift(self):
        for rec in self:
            rec.shift_active = 1
            if len(rec.wrapping_deadline_line) > 0:
                rec.shift_active = 0

    @api.depends('state')
    def _compute_css(self):
        for rec in self:
            if rec.state != 'draft':
                rec.custom_css = '<style>.o_form_button_edit {display: none !important;}</style>'
            else:
                rec.custom_css = False

    def action_submit(self):
        self.state = "submit"
        self.create_mo()

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

    def _count_mo(self):
        for rec in self:
            rec.count_mo = rec.env['mrp.production'].sudo().search_count([('wrapping_id', '=', rec.id)])

    def action_see_mo(self):
        list_domain = []
        if 'active_id' in self.env.context:
            list_domain.append(('wrapping_id', '=', self.env.context['active_id']))
        
        return {
            'name':_('Manufacturing Order'),
            'domain':list_domain,
            'res_model':'mrp.production',
            'view_mode':'tree,form',
            'type':'ir.actions.act_window',
        }

    def create_mo(self):
        for rec in self:
            arr_total_per_product = {}
            for line in rec.wrapping_deadline_line:
                arr_total_per_product[line.product.id] = arr_total_per_product.get(line.product.id, 0) + line.total_output

            product_done_to_process = []
            for line in rec.wrapping_deadline_line:
                # hanya proses item yang berbeda saja
                if line.product.id not in product_done_to_process:
                    product_done_to_process.append(line.product.id)
                else:
                    continue

                bom_line = self.env['mrp.bom.line'].sudo().search([('product_id', '=', line.product.id)])
                if bom_line:
                    bom = bom_line[0].bom_id
                    new_mo = {
                        "product_id": bom.product_tmpl_id.id,
                        "bom_id": bom.id,
                        "product_qty": bom.product_qty,
                        "product_uom_id": bom.product_uom_id.id,
                        "company_id": self.env.company.id,
                        "wrapping_id": rec.id,
                        "move_raw_ids": [[0,0, {
                            "product_id": line.product.id,
                            "product_uom": line.total_output_uom.id,
                            "product_uom_qty": arr_total_per_product[line.product.id],
                            "name": "New",
                            "location_id": self.env['mrp.production'].sudo()._get_default_location_src_id(),
                            "location_dest_id": line.product.with_context(force_company=self.company_id.id).property_stock_production.id
                        }]]
                    }

                    if new_mo:
                        self.env['mrp.production'].sudo().create(new_mo)
                        self._count_mo()

    
class WrappingDeadlineLine(models.Model):
    _name = "wrapping.deadline.line"
    _description = "Wrapping Deadline Line"
    _rec_name = "shift_deadline"

    shift_deadline = fields.Many2one('shift.deadline', string='Shift Deadline', required=True)
    wrapping_deadline_id = fields.Many2one(
        'wrapping', 
        string='Wrapping Deadline Id', 
        ondelete='cascade', 
        index=1, 
        copy=False
    )
    product = fields.Many2one('product.product', string='Product', required=True)
    operator_ids = fields.Many2many(
        comodel_name='employee.custom', 
        relation='employee_custom_operator_rel',
        string='Operator Name'
    )
    total_output = fields.Integer(string='Total', compute="_calculate_total_output", store=True, help="Result Calculation from total output in Wrapping Working time")
    total_output_uom = fields.Many2one('uom.uom', string='Total UOM', compute="_product_change", store=True, help="UOM for total output")
    ng = fields.Integer(string='NG')
    ng_uom = fields.Many2one('uom.uom', string='NG UOM', compute="_product_change", store=True)
    total_ok = fields.Integer(string='Total OK', readonly=True, compute="_calculate_total_output_ok")
    total_ok_uom = fields.Many2one('uom.uom', string='Total OK UOM', compute="_product_change", store=True)
    note = fields.Text(string='Catatan')
    wrapping_deadline_working_time_line = fields.One2many(
        'wrapping.deadline.working.time.line', 
        'wrapping_deadline_working_time_id', 
        string="Wrapping Deadline Working Time", 
        copy=True, 
        auto_join=True
    )
    list_id_wt = fields.Html(string='List ID Working Time can access base on Shift', compute="_set_list_id_wj", readonly=True, store=False)

    @api.depends('product')
    def _product_change(self):
        """ 
        fetch value UOM when field product change 
        """
        for rec in self:
            rec.ng_uom = rec.total_output_uom = rec.total_ok_uom = rec.product.product_tmpl_id.uom_id.id

    @api.depends('wrapping_deadline_working_time_line.output')
    def _calculate_total_output(self):
        """
        Calculate the total output of the wrapping_deadline_working output.
        """
        total_output = 0.0
        for rec in self:
            for line in rec.wrapping_deadline_working_time_line:
                total_output += line.output

            self.total_output = total_output

    @api.depends('total_output', 'ng')
    def _calculate_total_output_ok(self):
        """
        Calculate the total output of the wrapping_deadline_working total_output - ng.
        """
        for wrapping_deadline_line in self:
            wrapping_deadline_line.update({
                'total_ok': wrapping_deadline_line.total_output - wrapping_deadline_line.ng
            })

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        
        shift_id = self.env.context.get('shift')
        if shift_id:
            dict_wt_base_shift = self.env['shift.line'].sudo().search([('shift_id', '=', shift_id)])
            list_id_wt_base_shift = [v.id for v in dict_wt_base_shift]
            wrapping_deadline_working_time_line_list = [[0,0, {
                'wrapping_deadline_working_time_id': self.id,
                'working_time': wt.id
            }] for wt in dict_wt_base_shift]
            res.update({
                'wrapping_deadline_working_time_line' : wrapping_deadline_working_time_line_list,
                'list_id_wt': [('id', 'in', list_id_wt_base_shift)]
            })

            # self.env.context.update({'list_id_wt': list_id_wt_base_shift})
            dict(self.env.context).update({'list_id_wt':list_id_wt_base_shift})
            self.env.context = dict(self.env.context)
            self.env.context.update({
                'allowed_company_ids': [],
            })

            self = self.with_context({
                'allowed_company_ids': []
            })
        return res


class WrappingDeadlineWorkingtimeLine(models.Model):
    _name = "wrapping.deadline.working.time.line"
    _description = "Wrapping Deadline Working time Line"

    name = fields.Char(string='Name', copy=False, default='New', compute="_set_name", readonly=False)
    wrapping_deadline_working_time_id = fields.Many2one(
        'wrapping.deadline.line', 
        string='Wrapping Deadline Working time Id', 
        copy=False, 
        ondelete='cascade', 
        index=1
    )
    working_time = fields.Many2one('working.time', string='Working time', required=True)
    output = fields.Integer(string='Output')
    break_time = fields.Char(string='Jam Break')
    rest_time = fields.Char(string='Jam Istirahat')
    plastic_role_change_time = fields.Char(string='Ganti Rol Plastik')
    product_change_time = fields.Char(string='Jam Ganti Produk')
    sequence = fields.Integer(string='Sequence')

    @api.onchange('working_time')
    def _set_name(self):
        """
        set value field `name` with value from field `working_time`
        """
        for rec in self:
            for working_time in rec.working_time:
                rec.update({'name': working_time.name})


def _show_description(self):
    """
    show field `description` in options
    """
    result = []
    for rec in self:
        name = rec.name
        if self.env.context.get('show_description') and rec.description:
            name += ' - ' + rec.description

        result.append((rec.id, name))

    return result