from email.policy import default
from odoo import models, fields, api, _

class Shift(models.Model):
    _name = "shift"
    _description = "Shift"

    name = fields.Char(string='Shift name', required='1')
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default="1")

    def name_get(self):
        return _show_description(self)


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

    name = fields.Char(string='Wrapping Name', select=True, copy=False, default='New')
    sequence = fields.Integer(string='Sequence', default=10)
    shift = fields.Many2one('shift', string='Shift', required=True, domain="[('active', '=', '1')]")
    date = fields.Date(string='Date', default=fields.Date.today(), required=True)
    keeper = fields.Many2one('res.partner', string='Line Keeper', required=True)
    operator_absent_ids = fields.Many2many(
        comodel_name='res.partner', 
        relation='res_partner_wrapping_rel',
        string='Operator Tidak Masuk'
    )
    backup_ids = fields.Many2many(
        comodel_name='res.partner', 
        relation='res_partner_backup_rel',
        string='Backup'
    )
    leader = fields.Many2one('res.partner', string='Leader')
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

        return super(Wrapping, self).create(vals)            
    
    
class WrappingDeadlineLine(models.Model):
    _name = "wrapping.deadline.line"
    _description = "Wrapping Deadline Line"
    _rec_name = "shift_deadline"

    shift_deadline = fields.Many2one('shift.deadline', string='Shift Deadline', required=True)
    wrapping_deadline_id = fields.Integer(string='Wrapping Deadline Id')
    product = fields.Many2one('product.product', string='Product')
    operator_ids = fields.Many2many(
        comodel_name='res.partner', 
        relation='res_partner_operator_rel',
        string='Operator Name'
    )
    total_output = fields.Integer(string='Total Output', compute="_calculate_total_output", store=True)
    total_output_uom = fields.Many2one('uom.uom', string='Total Output UOM', compute="_product_change", store=True)
    ng = fields.Integer(string='NG')
    ng_uom = fields.Many2one('uom.uom', string='NG UOM', compute="_product_change", store=True)
    total_oke = fields.Integer(string='Total Oke', readonly=True, compute="_calculate_total_output_oke")
    total_oke_uom = fields.Many2one('uom.uom', string='Total Oke UOM', compute="_product_change", store=True)
    note = fields.Text(string='Catatan')
    wrapping_deadline_working_time_line = fields.One2many(
        'wrapping.deadline.working.time.line', 
        'wrapping_deadline_working_time_id', 
        string="Wrapping Deadline Working Time", 
        copy=True, 
        auto_join=True
    )

    @api.depends('product')
    def _product_change(self):
        """ 
        fetch value UOM when field product change 
        """
        for rec in self:
            rec.ng_uom = rec.total_output_uom = rec.total_oke_uom = rec.product.product_tmpl_id.uom_id.id

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
    def _calculate_total_output_oke(self):
        """
        Calculate the total output of the wrapping_deadline_working total_output - ng.
        """
        for wrapping_deadline_line in self:
            wrapping_deadline_line.update({
                'total_oke': wrapping_deadline_line.total_output - wrapping_deadline_line.ng
            })


class WrappingDeadlineWorkingtimeLine(models.Model):
    _name = "wrapping.deadline.working.time.line"
    _description = "Wrapping Deadline Working time Line"

    name = fields.Char(string='Name', copy=False, default='New', compute="_set_name", readonly=False)
    wrapping_deadline_working_time_id = fields.Many2one('wrapping.deadline.line', string='Wrapping Deadline Working time Id', copy=False)
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