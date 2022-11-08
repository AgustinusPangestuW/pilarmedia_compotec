from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date
from .inherit_models_model import inheritModel
from .utils import validate_reserved_qty, fill_done_qty, _get_todo

class GeneratorMOorSP(inheritModel):
    _name = 'generator.mo.or.sp'    
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    READONLY_STATES = {
        'submit': [('readonly', True)],
        'cancel': [('readonly', True)],
    }
    list_state = [("draft","Draft"), ("submit","Submited"), ('cancel', "Canceled")]
    readonly_fields = ["name", "date", "job", "shift", "line_ids"]

    name = fields.Char(
        string='Name Generator MO or SP', required=True, default="New", 
        states=READONLY_STATES, copy=False)
    date = fields.Date(
        string='Tanggal', default=date.today(), required=True, states=READONLY_STATES)
    job = fields.Many2one('job', string='Job', required=True, states=READONLY_STATES)
    generate_document = fields.Char('Create Document To?', compute="fetch_from_job", store=True)
    shift = fields.Many2one('shift', string='Shift', states=READONLY_STATES)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    total_ok = fields.Float(string='Total OK', compute="calculate_ok_ng", store=True)
    total_ng = fields.Float(string='Total NG', compute="calculate_ok_ng", store=True)
    total = fields.Float(string='Total', compute="calculate_ok_ng", store=True)
    state = fields.Selection([
        ("draft","Draft"),
        ("submit","Submited"), 
        ('cancel', "Canceled")], string='State', tracking=True, copy=True)
    custom_css = fields.Html(string='CSS', sanitize=False, compute='_compute_css', store=False)
    line_ids = fields.One2many(
        'generator.mosp.lines', 'line_id', 'Line', states=READONLY_STATES, copy=True)
    count_stock_picking = fields.Integer(
        string='Count Stock Picking', 
        compute="_count_stock_picking", 
        store=True, 
        readonly=True)
    count_mo = fields.Integer(string='Count MO', compute="_count_mo", store=True, readonly=True)

    @api.depends('job')
    def fetch_from_job(self):
        self.generate_document = ""
        if self.job:
            self.generate_document = self.job.generate_document

    @api.depends('state')
    def _compute_css(self):
        for rec in self:
            if rec.state != 'draft':
                rec.custom_css = '<style>.o_form_button_edit {display: none !important;}</style>'
            else:
                rec.custom_css = False

    def _count_mo(self):
        for rec in self:
            rec.count_mo = rec.env['mrp.production'].sudo().search_count([('generator_mosp_id', '=', rec.id)])
    
    def _count_stock_picking(self):
        for rec in self:
            rec.count_stock_picking = rec.env['stock.picking'].sudo().search_count([('generator_mosp_id', '=', rec.id)])

    def action_see_stock_picking(self):
        list_domain = []
        if 'active_id' in self.env.context:
            list_domain.append(('generator_mosp_id', '=', self.env.context['active_id']))
        
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
            list_domain.append(('generator_mosp_id', '=', self.env.context['active_id']))
        
        return {
            'name':_('Manufacturing Order'),
            'domain':list_domain,
            'res_model':'mrp.production',
            'view_mode':'tree,form',
            'type':'ir.actions.act_window',
        }

    @api.depends('line_ids.ok', 'line_ids.ng')
    def calculate_ok_ng(self):
        for rec in self:
            total_ok, total_ng = 0, 0
            for line in self.line_ids:
                total_ok += line.ok
                total_ng += line.ng
            
            rec.total_ok = total_ok
            rec.total_ng = total_ng
            rec.total = total_ok + total_ng

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            seq_date = None
            if 'date' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date']))
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'generator_mo_or_sp', sequence_date=seq_date) or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('generator_mo_or_sp', sequence_date=seq_date) or _('New')

        vals['company_id'] = self.env.company.id
        vals['state'] = 'draft'

        return super().create(vals)  
    
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

    def action_submit(self):
        self.state = "submit"
        
        if self.job.generate_document == "mo":
            self.create_mo()
        elif self.job.generate_document == "transfer":
            self.create_stock_picking() 

    def validate_picking_type_ng_and_ok(self):
        # validate JOB
        if not self.job:
            raise ValidationError(_("Need job for process to submit."))
        
        # validate OP type (NG & OK) base on field job
        if not self.job.op_type_ok:
            raise ValidationError(_("Need operation type OK in Job %s for process to submit." % (
                self.job.name
            )))
        if not self.job.op_type_ng:
            raise ValidationError(_("Need operation type NG in Job %s for process to submit." % (
                self.job.name
            )))

    def create_mo(self):
        for rec in self:
            arr_total_per_product = {}
            for line in rec.line_ids:
                arr_total_per_product[line.product_id.id] = arr_total_per_product.get(line.product_id.id, 0) + line.total

            product_done_to_process = []
            for line in rec.line_ids:
                # hanya proses item yang berbeda saja
                if line.product_id.id not in product_done_to_process:
                    product_done_to_process.append(line.product_id.id)
                else:
                    continue
                
                if not line.bom_id:
                    raise ValidationError(_("Need BOM ID in for process item %s" % (line.product_id.name)))

                bom = line.bom_id
                if bom:
                    product_id_from_bom = self.env['product.product'].sudo().search([
                        ('product_tmpl_id', '=', line.product_id.product_tmpl_id.id)
                    ])
                    new_mo = {
                        "product_id": product_id_from_bom.id,
                        "bom_id": bom.id,
                        "product_qty": arr_total_per_product[line.product_id.id],
                        "product_uom_id": bom.product_uom_id.id,
                        "company_id": self.env.company.id,
                        "generator_mosp_id": rec.id,
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

                            for line in mri.move_line_ids:
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
        self.validate_picking_type_ng_and_ok()

        sm_ng, sm_ok = {}, {}
        for rec in self:
            sm_ng['picking_type_id'] = rec.job.op_type_ng.id
            sm_ng['location_id'] = rec.job.source_location_ng.id
            sm_ng['location_dest_id'] = rec.job.dest_location_ng.id
            sm_ng['generator_mosp_id'] = rec.id
            sm_ng['name'] = '/'

            sm_ok['picking_type_id'] = rec.job.op_type_ok.id
            sm_ok['location_id'] = rec.job.source_location_ok.id
            sm_ok['location_dest_id'] = rec.job.dest_location_ok.id
            sm_ok['generator_mosp_id'] = rec.id
            sm_ok['name'] = '/'

            sm_ng['move_lines'], sm_ok['move_lines'] = [], []
            for line in rec.line_ids:
                product = line.product_id.with_context(lang=self.env.user.lang)
                name_desc = product.partner_ref
                sm_ng['move_lines'].append((0,0, {
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.ng,
                    'description_picking': name_desc,
                    'product_uom': line.product_id.uom_id.id,
                    'name': name_desc
                }))

                sm_ok['move_lines'].append((0,0, {
                    'product_id': line.product_id.id, 
                    'product_uom_qty': line.ok,
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
            
            validate_reserved_qty(sm_ng)
            validate_reserved_qty(sm_ok)
            fill_done_qty(sm_ng)
            fill_done_qty(sm_ok)

            # Validate
            sm_ng.button_validate()
            sm_ok.button_validate()

            self._count_stock_picking()


class GeneratorMOSPLines(models.Model):
    _name = "generator.mosp.lines"

    product_id = fields.Many2one(
        'product.product', string='Product', required=True, ondelete='cascade', 
        index=True)
    product_template = fields.Integer(string='Product Template', readonly=True)
    ok = fields.Float(string='OK')
    ng = fields.Float(string='NG')
    total = fields.Float(string='Total', compute="calculat_totals", store=True)
    desc_for_ng = fields.Text(string='Description NG')
    description = fields.Text(string='Description')
    line_id = fields.Many2one(
        'generator.mo.or.sp', 'Items', index=True, ondelete='cascade')
    bom_id = fields.Many2one(
        'mrp.bom', string='BOM ID', compute="get_first_bom", readonly=False)

    @api.depends('ok', 'ng')
    def calculat_totals(self):
        for rec in self:
            rec.total = rec.ok + rec.ng

    @api.depends('product_id')
    def get_first_bom(self):
        for rec in self:
            # reset bom_id
            rec.bom_id = None

            if rec.product_id:
                rec.product_template = rec.product_id.product_tmpl_id.id
                boms = self.env['mrp.bom'].sudo().search([('product_tmpl_id', '=', rec.product_template)])
                if boms:
                    rec.bom_id = boms[0].id