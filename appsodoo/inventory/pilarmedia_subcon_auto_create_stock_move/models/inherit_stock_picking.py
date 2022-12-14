from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form
import copy

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    stock_picking_subcont_ref_id = fields.Many2one(
        'stock.picking', 
        string='Stock Picking ID creator for Subcon', 
        tracking=True,
        readonly=True,
        copy=False
    )
    location_src_id_subcon = fields.Many2one(
        'stock.location', 
        string='Source Location', 
        readonly=True,
        copy=False
    )
    vendor_src_id_subcon = fields.Many2many(
        'res.partner', 
        string='Vendor src Subcon', 
        compute="_fill_vendor_from_src_id_subcon", 
        store=True
    )
    location_dest_id_subcon = fields.Many2one(
        'stock.location', 
        string='Destination Location', 
        readonly=True,
        copy=False
    )
    count_stock_picking_created = fields.Integer(
        string='Count Stock Pick Created', 
        readonly=1, 
        compute="_count_stock_picking_created",
        store=1,
        copy=False
    )

    @api.depends('location_src_id_subcon')
    def _fill_vendor_from_src_id_subcon(self):
        vendor = None
        for rec in self:
            if rec.location_src_id_subcon:
                warehouse = self.get_warehouse(rec.location_src_id_subcon)
                if warehouse:
                    vendor = warehouse.vendor.id
            rec.vendor_src_id_subcon = vendor

    state = fields.Selection(selection_add =[
        ('reject', 'Rejected'), ('waiting',),
        ('need_approval', 'Need Approval'), ('assigned',)],
        help=" * Draft: The transfer is not confirmed yet. Reservation doesn't apply.\n"
             " * Waiting another operation: This transfer is waiting for another operation before being ready.\n"
             " * Waiting: The transfer is waiting for the availability of some products.\n(a) The shipping policy is \"As soon as possible\": no product could be reserved.\n(b) The shipping policy is \"When all products are ready\": not all the products could be reserved.\n"
             " * Rejected: The transfer has been Rejected by user Approval.\n"
             " * Ready: The transfer is ready to be processed.\n(a) The shipping policy is \"As soon as possible\": at least one product has been reserved.\n(b) The shipping policy is \"When all products are ready\": all product have been reserved.\n"
             " * Done: The transfer has been processed.\n"
             " * Cancelled: The transfer has been cancelled.\n")
    approved_by = fields.Many2one('res.users', string='Approved By')
    rejected_by = fields.Many2one('res.users', string='Rejected By')
    is_approval = fields.Boolean(string='Approval ?', compute="_compute_is_approval")
    restrict_user_for_approve = fields.Boolean(string='restrict user for approve ?', compute="_compute_is_approval")
    location_src = fields.Many2one(
        'stock.location', 
        string='Destination Location', 
        readonly=True,
        copy=False,
        help="location src for show in tree",
        compute="_get_location_src_for_show"
    )
    location_dest = fields.Many2one(
        'stock.location', 
        string='Destination Location', 
        readonly=True,
        copy=False,
        help="location destination for show in tree",
        compute="_get_location_dest_for_show"
    )
    users_waiting_approval = fields.Many2many(
        comodel_name='res.users', 
        relation='users_waiting_approval_rel',
        string='User Waiting Approval',
        copy=False,
        store=True
    )

    def write(self, vals):
        # reset value `users_waiting_approval` 
        # filled value in field `users_waiting_approval` by system 
        # when auto create step2 stock picking (autocreate stock picking)
        for rec in self:
            if rec.state == 'done':
                vals['users_waiting_approval'] = [(5,0,0)]
        return super().write(vals)

    def action_assign(self):
        super().action_assign()

        if (self.picking_type_id.is_subcon):
            for sm in self.move_ids_without_package:
                if float(sm.reserved_availability) < float(sm.product_uom_qty):
                    raise ValidationError(_("Item {item} memerlukan Qty {product_uom_qty} {uom} pada location {location} untuk melanjutkan proses. Stock tersedia {reserved_qty} {uom}.".format(
                        item=sm.product_id.name,
                        product_uom_qty=sm.product_uom_qty,
                        uom=sm.product_uom.name,
                        location=(sm.location_id.location_id.name or "")+ '/' + sm.location_id.name,
                        reserved_qty=sm.reserved_availability
                    )))
        
    @api.depends('location_id', 'location_src_id_subcon')
    def _get_location_src_for_show(self):
        for rec in self:
            if rec.location_src_id_subcon:
                rec.location_src = rec.location_src_id_subcon
            else:
                rec.location_src = rec.location_id

    @api.depends('location_dest_id', 'location_dest_id_subcon')
    def _get_location_dest_for_show(self):
        for rec in self:
            if rec.location_dest_id_subcon:
                rec.location_dest = rec.location_dest_id_subcon
            else:
                rec.location_dest = rec.location_dest_id
    
    @api.depends('state')
    def _compute_is_approval(self):
        is_approval = False
        restrict_user_for_approve = False
        for rec in self:
            if self.picking_type_id.approvals and rec.state in ["assigned", "need_approval"]:
                is_approval = True
                rec.state = "need_approval"
                if self.env.user in self.picking_type_id.approvals:
                    restrict_user_for_approve = False
                else: restrict_user_for_approve = True
            rec.is_approval = is_approval
            rec.restrict_user_for_approve = restrict_user_for_approve


    def button_approve(self):
        for rec in self:
            rec.approved_by = self.env.user.id
        return self.button_validate()

    def button_reject(self):
        for rec in self:
            rec.rejected_by = self.env.user.id
            rec.state = "reject"

        if self.stock_picking_subcont_ref_id:
            stock_picking_subcont_maker = self.stock_picking_subcont_ref_id

            stock_return_picking_form = Form(self.env['stock.return.picking']
                .with_context(active_ids=stock_picking_subcont_maker.ids, active_id=stock_picking_subcont_maker.ids[0],
                active_model='stock.picking'))
            stock_return_picking = stock_return_picking_form.save()
            stock_return_picking._onchange_picking_id()

            qty_stock_move = {}
            for prm in stock_return_picking.product_return_moves:
                sm = self.env['stock.move'].search([('id', '=', prm.move_id.id), ('product_id', '=', prm.product_id.id)])
                qty_stock_move[prm.product_id.id] = (qty_stock_move.get(prm.product_id.id) or 0) + prm.quantity

            stock_return_picking_action = stock_return_picking.create_returns()
            return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
            return_pick.action_assign()

            # Validate Qty return base on Stock Picking
            for sm in return_pick.move_lines:
                if float(sm.reserved_availability) < float(qty_stock_move[sm.product_id.id] or 0):
                    raise ValidationError(_("item {item} membutuhkan Qty {qty} {uom} pada location {loc} untuk melanjutkan proses. Stock tersedia {reserved_qty} {uom}.").format(
                        item=sm.product_id.name,
                        qty=sm.product_uom_qty,
                        uom=sm.product_uom.name,
                        loc=(sm.location_id.location_id.name or "") + '/' + sm.location_id.name,
                        reserved_qty=sm.reserved_availability
                    ))
                else:
                    for sml in sm.move_line_ids:
                        sml.qty_done = sml.product_uom_qty

            return_pick.action_done()

    def button_validate(self):
        res_validate = super(StockPicking, self).button_validate()
        self = edit_dest_loc_into_transit(self)

        if res_validate:
            return res_validate

        self = make_another_stock_pick_if_subcon(self)
        return self

    def _count_stock_picking_created(self):
        for rec in self:
            rec.count_stock_picking_created = rec.env['stock.picking'].sudo().search_count([('stock_picking_subcont_ref_id', '=', rec.id)])

    def action_see_stock_move_created(self):
        list_domain = []
        if 'active_id' in self.env.context:
            list_domain.append(('stock_picking_subcont_ref_id', '=', self.env.context['active_id']))
        
        return {
            'name':_('Transfers'),
            'domain':list_domain,
            'res_model':'stock.picking',
            'view_mode':'tree,form',
            'type':'ir.actions.act_window',
        }


#######################################################################################################

def edit_dest_loc_into_transit(self):
    for rec in self:
        if rec.picking_type_id.is_subcon and rec.picking_type_id.operation_type_id:
            # ditampung ke variable untuk ditampilkan
            self.env['stock.picking'].sudo().search([('id', '=', rec.id)]).write(
                {'location_dest_id_subcon': rec.location_dest_id.id})

            if rec.picking_type_id.operation_type_id.default_location_src_id:
                # destination warehouse isikan dengan warehouse transit
                self.env['stock.picking'].sudo().search([('id', '=', rec.id)]).write(
                    {'location_dest_id': rec.picking_type_id.operation_type_id.default_location_src_id.id})

                # rubah destinasi location per item 
                for line in rec.move_line_ids_without_package:
                    self.env['stock.move.line'].sudo().search([('id', '=', line.id)]).write(
                        {'location_dest_id': rec.picking_type_id.operation_type_id.default_location_src_id.id})
            else:
                # field transit location kosong
                raise UserError(_("Field Default Source Location in next Operation Type %s is null." % rec.picking_type_id.name ))

    return self

def make_another_stock_pick_if_subcon(self):
    new_sm = {}
    for rec in self:
        if rec.picking_type_id.is_subcon and rec.picking_type_id.operation_type_id:
            # Mapping data stock picking
            new_sm.update(_collect_stock_picking(rec))

            if self.env.context.get('uid'):
                new_sm.update({"users_waiting_approval": [(4, self.env.context.get('uid'))] })
            
            for line in rec.move_line_ids_without_package:
                # isikan line (move_line_ids_without_package) karena mau membuat `transfer immediate` 
                dict_line = _copy_line(rec, line)
                new_sm['move_line_ids_without_package'].append((0,0, dict_line))
    
    if new_sm:
        st_subcon_created = self.env['stock.picking'].sudo().create(new_sm)
        st_subcon_created.update({'state': 'assigned'})
        # merubah state ke ready pada Immediate Transfer
        # st_subcon_created.button_validate()
        
        # ini state saat transfer planned
        # st_subcon_created.action_confirm()
        # st_subcon_created.action_assign()
        
    self._count_stock_picking_created()

    return self

def _copy_line(rec, line):
    return {
        'location_id': rec.picking_type_id.operation_type_id.default_location_src_id.id,
        'location_dest_id': rec.location_dest_id_subcon.id,
        'product_id': line.product_id.id,
        'product_uom_id': line.product_uom_id.id,
        'product_uom_qty': line.product_uom_qty,
        'qty_done': line.qty_done,
        'lot_id': line.lot_id.id or '',
        'lot_name': line.lot_name or '',
        'description_picking': line.description_picking or '',
        'lot_produced_qty': line.lot_produced_qty or '',
        'picking_id': rec.id
    }

def _collect_stock_picking(rec):
    return {
        'name': rec.name + "-R",
        'message_main_attachment_id': rec.message_main_attachment_id.id or '',
        'origin': rec.origin,
        'note': rec.note,
        'backorder_id': rec.backorder_id.id,
        'partner_id': rec.partner_id.id,
        # 'sale_id': rec.sale_id.id or '',
        # 'website_id': rec.website_id.id,
        'vehicle_id': rec.vehicle_id.id,
        'driver_id': rec.driver_id,
        'location_src_id_subcon': int(rec.location_id.id),
        'location_id': rec.picking_type_id.operation_type_id.default_location_src_id.id,
        'location_dest_id': rec.location_dest_id_subcon.id,
        'location_dest_id_subcon': None,
        'stock_picking_subcont_ref_id': rec.id,
        'picking_type_id': rec.picking_type_id.operation_type_id.id if rec.picking_type_id.operation_type_id.id else rec.picking_type_id.id,
        'immediate_transfer': True,
        'move_line_ids_without_package': [],
        'surat_jalan_id': rec.id,
        'vehicle_id': rec.vehicle_id.id,
        'driver_id': rec.driver_id.id
    }