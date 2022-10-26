from enum import unique
from odoo import models, fields, api, _, exceptions
from datetime import datetime
from odoo.exceptions import ValidationError, UserError
from .employee_custom import _get_domain_user
from .inherit_models_model import inheritModel


class Lot(inheritModel):
    _name = "lot"
    _sql_constraints = [
        ('check_name_unique', 'UNIQUE(name)', 'The name is not unique')
    ]
    
    name = fields.Char(string='Name', required=True, default="-1")
    sequence = fields.Integer(string='Sequence')
    description = fields.Text(string='Desciption')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if not res.get('name', -1) == -1:
            self._cr.execute(""" SELECT MAX(name::integer) as get_max_name FROM lot """)
            res_max = self.env.cr.dictfetchone()
            max_ctr_name = 0
            if res_max:
                max_ctr_name = res_max['get_max_name'] if 'get_max_name' in res_max else 0

            res.update({'name': str(int(max_ctr_name) + 1)})

        return res

    @api.onchange('name')
    def _validate_name(self):
        for rec in self:
            try:
                rec.name = int(rec.name)
            except Exception as e:
                raise ValidationError(_("name must be Integer"))


class WholesaleJob(inheritModel):
    _name = 'wholesale.job'
    _description = "Wholesale Job"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    READONLY_STATES = {
        'submit': [('readonly', True)],
        'cancel': [('readonly', True)],
    }
    list_state = [("draft","Draft"), ("submit","Submited"), ('cancel', "Canceled")]
    readonly_fields = ["name", "date", "job_id", "checked_coordinator", "checked_qc", "shift", ]

    name = fields.Char(
        string='Wholesale Job Name', 
        required=True, 
        readonly=True, 
        index=True, 
        default=lambda 
        self: _('New'))
    sequence = fields.Integer(string='Sequence', default=10)
    date = fields.Date(string="Date", required=True, default=datetime.now().date(), states=READONLY_STATES)
    job_id_active = fields.Boolean(string='Job ID Active', compute="_set_job_id_active", store=True)
    job_id = fields.Many2one(
        'job', 
        string='Job', 
        domain=[('active', '=', 1), ('for_form', '=', 'wholesale_job')], 
        required=True, states=READONLY_STATES
    )
    wholesale_job_lines = fields.One2many(
        'wholesale.job.line', 
        'wholesale_job_id', 
        'Lot Line', 
        auto_join=True, 
        copy=True, 
        states=READONLY_STATES)
    checked_coordinator = fields.Many2one(
        'employee.custom', 
        string='Checked Coordinator', 
        domain=_get_domain_user, 
        states=READONLY_STATES)
    checked_qc = fields.Many2one(
        'employee.custom', 
        string='Checked QC', 
        domain=_get_domain_user, 
        states=READONLY_STATES)
    shift = fields.Many2one('shift', string='Shift', states=READONLY_STATES)
    state = fields.Selection([
        ("draft","Draft"),
        ("submit","Submited"), 
        ('cancel', "Canceled")], string='State', tracking=True)
    custom_css = fields.Html(string='CSS', sanitize=False, compute='_compute_css', store=False)
    operation_type_id_ng = fields.Many2one(
        'stock.picking.type', 
        string='Operation Type for NG', 
        # required=True, 
        compute="_get_op_type_from_job", 
        store=True
    )
    operation_type_id_ok = fields.Many2one(
        'stock.picking.type', 
        string='Operation Type for OK', 
        # required=True, 
        compute="_get_op_type_from_job", 
        store=True
    )
    count_stock_picking = fields.Integer(
        string='Count Stock Picking', 
        compute="_count_stock_picking", 
        store=True, 
        readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            seq_date = None
            if 'date_order' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'wholesale_job', sequence_date=seq_date) or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('wholesale_job', sequence_date=seq_date) or _('New')
        
        vals['company_id'] = self.env.company.id
        vals['state'] = 'draft'

        return super().create(vals)  

    @api.depends('job_id')
    def _get_op_type_from_job(self):
        if self.job_id:
            self.operation_type_id_ok = self.job_id.op_type_ok or ''
            self.operation_type_id_ng = self.job_id.op_type_ng or ''
        else:
            self.operation_type_id_ng = self.operation_type_id_ok = ""

    @api.depends('state')
    def _compute_css(self):
        for rec in self:
            if rec.state != 'draft':
                rec.custom_css = '<style>.o_form_button_edit {display: none !important;}</style>'
            else:
                rec.custom_css = False

    @api.depends('wholesale_job_lines')
    def _set_job_id_active(self):
        for rec in self:
            if len(rec.wholesale_job_lines) > 0: rec.job_id_active = 1
            else: rec.job_id_active = 0

    def validate_wj_lines(self):
        for rec in self:
            if not rec.wholesale_job_lines:
                raise ValidationError(_("Detail kantong masih kosong, harap isikan terlebih dahulu." ))

    def action_submit(self):
        self.state = "submit"
        # self.validate_wj_lines()
        self.create_stock_move()

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
        return super(WholesaleJob, self).unlink()

    def remove(self):
        if self.state not in ['draft', 'cancel']:
            raise ValidationError(_("You Cannot Delete %s as it is in %s State" % (self.name, (self.state))))
        return super(WholesaleJob, self).remove()

    def _count_stock_picking(self):
        for rec in self:
            rec.count_stock_picking = rec.env['stock.picking'].sudo().search_count([('wholesale_job_id', '=', rec.id)])

    def action_see_stock_picking(self):
        list_domain = []
        if 'active_id' in self.env.context:
            list_domain.append(('wholesale_job_id', '=', self.env.context['active_id']))
        
        return {
            'name':_('Transfers'),
            'domain':list_domain,
            'res_model':'stock.picking',
            'view_mode':'tree,form',
            'type':'ir.actions.act_window',
        }

    def create_stock_move(self):
        self.validate_wj_lines()

        sm_ng, sm_ok = {}, {}
        for rec in self:
            det_picking_type_ng = self.env['stock.picking.type'].sudo().search([('id', '=', rec.operation_type_id_ng.id)])
            sm_ng['picking_type_id'] = rec.operation_type_id_ng.id
            sm_ng['location_id'] = det_picking_type_ng.default_location_src_id.id or self.env['stock.warehouse']._get_partner_locations()[1].id
            sm_ng['location_dest_id'] = det_picking_type_ng.default_location_dest_id.id or self.env['stock.warehouse']._get_partner_locations()[1].id
            sm_ng['wholesale_job_id'] = self.id

            det_picking_type_ok = self.env['stock.picking.type'].sudo().search([('id', '=', rec.operation_type_id_ok.id)])
            sm_ok['picking_type_id'] = rec.operation_type_id_ok.id
            sm_ok['location_id'] = det_picking_type_ok.default_location_src_id.id or self.env['stock.warehouse']._get_partner_locations()[1].id
            sm_ok['location_dest_id'] = det_picking_type_ok.default_location_dest_id.id or self.env['stock.warehouse']._get_partner_locations()[1].id
            sm_ok['wholesale_job_id'] = self.id

            sm_ng['move_lines'], sm_ok['move_lines'] = [], []
            for line in self.wholesale_job_lines:
                product = line.product_id.with_context(lang=self.env.user.lang)
                name_desc = product.partner_ref
                sm_ng['move_lines'].append((0,0, {
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.total_ng,
                    'description_picking': name_desc,
                    'product_uom': line.product_id.uom_id.id,
                    'name': name_desc
                }))

                sm_ok['move_lines'].append((0,0, {
                    'product_id': line.product_id.id, 
                    'product_uom_qty': line.total_ok,
                    'description_picking': name_desc,
                    'product_uom': line.product_id.uom_id.id,
                    'name': name_desc
                }))
            
            # Create
            sm_ng = self.env['stock.picking'].sudo().create(sm_ng)
            sm_ok = self.env['stock.picking'].sudo().create(sm_ok)

            # Mark as To Do
            sm_ng.action_confirm()
            sm_ok.action_confirm()

            # Assign
            sm_ng.action_assign()
            sm_ok.action_assign()
            
            self.validate_reserved_qty(sm_ng)
            self.validate_reserved_qty(sm_ok)
            self.fill_done_qty(sm_ng)
            self.fill_done_qty(sm_ok)

            # Validate
            sm_ng.button_validate()
            sm_ok.button_validate()

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

class WholesaleJobLine(inheritModel):
    _name = "wholesale.job.line"
    _description = "Wholesale Job Line"

    sequence = fields.Integer(string='Sequence')
    wholesale_job_id = fields.Many2one(
        'wholesale.job', 
        'wholesale job id', 
        index=1, 
        ondelete="cascade"
    )
    is_set = fields.Boolean(
        string='Kantong?', 
        store=True,
        help="This field will be True when product UOM = `set`"
    )
    job_id = fields.Many2one(
        'job', string='Job', 
        required=True, 
        readonly=True, 
        domain=[('active', '=', 1)]
    )
    product_id = fields.Many2one('product.product', string='Produk', required=True)
    operator = fields.Many2one('employee.custom', string='Operator', required=True, domain=_get_domain_user)
    total_set = fields.Float(string="Total SET", readonly=True, compute="_calc_total_ok_n_set", store=True)
    total_ng = fields.Float(string="Total NG", compute="_calc_total_ng_ok", store=True, copy=True)
    total_ok = fields.Float(string="Total OK", readonly=True, compute="_calc_total_ng_ok", store=True)
    total_pcs = fields.Float(string='Total PCS', readonly=True, compute="_calc_total_ng_ok", store=True)
    factor = fields.Float(string='Isi Kantong', compute="_get_pocket_factor_in_product", store=True, readonly=False, copy=True)
    biggest_lot = fields.Many2one(
        'lot', 
        string='Last Lot', 
        readonly=True, 
        compute="_compute_get_biggest_lot", 
        store=True, 
        help="this field for track last Lot ID"
    )
    wholesale_job_lot_lines = fields.One2many(
        'wholesale.job.lot.line', 'wholesale_job_line_id', 
        'Lot Line', auto_join=True, copy=True)   

    @api.model
    def default_get(self, fields_list):
        res = super(WholesaleJobLine, self).default_get(fields_list)

        if self.env.context.get('job_id'):
            job_id = self.env.context.get('job_id')
            res.update({'job_id' : job_id})

        return res

    def add_job_lot_lines(self):
        """
        fucntion for create wholesale_job_lot_lines in different lot ID (unique)
        """
        biggest_lot_id, next_lot_id = "", ""
        list_lots = self.env['lot'].sudo().search([]).sorted(key=lambda r: int(r.name))

        # get list data `job_lot_line`
        if len(self.wholesale_job_lot_lines) > 0:
            biggest_lot_id = self.wholesale_job_lot_lines[-1].lot_id.id
        elif len(list_lots) > 0:
            # isikan lot pertama
            next_lot_id = list_lots[0].id 
        else:
            raise exceptions.ValidationError(_("Template data Kantong belum tersedia, silahkan tambahkan data pada Configuration Kantong"))

        if biggest_lot_id:
            # ambil urutan lot setelahnya untuk set lot id saat ini
            for idx_l, l in enumerate(list_lots):
                if int(l.id) == int(biggest_lot_id) and len(list_lots) > idx_l+1:
                    next_lot_id = list_lots[idx_l+1].id
                    break

        biggest_lot_id = next_lot_id

        if not biggest_lot_id:
            raise exceptions.ValidationError(_("Kantong melebihi batas yang ditentukan, silahkan sesuaikan dengan kantong yang tersedia."))
        
        self.update({
            'wholesale_job_lot_lines': [[0,0,{ 'lot_id': biggest_lot_id, 'wholesale_job_line_id': self.id }]],
            'biggest_lot': biggest_lot_id
        })

        self._calc_total_ng_ok()

        return self

    def remove_job_lot_lines(self):    
        # validation list job_lot_lines
        if len(self.wholesale_job_lot_lines) > 0:
            new_job_lot_line = self.wholesale_job_lot_lines[:-1]
            biggest_lot = None

            if len(new_job_lot_line) > 0:
                biggest_lot = new_job_lot_line[-1].lot_id.id
            
            self.write({
                'wholesale_job_lot_lines': new_job_lot_line,
                'biggest_lot': biggest_lot
            })

            self._calc_total_ng_ok()

            return self
        else:
            raise exceptions.ValidationError(_("Kantong saat ini belum tersedia."))

    @api.depends('is_set', 'wholesale_job_lot_lines.ng', 'wholesale_job_lot_lines.ok', \
        'total_ng')
    def _calc_total_ng_ok(self):
        for rec in self:
            # calculation NG & OK when is_set = FALSE (NON set)
            if not rec.is_set:
                self._calculate_ok_ng_pcs()

            # calculation NG & OK when is_set = TRUE
            else:
                self._calc_total_ok_n_set()


    def _calculate_ok_ng_pcs(self):
        total_ng, total_ok, total_pcs = 0, 0, 0
        for rec in self:
            if not rec.is_set:
                for line in self.wholesale_job_lot_lines:
                    total_ng += line.ng
                    total_ok += line.ok
                    total_pcs = total_ng + total_ok

                rec.update({
                    'total_ng': total_ng,
                    'total_ok': total_ok,
                    'total_pcs': total_pcs
                }) 
            
    @api.depends('factor', 'is_set', 'total_ng')
    def _calc_total_ok_n_set(self):
        new_total_lot, total_set = 0, 0
        for rec in self:
            if rec.is_set:
                last_lot_list = rec.wholesale_job_lot_lines
                last_lot_name = ''
                if len(last_lot_list) > 0:
                    last_lot_name = last_lot_list[-1].lot_id.name
                    new_total_lot = int(rec.factor) * int(last_lot_name)
                    
                total_set = rec.total_ok + rec.total_ng
                    
            rec.total_ok = new_total_lot
            rec.total_set = total_set

    @api.onchange('factor')
    def validate_factor(self):
        if self.is_set and (self.factor or 0) <= 0:
            raise ValidationError(_("field isi kantong tidak boleh <= 0" )) 

    @api.depends('product_id', 'is_set')
    def _get_pocket_factor_in_product(self):
        new_factor = None
        if self.is_set and self.product_id:
            new_factor = self.product_id.product_tmpl_id.pocket_factor
        self.factor = new_factor


class WholesaleJobLotLine(inheritModel):
    _name = "wholesale.job.lot.line"
    _description = "Wholesale Job Lot Line"
    _rec_name = "lot_id"
    
    wholesale_job_line_id = fields.Many2one('wholesale.job.line','Wholesale Job Line ID', index=1, ondelete="cascade")
    lot_id = fields.Many2one('lot', string='Lot No', required=True, readonly=True)
    ok = fields.Float(string='OK')
    ng = fields.Float(string='NG')