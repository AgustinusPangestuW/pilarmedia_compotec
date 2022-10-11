from odoo import models, fields, api, _
from odoo.exceptions import UserError
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

    def button_validate(self):
        self = edit_dest_loc_into_transit(self)
        res_validate = super(StockPicking, self).button_validate()

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
        if rec.picking_type_id.is_subcon and not self.stock_picking_subcont_ref_id:
            # ditampung ke variable untuk ditampilkan
            rec.location_dest_id_subcon = int(rec.location_dest_id.id)

            if rec.picking_type_id.transit_location_id:
                # destination warehouse isikan dengan warehouse transit
                rec.update({'location_dest_id' : rec.picking_type_id.transit_location_id.id})

                # rubah destinasi location per item 
                for line in rec.move_line_ids_without_package:
                    line.update({"location_dest_id": int(rec.picking_type_id.transit_location_id.id)})
            else:
                # field transit location kosong
                raise UserError(_("Field Transit Location in Operation Type %s is null." % rec.picking_type_id.name ))

    return self

def make_another_stock_pick_if_subcon(self):
    new_sm = {}
    for rec in self:
        if rec.picking_type_id.is_subcon and not self.stock_picking_subcont_ref_id:
            # Mapping data stock picking
            new_sm.update(_collect_stock_picking(rec))
            
            for line in rec.move_line_ids_without_package:
                # isikan line (move_line_ids_without_package) karena mau membuat `transfer immediate` 
                dict_line = _copy_line(rec, line)
                new_sm['move_line_ids_without_package'].append((0,0, dict_line))
    
    if new_sm:
        st_subcon_created = self.env['stock.picking'].sudo().create(new_sm)
        # merubah state ke ready pada Immediate Transfer
        st_subcon_created.button_validate()
        
        # ini state saat transfer planned
        # st_subcon_created.action_confirm()
        # st_subcon_created.action_assign()
        
    self._count_stock_picking_created()

    return self

def _copy_line(rec, line):
    return {
        'location_id': rec.picking_type_id.transit_location_id.id,
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
        'location_id': rec.picking_type_id.transit_location_id.id,
        'location_dest_id': rec.location_dest_id_subcon.id,
        'location_dest_id_subcon': '',
        'stock_picking_subcont_ref_id': rec.id,
        'picking_type_id': rec.picking_type_id.id,
        'immediate_transfer': True,
        'move_line_ids_without_package': []
    }