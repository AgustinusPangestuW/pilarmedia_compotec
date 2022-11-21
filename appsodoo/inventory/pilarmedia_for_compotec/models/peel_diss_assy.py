from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError, UserError
from .employee_custom import _get_domain_user
from .wrapping import _get_todo
from .inherit_models_model import inheritModel


class PeelDissAssy(inheritModel):
    _name = 'peel.diss.assy'
    _description = "Form Kupas Diss Assy"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    READONLY_STATES = {
        'submit': [('readonly', True)],
        'cancel': [('readonly', True)],
    }
    list_state = [("draft","Draft"), ("submit","Submited"), ('cancel', "Canceled")]
    readonly_fields = ["name", "date", "job"]

    sequence = fields.Integer(string='Sequence')
    name = fields.Char(string='Name', readonly=True, copy=False)
    date = fields.Date(
        string='Tangal',
        default=datetime.now().date(), 
        required=True, 
        states=READONLY_STATES)
    job = fields.Many2one(
        'job', 
        string='Job', 
        required=True, 
        domain=[('active', '=', 1), ('for_form', '=', 'peel_diss_assy')], 
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
    peel_diss_assy_line = fields.One2many(
        'peel.diss.assy.line', 
        'peel_diss_assy_id', 
        'Line', 
        copy=True, 
        auto_join=True)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            seq_date = None
            if 'date_order' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'peel_diss_assy', sequence_date=seq_date) or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('peel_diss_assy', sequence_date=seq_date) or _('New')
        
        vals['company_id'] = self.env.company.id
        vals['state'] = 'draft'

        return super().create(vals)  

    def validate_qty_component(self):
        for idx, rec in enumerate(self.peel_diss_assy_line):
            for line in rec.peel_diss_assy_component_line:
                if float(line.peeled_total) != float(rec.qty):
                    raise UserError(_("Product {} pada baris {}, total kupas componen {} ({}) harus sama dengan qty product acuan ({})".format(
                            rec.product_id.name, idx+1, line.product_id.name, line.peeled_total, rec.qty
                        )))

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
        vals = super().write(vals)
        self.validate_qty_component()
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
            rec.count_mo = rec.env['mrp.production'].sudo().search_count([('peel_diss_assy_id', '=', rec.id)])
    
    def _count_stock_picking(self):
        for rec in self:
            rec.count_stock_picking = rec.env['stock.picking'].sudo().search_count([('peel_diss_assy_id', '=', rec.id)])

    def action_see_mo(self):
        list_domain = []
        if 'active_id' in self.env.context:
            list_domain.append(('peel_diss_assy_id', '=', self.env.context['active_id']))
        
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
            list_domain.append(('peel_diss_assy_id', '=', self.env.context['active_id']))
        
        return {
            'name':_('Transfers'),
            'domain':list_domain,
            'res_model':'stock.picking',
            'view_mode':'tree,form',
            'type':'ir.actions.act_window',
        }

    def create_mo(self):
        for rec in self:
            for line in rec.peel_diss_assy_line:
                new_mo = {
                    "product_id": line.product_id.id,
                    "bom_id": line.bom_id.id,
                    "product_qty": line.qty,
                    "product_uom_id": line.bom_id.product_uom_id.id,
                    "company_id": self.env.company.id,
                    "peel_diss_assy_id": rec.id,
                    "picking_type_id": rec.job.op_type_ok.id,
                    "location_src_id": rec.job.source_location_ok.id,
                    "location_dest_id": rec.job.dest_location_ok.id,
                    "move_raw_ids": []
                }
                for c in line.peel_diss_assy_component_line:
                    new_mo['move_raw_ids'].append([0,0, {
                        "product_id": c.product_id.id,
                        "product_uom": c.product_id.uom_id.id,
                        "product_uom_qty": float(c.peeled_total),
                        "name": "New",
                        "picking_type_id": rec.job.op_type_ok.id,
                        "location_id": rec.job.source_location_ok.id,
                        "location_dest_id": rec.job.dest_location_ok.id
                    }])

                if new_mo:
                    mo = self.env['mrp.production'].sudo().create(new_mo)
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
                                'consumption': line.bom_id.consumption,
                                'serial': bool(serial_finished)
                            })
                            prod._compute_pending_production()
                            prod.do_produce()

                    # set done qty in stock move line
                    # HACK: cause qty done doesn't change / trigger when execute do_produce
                    for rec in mo.move_raw_ids:
                        # stock tidak mencukupi
                        if float(rec.reserved_availability) < float(rec.product_uom_qty):
                            raise UserError(_("item {} pada location {} diperlukan qty {} untuk melanjutkan proses Manufacturing Order.".format(
                                rec.product_id.name, 
                                rec.location_id.location_id.name+'/'+rec.location_id.name, 
                                str(rec.product_uom_qty)
                            )))
                            
                        for line in rec.move_line_ids:
                            line.qty_done = rec.product_uom_qty
                            line.product_uom_qty = float(rec.product_uom_qty)
                            line.lot_produced_ids = finished_lot_id

                    mo.button_mark_done()
                    self._count_mo()

    def create_stock_picking(self):
        def get_total_ok_ng_from_component(line):
            ok, ng = 0, 0
            for c in line.peel_diss_assy_component_line:
                ok += c.ok
                ng += c.ng

            return ok,ng

        sp_ng, sp_ok = {}, {}
        for rec in self:
            sp_ng['picking_type_id'] = rec.job.op_type_ng.id
            sp_ng['location_id'] = rec.job.source_location_ng.id or self.env['stock.warehouse']._get_partner_locations()[1].id
            sp_ng['location_dest_id'] = rec.job.dest_location_ng.id or self.env['stock.warehouse']._get_partner_locations()[1].id
            sp_ng['peel_diss_assy_id'] = self.id
            sp_ng['name'] = '/'

            sp_ok['picking_type_id'] = rec.job.op_type_ok.id
            sp_ok['location_id'] = rec.job.source_location_ok.id or self.env['stock.warehouse']._get_partner_locations()[1].id
            sp_ok['location_dest_id'] = rec.job.dest_location_ok.id or self.env['stock.warehouse']._get_partner_locations()[1].id
            sp_ok['peel_diss_assy_id'] = self.id
            sp_ok['name'] = '/'

            sp_ng['move_lines'], sp_ok['move_lines'] = [], []
            for line in self.peel_diss_assy_line:
                product = line.product_id.with_context(lang=self.env.user.lang)
                ok, ng = get_total_ok_ng_from_component(line)
                name_desc = product.partner_ref
                sp_ng['move_lines'].append((0,0, {
                    'product_id': line.product_id.id,
                    'product_uom_qty': ng,
                    'description_picking': name_desc,
                    'product_uom': line.product_id.uom_id.id,
                    'name': name_desc
                }))

                sp_ok['move_lines'].append((0,0, {
                    'product_id': line.product_id.id, 
                    'product_uom_qty': ok,
                    'description_picking': name_desc,
                    'product_uom': line.product_id.uom_id.id,
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
    

class PeelDissAssyLine(inheritModel):
    _name = "peel.diss.assy.line"
    _description = "Detail Job of Peel Diss Assy"

    peel_diss_assy_id = fields.Many2one(
        'peel.diss.assy', 
        'Peel Diss Assy Line ID', 
        ondelete='cascade', 
        index=True
    )
    user = fields.Many2one('employee.custom', string='Operator', required=True, domain=_get_domain_user)
    product_id = fields.Many2one('product.product', string='Produk', required=True)
    product_template_id = fields.Many2one(
        'product.template', string='Product Template', compute="get_product_template", store=True, 
        readonly=True)
    bom_id = fields.Many2one(
        'mrp.bom', 
        string='BOM', 
        required=True, 
        compute='get_first_bom', 
        store=True,
        copy=True,
        readonly=False
    )
    description = fields.Text(string="Description")
    peel_diss_assy_component_line = fields.One2many(
        'peel.diss.assy.component.line', 
        'peel_diss_assy_line_id', 
        'Peel Diss Assy Componen Line',
        compute="fetch_component_bom",
        store=True,
        readonly=False,
        copy=True,
        auto_join=True
    )
    qty = fields.Float(string='Quantity')

    @api.depends('product_id')
    def get_product_template(self):
        for rec in self:
            product_template = None
            if rec.product_id:
                product_template = rec.product_id.product_tmpl_id.id
            rec.product_template_id = product_template

    @api.depends('product_id')
    def get_first_bom(self):
        for rec in self:
            bom = None
            if rec.product_id:
                bom = self.env['mrp.bom'].sudo().search([('product_tmpl_id', '=', rec.product_id.product_tmpl_id.id)])
                if bom:
                    bom = bom[0].id

            rec.update({'bom_id': bom})
                    
    @api.depends('bom_id')
    def fetch_component_bom(self):
        list_component = []
        for rec in self:
            rec.peel_diss_assy_component_line = [(5,0,0)]
            if 'bom_id' in rec and rec.bom_id:
                for component in rec.bom_id.bom_line_ids or []:
                    list_component.append((0,0,{'product_id': component.product_id.id}))
            rec.peel_diss_assy_component_line =  list_component

    @api.onchange('qty')
    def validate_peeled_total(self):
        for rec in self:
            for c in rec.peel_diss_assy_component_line:
                if c.ng and c.ok and rec.qty != c.peeled_total:
                    return _warn_qty_not_valid(rec.qty)


class PeelDissAssyComponentLine(inheritModel):
    _name = "peel.diss.assy.component.line"
    _description = "Compoent Kupas Diss Assy"
    
    peel_diss_assy_line_id = fields.Many2one(
        'peel.diss.assy.line', 
        string='Peel Diss Assy Line ID', 
        ondelete="cascade", 
        index=True
    )
    product_id = fields.Many2one('product.product', string='Component', required=True, readonly=True, store=True)
    peeled_total = fields.Float(string="Total yang dikupas", compute="_validate_ng_ok", readonly=True, store=True)
    ok = fields.Float(string='OK', store=True)
    ng = fields.Float(string='NG', store=True)

    def write(self, vals):
        return super(PeelDissAssyComponentLine, self).write(vals)

    @api.depends('ok', 'ng')
    def _validate_ng_ok(self):
        """
        validate field ng + ok = peeled_total
        """
        for rec in self:
            rec.peeled_total = rec.ng + rec.ok

    @api.onchange('peeled_total')
    def validate_peeled_total(self):
        qty = self.peel_diss_assy_line_id.qty
        for c in self:
            if c.ng and c.ok and qty != c.peeled_total:
                return _warn_qty_not_valid(qty)

def _warn_qty_not_valid(qty):
    return  {'warning':{
        'title':('Warning'),
        'message':_("Total OK + NG (total kupas) harus = %s (acuan qty product) " % (qty))
    }}