from dbm import dumb
from email.policy import default
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError 
import json
from .employee_custom import _get_domain_user
from .inherit_models_model import inheritModel
from .utils import return_sp


class Shift(inheritModel):
    _name = "shift"
    _description = "Shift"

    name = fields.Char(string='Shift name', required='1')
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default="1")
    shift_line = fields.One2many('shift.line', 'shift_id', 'Line', copy=True, auto_join=True)

    def name_get(self):
        return _show_description(self)


class ShiftLine(inheritModel):
    _name = "shift.line"
    _description = "Shift Template"

    shift_id = fields.Many2one('shift', 'Shift Template ID', ondelete="cascade", index=True)
    sequence = fields.Integer(string='Sequence')
    working_time = fields.Many2one('working.time', string='Working Time', domain=[('active', '=', True)], required=True)


class ShiftDeadline(inheritModel):
    _name = "shift.deadline"
    _description = "Shift Deadline"

    name = fields.Char(string='Shift Deadline', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default="1")

    def name_get(self):
        return _show_description(self)


class WorkingTime(inheritModel):
    _name = "working.time"
    _description = "Working Time"

    name = fields.Char(string='Working Time name', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default="1")

    def name_get(self):
        return _show_description(self)


class Wrapping(inheritModel):
    _name = 'wrapping'
    _description = "Wrapping"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    READONLY_STATES = {
        'submit': [('readonly', True)],
        'cancel': [('readonly', True)],
    }
    list_state = [("draft","Draft"), ("submit","Submited"), ('cancel', "Canceled")]
    readonly_fields = ["name", "shift", "date", "keeper", "operator_absent_ids", "backup_ids", "leader", "job", "wrapping_deadline_line"]

    name = fields.Char(string='Wrapping Name', select=True, copy=False, default='New', states=READONLY_STATES)
    sequence = fields.Integer(string='Sequence', default=10)
    shift = fields.Many2one(
        'shift', 
        string='Shift', 
        required=True, 
        domain="[('active', '=', '1')]", 
        copy=True, 
        states=READONLY_STATES)
    shift_active = fields.Boolean(
        string='Shift Active?', 
        readonly=True, 
        compute="_change_active_shift", 
        store=False)
    date = fields.Date(string='Date', default=fields.Date.today(), required=True, states=READONLY_STATES)
    keeper = fields.Many2one(
        'employee.custom', 
        string='Line Keeper', 
        required=True, 
        domain=_get_domain_user, 
        copy=True, 
        states=READONLY_STATES)
    operator_absent_ids = fields.Many2many(
        comodel_name='employee.custom', 
        relation='employee_custom_wrapping_rel',
        string='Operator Tidak Masuk',
        domain=_get_domain_user, 
        states=READONLY_STATES
    )
    backup_ids = fields.Many2many(
        comodel_name='employee.custom', 
        relation='employee_custom_backup_rel',
        string='Backup',
        domain=_get_domain_user, states=READONLY_STATES
    )
    leader = fields.Many2one(
        'employee.custom', 
        string='Leader', 
        domain=_get_domain_user, 
        copy=True, 
        states=READONLY_STATES)
    state = fields.Selection(list_state, string='State', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True)
    custom_css = fields.Html(string='CSS', sanitize=False, compute='_compute_css', store=False)
    count_mo = fields.Integer(string='Count MO', compute="_count_mo", store=True, readonly=True)
    count_stock_picking = fields.Integer(
        string='Count Stock Picking', 
        compute="_count_stock_picking", 
        store=True, 
        readonly=True)
    job = fields.Many2one(
        'job', 
        string='Job', 
        required=True, 
        domain=[('active', '=', 1), ('for_form', '=', 'wrapping')], 
        copy=True, 
        states=READONLY_STATES)
    wrapping_deadline_line = fields.One2many(
        'wrapping.deadline.line', 
        'wrapping_deadline_id', 
        string='Wrapping Deadline', 
        copy=True, 
        auto_join=True, 
        states=READONLY_STATES
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
        
        if self.job.generate_document == "mo":
            self.create_mo()
        elif self.job.generate_document == "transfer":
            self.create_stock_picking()

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
        return super().write(vals)
        
    def action_cancel(self):
        # cancel all MO & Stock Picking (SP)
        for rec in self:
            mo_ids = self.env['mrp.production'].sudo().search([('wrapping_id', '=', rec.id)])
            for i in mo_ids:
                i.action_cancel()
                rec._count_mo()
            
            picking_ids = self.env['stock.picking'].sudo().search([('wrapping_id', '=', rec.id)])
            for i in picking_ids:
                return_sp(i)
                rec._count_stock_picking()

            rec.state = "cancel"

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

    def _count_stock_picking(self):
        for rec in self:
            rec.count_stock_picking = rec.env['stock.picking'].sudo().search_count([('wrapping_id', '=', rec.id)])

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

    def action_see_stock_picking(self):
        list_domain = []
        if 'active_id' in self.env.context:
            list_domain.append(('wrapping_id', '=', self.env.context['active_id']))
        
        return {
            'name':_('Transfers'),
            'domain':list_domain,
            'res_model':'stock.picking',
            'view_mode':'tree,form',
            'type':'ir.actions.act_window',
        }

    def create_mo(self):
        for rec in self:
            arr_total_per_product = {}
            for line in rec.wrapping_deadline_line:
                arr_total_per_product[line.product.id] = arr_total_per_product.get(line.product.id, 0) + line.total

            product_done_to_process = []
            for line in rec.wrapping_deadline_line:
                # hanya proses item yang berbeda saja
                if line.product.id not in product_done_to_process:
                    product_done_to_process.append(line.product.id)
                else:
                    continue

                bom = self.env['mrp.bom'].sudo().search([('product_tmpl_id', '=', line.product.product_tmpl_id.id)])
                if bom:
                    product_id_from_bom = self.env['product.product'].sudo().search([('product_tmpl_id', '=', line.product.product_tmpl_id.id)])
                    new_mo = {
                        "product_id": product_id_from_bom.id,
                        "bom_id": bom.id,
                        "product_qty": arr_total_per_product[line.product.id],
                        "product_uom_id": bom.product_uom_id.id,
                        "company_id": self.env.company.id,
                        "wrapping_id": rec.id,
                        "picking_type_id": rec.job.op_type_ok.id,
                        "location_src_id": rec.job.source_location_ok.id,
                        "location_dest_id": rec.job.dest_location_ok.id
                    }
                    
                    try:
                        finished_lot_id = ""
                        mo = self.env['mrp.production'].sudo().create(new_mo)
                        mo._onchange_move_raw()
                        mo.action_confirm()
                        mo.action_assign()
                        for rec in mo:
                            if mo.reservation_state == "waiting":
                                raise UserError(_('stock is not enough.'))
                            else:
                                finished_lot_id = self.env['stock.production.lot'].create({
                                    'product_id': rec.product_id.id,
                                    'company_id': rec.company_id.id
                                })
                                # create produce
                                todo_qty, todo_uom, serial_finished = _get_todo(self, rec)
                                prod = mo.env['mrp.product.produce'].sudo().create({
                                    'production_id': rec.id,
                                    'product_id': rec.product_id.id,
                                    'qty_producing': todo_qty,
                                    'product_uom_id': todo_uom,
                                    'finished_lot_id': finished_lot_id.id,
                                    'consumption': bom.consumption,
                                    'serial': bool(serial_finished)
                                })
                                prod._compute_pending_production()
                                prod.do_produce()

                        # set done qty in stock move line
                        # HACK: cause qty done doesn't change / trigger when execute do_produce
                        for rec in mo.move_raw_ids:
                            # validation reserved_availability must be same with product_uom_qty (to consume)
                            if float(rec.reserved_availability or 0) < float(rec.product_uom_qty):
                                raise ValidationError(_("Item %s diperlukan Qty %s %s pada location %s untuk melanjutkan proses. Stock tersedia hanya %s") %(
                                    rec.product_id.name,
                                    rec.product_uom_qty, rec.product_uom.name,
                                    mo.location_src_id.location_id.name + '/' + mo.location_src_id.name,
                                    rec.reserved_availability
                                ))

                            for line in rec.move_line_ids:
                                line.qty_done = line.product_uom_qty
                                line.lot_produced_ids = finished_lot_id

                        mo.button_mark_done()
                        self._count_mo()
                    
                    except Exception as e:
                        raise (e)
                    
                else:
                    raise ValidationError(_("BOM untuk item %s belum tersedia") % (
                        line.product.product_tmpl_id.name
                    ))

    def create_stock_picking(self):
        sp_ng, sp_ok = {}, {}
        for rec in self:
            sp_ng['picking_type_id'] = rec.job.op_type_ng.id
            sp_ng['location_id'] = rec.job.source_location_ng.id or self.env['stock.warehouse']._get_partner_locations()[1].id
            sp_ng['location_dest_id'] = rec.job.dest_location_ng.id or self.env['stock.warehouse']._get_partner_locations()[1].id
            sp_ng['wrapping_id'] = self.id
            sp_ng['name'] = '/'

            sp_ok['picking_type_id'] = rec.job.op_type_ok.id
            sp_ok['location_id'] = rec.job.source_location_ok.id or self.env['stock.warehouse']._get_partner_locations()[1].id
            sp_ok['location_dest_id'] = rec.job.dest_location_ok.id or self.env['stock.warehouse']._get_partner_locations()[1].id
            sp_ok['wrapping_id'] = self.id
            sp_ok['name'] = '/'

            sp_ng['move_lines'], sp_ok['move_lines'] = [], []
            for line in self.wrapping_deadline_line:
                product = line.product.with_context(lang=self.env.user.lang)
                name_desc = product.partner_ref
                sp_ng['move_lines'].append((0,0, {
                    'product_id': line.product.id,
                    'product_uom_qty': line.ng,
                    'description_picking': name_desc,
                    'product_uom': line.product.uom_id.id,
                    'name': name_desc
                }))

                sp_ok['move_lines'].append((0,0, {
                    'product_id': line.product.id, 
                    'product_uom_qty': line.total_ok,
                    'description_picking': name_desc,
                    'product_uom': line.product.uom_id.id,
                    'name': name_desc
                }))
            
            # Create
            sp_ng = self.env['stock.picking'].sudo().create(sp_ng)
            sp_ok = self.env['stock.picking'].sudo().create(sp_ok)

            # Mark as To Do
            sp_ng.action_confirm()
            sp_ok.action_confirm()

            # Assign
            sp_ng.action_assign()
            sp_ok.action_assign()
            
            self.validate_reserved_qty(sp_ng)
            self.validate_reserved_qty(sp_ok)
            self.fill_done_qty(sp_ng)
            self.fill_done_qty(sp_ok)

            # Validate
            sp_ng.button_validate()
            sp_ok.button_validate()

            self._count_stock_picking()

    def validate_reserved_qty(self, stock_picking):
        for rec in stock_picking:
            for line in rec.move_ids_without_package:
                if line.reserved_availability < line.product_uom_qty:
                    raise UserError(_('Item {} pada location {} diperlukan Qty {} {}.').format(
                        line.product_id.name, 
                        rec.location_id.location_id.name + '/' + rec.location_id.name,
                        line.product_uom_qty,
                        line.product_uom.name
                    ))

    def fill_done_qty(self, stock_picking):
        for rec in stock_picking:
            for line in rec.move_line_ids_without_package:
                line.qty_done = line.product_uom_qty


def _get_todo(self, production):
    """ This method will return remaining todo quantity of production. """
    todo_uom = production.product_uom_id.id

    main_product_moves = production.move_finished_ids.filtered(lambda x: x.product_id.id == production.product_id.id)
    todo_quantity = production.product_qty - sum(main_product_moves.mapped('quantity_done'))
    todo_quantity = todo_quantity if (todo_quantity > 0) else 0

    serial_finished = production.product_id.tracking == 'serial'

    if serial_finished:
        todo_quantity = 1.0
        if production.product_uom_id.uom_type != 'reference':
            todo_uom = self.env['uom.uom'].search([('category_id', '=', production.product_uom_id.category_id.id), ('uom_type', '=', 'reference')]).id
    
    return todo_quantity, todo_uom, serial_finished

    
class WrappingDeadlineLine(inheritModel):
    _name = "wrapping.deadline.line"
    _description = "Wrapping Deadline Line"
    _rec_name = "shift_deadline"

    shift_deadline = fields.Many2one(
        'shift.deadline', 
        string='Shift Deadline', 
        required=True, 
        ondelete="cascade", 
        index=True)
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
        string='Operator Name',
        domain=_get_domain_user
    )
    total_ok = fields.Integer(
        string='OK', 
        compute="_calculate_total_ok", 
        store=True, 
        help="Result Calculation from total output in Wrapping Working time")
    total_output_uom = fields.Many2one(
        'uom.uom', 
        string='Total UOM', 
        compute="_product_change", 
        store=True, 
        help="UOM for total output")
    ng = fields.Integer(string='NG')
    ng_uom = fields.Many2one('uom.uom', string='NG UOM', compute="_product_change", store=True)
    total = fields.Integer(string='Total', readonly=True, compute="_calculate_total")
    total_ok_uom = fields.Many2one('uom.uom', string='Total OK UOM', compute="_product_change", store=True)
    note = fields.Text(string='Catatan')
    wrapping_deadline_working_time_line = fields.One2many(
        'wrapping.deadline.working.time.line', 
        'wrapping_deadline_working_time_id', 
        string="Wrapping Deadline Working Time", 
        copy=True, 
        auto_join=True
    )
    list_id_wt = fields.Char(
        string='List ID Working Time can access base on Shift', 
        readonly=True, 
        store=False)

    @api.depends('product')
    def _product_change(self):
        """ 
        fetch value UOM when field product change 
        """
        for rec in self:
            rec.ng_uom = rec.total_output_uom = rec.total_ok_uom = rec.product.product_tmpl_id.uom_id.id

    @api.depends('wrapping_deadline_working_time_line', 'wrapping_deadline_working_time_line.output')
    def _calculate_total(self):
        """
        Calculate the total output of the wrapping_deadline_working output.
        """
        for rec in self:
            rec.total = sum([l.output for l in rec.wrapping_deadline_working_time_line]) or 0

    @api.depends('total', 'ng')
    def _calculate_total_ok(self):
        """
        Calculate the total output of the wrapping_deadline_working total_ok + ng.
        """
        for rec in self:
            rec.update({
                'total_ok': rec.total - rec.ng
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
                'working_time': wt.working_time.id
            }] for wt in dict_wt_base_shift]
            res.update({
                'wrapping_deadline_working_time_line' : wrapping_deadline_working_time_line_list,
                'list_id_wt': list_id_wt_base_shift
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


class WrappingDeadlineWorkingtimeLine(inheritModel):
    _name = "wrapping.deadline.working.time.line"
    _description = "Wrapping Deadline Working time Line"

    name = fields.Char(
        string='Name', 
        copy=False, 
        default='New', 
        compute="_set_name", 
        readonly=False)
    wrapping_deadline_working_time_id = fields.Many2one(
        'wrapping.deadline.line', 
        string='Wrapping Deadline Working time Id', 
        copy=False, 
        ondelete='cascade', 
        index=1
    )
    working_time = fields.Many2one('working.time', string='Working time', required=True)
    output = fields.Integer(string='Total')
    break_time = fields.Char(string='Jam Break')
    rest_time = fields.Char(string='Jam Istirahat')
    plastic_roll_change_time = fields.Char(string='Ganti Rol Plastik')
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