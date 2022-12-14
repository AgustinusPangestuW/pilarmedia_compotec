from enum import unique
from odoo import models, fields, api, _, exceptions
from datetime import datetime
from odoo.exceptions import ValidationError, UserError
from .employee_custom import _get_domain_user
from .inherit_models_model import inheritModel
from .wrapping import _get_todo
from .utils import return_sp


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


class PricelistLine(models.Model):
    _name = "wjob.pricelist.line"

    wholesale_job_id = fields.Many2one('wholesale.job', string='Wholesale Job ID', ondelete='cascade', index=1, readonly=1)
    pricelist_id = fields.Many2one('pilar.pricelist', string='Pricelist ID')
    price = fields.Float(string='Price', readonly=1)
    billed_ids = fields.One2many('wholesale.job.billed', 'wjpl_id', 'Line Billed')

    @api.onchange('pricelist_id')
    def get_price(self):
        for rec in self:
            rec.price = rec.pricelist_id.price or 0

    @api.model
    def create(self, vals):
        res = super().create(vals)
        for rec in res:
            for line in rec.wholesale_job_id.wholesale_job_lines:
                rec['billed_ids'] = [(0,0,{
                    'wjpl_id': rec.id,
                    'wjl_id': line.id,
                    'created_bill': False
                })]
        return res


class WholesaleJob(inheritModel):
    _name = 'wholesale.job'
    _description = "Wholesale Job"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    READONLY_STATES = {
        'submit': [('readonly', True)],
        'cancel': [('readonly', True)],
    }
    list_state = [("draft","Draft"), ("submit","Submited"), ('cancel', "Canceled")]
    readonly_fields = ["name", "date", "job", "checked_coordinator", "checked_qc", "shift", ]

    name = fields.Char(
        string='Wholesale Job Name', 
        required=True, 
        readonly=True, 
        index=True, 
        default=lambda 
        self: _('New'),
        copy=False)
    sequence = fields.Integer(string='Sequence', default=10)
    date = fields.Date(string="Date", required=True, default=datetime.now().date(), states=READONLY_STATES)
    job_id_active = fields.Boolean(string='Job ID Active', compute="_set_job_id_active", store=True)
    job = fields.Many2one(
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
    count_bill = fields.Integer(
        string='Count Bill', 
        compute="_count_bill", 
        store=True, 
        readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    count_mo = fields.Integer(string='Count MO', compute="_count_mo", store=True, readonly=True)
    pricelist_lines = fields.One2many('wjob.pricelist.line', 'wholesale_job_id', string='Pricelist Lines', copy=True)

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

    @api.depends('job')
    def _get_op_type_from_job(self):
        if self.job:
            self.operation_type_id_ok = self.job.op_type_ok or ''
            self.operation_type_id_ng = self.job.op_type_ng or ''
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
        vals = super().write(vals)
        return vals
        
    def action_cancel(self):            
        # cancel all MO & Stock Picking (SP)
        for rec in self:
            # restrict when have bill
            wholesale_job_line_ids = [i.id for i in rec.wholesale_job_lines]
            bill_ids = self.env['account.move.line'].sudo().search([('wholesale_job_line_id', 'in', wholesale_job_line_ids)])
            if bill_ids:
               raise UserError('Cannot cancel this document, cause this document have created bill.')

            mo_ids = self.env['mrp.production'].sudo().search([('wholesale_job_id', '=', rec.id)])
            for i in mo_ids:
                i.action_cancel()
                rec._count_mo()
            
            picking_ids = self.env['stock.picking'].sudo().search([('wholesale_job_id', '=', rec.id)])
            for i in picking_ids:
                return_sp(i)
                rec._count_stock_picking()

            rec.state = "cancel"

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

    def _count_mo(self):
        for rec in self:
            rec.count_mo = rec.env['mrp.production'].sudo().search_count([('wholesale_job_id', '=', rec.id)])
    
    def _count_stock_picking(self):
        for rec in self:
            rec.count_stock_picking = rec.env['stock.picking'].sudo().search_count([('wholesale_job_id', '=', rec.id)])

    def _count_bill(self):
        for rec in self:
            line_ids = [str(i.id) for i in rec.wholesale_job_lines]
            res = None
            if line_ids:
                self._cr.execute(""" 
                    SELECT count(move_id::integer) as get_count 
                    FROM account_move_line 
                    WHERE wholesale_job_line_id in (%s)
                    GROUP BY move_id 
                """ % (",".join(line_ids)))
                res = self.env.cr.dictfetchone()
                
            count = 0
            if res:
                count = res['get_count'] if 'get_count' in res else 0

            rec.count_bill = count

    def action_see_bill(self):
        list_domain = []
        if 'active_id' in self.env.context:
            wholesale_job_line_ids = self.env['wholesale.job.line'].sudo().search([
                ('wholesale_job_id', '=', self.env.context['active_id'])
            ])
            wholesale_job_line_ids = [str(i.id) for i in wholesale_job_line_ids]
            list_domain = []

            if wholesale_job_line_ids:
                self._cr.execute(""" 
                    SELECT aml.move_id  
                    FROM account_move_line aml
                    WHERE aml.wholesale_job_line_id in (%s)
                    GROUP BY aml.move_id 
                """ % (",".join(wholesale_job_line_ids)))
                bill_ids = self.env.cr.fetchall()
                bill_ids = [i[0] for i in bill_ids]
                list_domain.append(('id', 'in', bill_ids))
        
        return {
            'name':_('Bill'),
            'domain':list_domain,
            'res_model':'account.move',
            'view_mode':'tree,form',
            'type':'ir.actions.act_window',
        }

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

    def action_see_mo(self):
        list_domain = []
        if 'active_id' in self.env.context:
            list_domain.append(('wholesale_job_id', '=', self.env.context['active_id']))
        
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
            for line in rec.wholesale_job_lines:
                arr_total_per_product[line.product_id.id] = arr_total_per_product.get(line.product_id.id, 0) + (line.total_set or line.total_pcs)

            product_done_to_process = []
            for line in rec.wholesale_job_lines:
                # hanya proses item yang berbeda saja
                if line.product_id.id not in product_done_to_process:
                    product_done_to_process.append(line.product_id.id)
                else:
                    continue
                
                bom = line.bom_id
                if not bom:
                    bom = self.env['mrp.bom'].sudo().search([('product_tmpl_id', '=', line.product_id.product_tmpl_id.id)])
                    bom = bom[0] if bom else None
                if bom:
                    product_id_from_bom = self.env['product.product'].sudo().search([('product_tmpl_id', '=', line.product_id.product_tmpl_id.id)])
                    new_mo = {
                        "name": "New",
                        "product_id": product_id_from_bom.id,
                        "bom_id": bom.id,
                        "product_qty": arr_total_per_product[line.product_id.id],
                        "product_uom_id": bom.product_uom_id.id,
                        "company_id": self.env.company.id,
                        "wholesale_job_id": rec.id,
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
                        for rec_mo in mo:
                            if mo.reservation_state == "waiting":
                                raise UserError(_('stock is not enough.'))
                            else:
                                finished_lot_id = self.env['stock.production.lot'].create({
                                    'product_id': rec_mo.product_id.id,
                                    'company_id': rec_mo.company_id.id
                                })
                                # create produce
                                todo_qty, todo_uom, serial_finished = _get_todo(self, rec_mo)
                                prod = mo.env['mrp.product.produce'].sudo().create({
                                    'production_id': rec_mo.id,
                                    'product_id': rec_mo.product_id.id,
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
                        for mri in mo.move_raw_ids:
                            # validation reserved_availability must be same with product_uom_qty (to consume)
                            if float(mri.reserved_availability or 0) < float(mri.product_uom_qty):
                                raise ValidationError(_("Item %s diperlukan Qty %s %s pada location %s untuk melanjutkan proses. Stock tersedia hanya %s") %(
                                    mri.product_id.name,
                                    mri.product_uom_qty, mri.product_uom.name,
                                    mo.location_src_id.location_id.name + '/' + mo.location_src_id.name,
                                    mri.reserved_availability
                                ))

                            for mli in mri.move_line_ids:
                                mli.qty_done = mo.product_uom_qty
                                mli.lot_produced_ids = finished_lot_id

                        # detail component NG
                        if line.with_component:
                            self.scrap_components(mo, mo.move_raw_ids, line.wholesale_job_component_lines)

                        mo.button_mark_done()
                        self._count_mo()
                    
                    except Exception as e:
                        raise (e)
                    
                else:
                    raise ValidationError(_("BOM untuk item %s belum tersedia") % (
                        line.product.product_tmpl_id.name
                    ))

    def scrap_components(self, production, move_raw_ids:list, component_line:object):
        def scrap_component(product_id, qty, src_location, dest_location, production, lot_id):
            new_scrap = {
                'product_id': product_id.id,
                'scrap_qty': qty,
                'product_uom_id': product_id.uom_id.id,
                'location_id': src_location,
                'scrap_location_id': dest_location,
                'production_id': production.id,
                'lot_id': lot_id.id
            }
            new_scrap = self.env['stock.scrap'].sudo().create(new_scrap)
            new_scrap.action_validate()

        for mri in move_raw_ids:
            if mri.product_id.id == component_line.product_id.id and component_line.ng > 0:
                src_loc = component_line.wholesale_job_line_id.wholesale_job_id.job.source_location_ng.id or None
                dest_loc = component_line.wholesale_job_line_id.wholesale_job_id.job.dest_location_ng.id or None
                lot_id = None
                for mvl in mri.move_line_ids:
                    if mvl.qty_done >= component_line.ng:
                        lot_id = mvl.lot_id
                
                scrap_component(component_line.product_id, component_line.ng, src_loc, dest_loc, production, lot_id)
        

    def create_stock_picking(self):
        self.validate_wj_lines()

        sm_ng, sm_ok = {}, {}
        for rec in self:
            det_picking_type_ng = self.env['stock.picking.type'].sudo().search([('id', '=', rec.operation_type_id_ng.id)])
            sm_ng['picking_type_id'] = rec.operation_type_id_ng.id
            sm_ng['location_id'] = det_picking_type_ng.default_location_src_id.id or self.env['stock.warehouse']._get_partner_locations()[1].id
            sm_ng['location_dest_id'] = det_picking_type_ng.default_location_dest_id.id or self.env['stock.warehouse']._get_partner_locations()[1].id
            sm_ng['wholesale_job_id'] = self.id
            sm_ng['name'] = '/'

            det_picking_type_ok = self.env['stock.picking.type'].sudo().search([('id', '=', rec.operation_type_id_ok.id)])
            sm_ok['picking_type_id'] = rec.operation_type_id_ok.id
            sm_ok['location_id'] = det_picking_type_ok.default_location_src_id.id or self.env['stock.warehouse']._get_partner_locations()[1].id
            sm_ok['location_dest_id'] = det_picking_type_ok.default_location_dest_id.id or self.env['stock.warehouse']._get_partner_locations()[1].id
            sm_ok['wholesale_job_id'] = self.id
            sm_ok['name'] = '/'

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
    job = fields.Many2one(
        'job', string='Job', 
        required=True, 
        compute="fetch_job",
        store=True,
        readonly=True, 
        domain=[('active', '=', 1)]
    )
    product_id = fields.Many2one('product.product', string='Produk', required=True)
    product_template_id = fields.Many2one('product.template', string='Product Template', compute="get_product_template")
    operator = fields.Many2one('employee.custom', string='Operator', required=True, domain=_get_domain_user)
    total_set = fields.Float(string="Total SET", readonly=True, compute="_calc_total_ok_n_set", store=True, copy=True)
    total_ng = fields.Float(string="Total NG", compute="_calc_total_ng_ok", readonly=False, store=True, copy=True)
    total_ok = fields.Float(string="Total OK", readonly=True, compute="_calc_total_ng_ok", store=True, copy=True)
    total_pcs = fields.Float(string='Total PCS', readonly=True, compute="_calc_total_ng_ok", store=True, copy=True)
    factor = fields.Float(string='Isi Kantong', compute="_get_pocket_factor_in_product", store=True, readonly=False, copy=True)
    biggest_lot = fields.Many2one(
        'lot', 
        string='Last Lot', 
        readonly=True, 
        compute="_compute_get_biggest_lot", 
        store=True, 
        help="this field for track last Lot ID"
    )
    ng_reason = fields.Boolean(string='NG detail reason?', compute="fetch_from_job", store=True, readonly=False)
    total_from_ng_reason = fields.Float(
        string='Total NG', 
        compute="_calculate_total_ng_from_detail_ng", 
        store=True,
        help="result from calculate total_ng from detail ng (ng_ids)")
    ng_ids = fields.One2many('details.ng', 'wholesale_job_line_id', 'NG Details')
    msg_error = fields.Text(
        string='', readonly=1, default="Total NG in detail not same with Total NG current")
    show_msg_error = fields.Boolean(
        string='Show Message Error', help="flag for show field msg_error", compute="_comp_show_msg_error")
    wholesale_job_lot_lines = fields.One2many(
        'wholesale.job.lot.line', 'wholesale_job_line_id', 
        'Lot Line', auto_join=True, copy=True)   
    reason_for_ng = fields.Text(string='Keterangan NG')
    with_component = fields.Boolean(string='NG Component ?', store=True, compute="fetch_from_job", readonly=False)
    wholesale_job_component_lines = fields.One2many(
        'wholesale.job.component.line', 'wholesale_job_line_id', 'Lines', compute="get_component",
        store=True, readonly=False)
    bom_id = fields.Many2one('mrp.bom', string='BOM', compute="get_first_bom", store=True, readonly=False)
    billed_ids = fields.One2many('wholesale.job.billed', 'wjl_id', 'Line Billed')

    @api.model
    def create(self, vals):
        res = super().create(vals)
        for rec in res:
            for line in rec.wholesale_job_id.pricelist_lines:
                rec['billed_ids'] = [(0,0,{
                    'wjpl_id': line.id,
                    'wjl_id': rec.id,
                    'created_bill': False
                })]

        return res

    @api.depends('job')
    def fetch_from_job(self):
        for rec in self:
            fill = {'ng_reason': 0, 'with_component': 0}
            if rec.job and rec.job.for_form == "wholesale_job":
                fill.update({
                    'ng_reason': rec.job.ng_reason,
                    'with_component': rec.job.with_component
                })
            rec.ng_reason = fill['ng_reason']
            rec.with_component = fill['with_component']

    @api.depends('product_id')
    def get_first_bom(self):
        for rec in self:
            bom = None

            if rec.product_id:
                boms = self.env['mrp.bom'].sudo().search([('product_tmpl_id', '=', rec.product_id.product_tmpl_id.id)])
                bom = boms[0] if boms else None
            rec.bom_id = bom

    @api.depends('bom_id')
    def get_component(self):
        for rec in self:
            rec.wholesale_job_component_lines = [(5,0,0)]
            list_component = []
            for c in rec.bom_id.bom_line_ids:
                list_component.append((0,0,{
                    'product_id': c.product_id.id,
                    'qty_in_bom': c.product_qty,
                    'uom': c.product_uom_id.id,
                }))

            rec.wholesale_job_component_lines = list_component
    
    @api.depends('product_id')
    def get_product_template(self):
        for rec in self:
            product_template = None
            if rec.product_id:
                product_template = rec.product_id.product_tmpl_id.id
            rec.product_template_id = product_template

    @api.depends("wholesale_job_lot_lines")
    def _compute_get_biggest_lot(self):
        for rec in self:
            rec.biggest_lot = rec.wholesale_job_lot_lines[-1].lot_id.id \
                if len(rec.wholesale_job_lot_lines) > 0 else None

    @api.depends('ng_reason', 'total_from_ng_reason', 'total_ng')
    def _comp_show_msg_error(self):
        for rec in self:
            show_msg_error = 0
            if rec.ng_reason and rec.total_from_ng_reason != rec.total_ng:
                show_msg_error = 1
            rec.show_msg_error = show_msg_error

    @api.depends('wholesale_job_id')
    def fetch_job(self):
        for rec in self:
            if rec.wholesale_job_id.job:
                job = rec.wholesale_job_id.job.id
                rec.update({'job': job})

    @api.model
    def default_get(self, fields_list):
        res = super(WholesaleJobLine, self).default_get(fields_list)

        if self.env.context.get('job'):
            job = self.env.context.get('job')
            res.update({'job' : job})

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

    @api.depends('ng_ids', 'ng_reason')
    def _calculate_total_ng_from_detail_ng(self):
        for rec in self:
            total_ng = sum([i.total_ng for i in rec.ng_ids])
            rec.total_from_ng_reason = total_ng

    @api.depends('is_set', 'wholesale_job_lot_lines.ng', 'wholesale_job_lot_lines.ok', \
        'total_ng', 'total_from_ng_reason')
    def _calc_total_ng_ok(self):
        for rec in self:
            # calculation NG & OK when is_set = FALSE (NON set)
            if not rec.is_set:
                self._calculate_ok_ng_pcs()

            # calculation NG & OK when is_set = TRUE
            else:
                # get total ng base on table detail_ng
                rec.total_ng = rec.total_from_ng_reason

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
                    rec.biggest_lot = last_lot_list[-1].lot_id.id
                    last_lot_name = last_lot_list[-1].lot_id.name
                    new_total_lot = int(rec.factor) * int(last_lot_name)
                    
                rec.total_ok = new_total_lot
                total_set = rec.total_ok + rec.total_ng
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

class WholesaleJobBilled(models.Model):
    _name = "wholesale.job.billed"

    wjl_id = fields.Many2one('wholesale.job.line', string='Wholesale Job Lile ID', ondelete='cascade', index=1)
    wjpl_id = fields.Many2one('wjob.pricelist.line', string='WJOB Pricelist Line ID', ondelete='cascade', index=1)
    created_bill = fields.Boolean(string='Created Bill ?')

class WholesaleJobLotLine(inheritModel):
    _name = "wholesale.job.lot.line"
    _description = "Wholesale Job Lot Line"
    _rec_name = "lot_id"
    
    wholesale_job_line_id = fields.Many2one('wholesale.job.line','Wholesale Job Line ID', index=1, ondelete="cascade")
    lot_id = fields.Many2one('lot', string='Lot No', required=True, readonly=True)
    ok = fields.Float(string='OK')
    ng = fields.Float(string='NG')


class MasterNG(inheritModel):
    _name = "master.ng"
    _description = "Master NG"

    _sql_constraints = [
        ('check_name_unique', 'UNIQUE(name)', 'The name must be unique')
    ]

    name = fields.Char(string='Name', required=True, copy=False)
    active = fields.Boolean(string='Active', default=True)
    description = fields.Text(string='Description')


class DetailsNG(inheritModel):
    _name = "details.ng"
    _description = "Detail NG"
   
    wholesale_job_line_id = fields.Many2one('wholesale.job.line', 'Wholesale Job Line ID', ondelete='cascade', index=True)
    ng_id = fields.Many2one('master.ng', string='NG', domain="[('active', '=', True)]", required=True, copy=True)
    total_ng = fields.Float(string='NG Total')


class WholesaleJobComponentLine(inheritModel):
    _name = "wholesale.job.component.line"
    _description = "Wholesale Job Component Line"

    wholesale_job_line_id = fields.Many2one(
        'wholesale.job.line', 'Wholesale Job Line ID', index=1, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    uom = fields.Many2one('uom.uom', string='UOM', readonly=True)
    qty_in_bom = fields.Float(string='Qty in BOM', readonly=True)
    total = fields.Float(string='Total', readonly=True, compute="calculate_total")
    ok = fields.Float(string='OK', compute="get_total")
    ng = fields.Float(string='NG')

    @api.depends('wholesale_job_line_id.total_pcs', 'wholesale_job_line_id.total_set')
    def get_total(self):
        for rec in self:
            rec.ok = rec.wholesale_job_line_id.total_pcs or rec.wholesale_job_line_id.total_set or 0

    @api.depends('ok', 'ng')
    def calculate_total(self):
        for rec in self:
            rec.total = rec.ok + rec.ng