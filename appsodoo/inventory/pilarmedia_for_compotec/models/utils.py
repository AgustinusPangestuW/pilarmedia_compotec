from odoo import _
from odoo.http import request
from odoo.exceptions import UserError, ValidationError
from odoo.addons.stock.models.stock_move import StockMove
from odoo.tests import Form

def domain_location_by_vendor(self):
    domain = []

    if self.env.user and self.env.user.vendors:
        locations = get_location_by_vendor(self)

        if locations:
            domain = [('id', 'in', locations)]

    return domain

def get_location_by_vendor(self):
    warehouses = request.env['stock.warehouse'].sudo().search([('vendor', 'in', [v.id for v in self.env.user.vendors])])
    locations = []
    for w in warehouses:
        locations += get_location_from_warehouse(w.view_location_id.id, [])
    return locations

def get_location_from_warehouse(location_id, locations=[]):
    locations_base_on_parent = request.env['stock.location'].sudo().search([('location_id', '=', location_id)])
    
    for i in locations_base_on_parent:
        if i.id not in locations: locations.append(i.id)
        
        get_location_from_warehouse(i.id, locations)

    return locations

def validate_reserved_qty(stock_picking:object):
    for rec in stock_picking:
        required_items = []
        for line in rec.move_ids_without_package:
            if line.reserved_availability < line.product_uom_qty or StockMove._should_bypass_reservation(line):
                required_items.append(line)
                
        if required_items:
            raise UserError(_('Item {} pada location {} diperlukan Qty {} {}.').format(
                required_items[0].product_id.name, 
                rec.location_id.location_id.name + '/' + rec.location_id.name,
                required_items[0].product_uom_qty,
                required_items[0].product_uom.name
            ))

def fill_done_qty(stock_picking:object):
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
            todo_uom = self.env['uom.uom'].search([
                ('category_id', '=', production.product_uom_id.category_id.id), 
                ('uom_type', '=', 'reference')
            ]).id
    
    return todo_quantity, todo_uom, serial_finished

def return_sp(picking_id:object):
    stock_return_picking_form = Form(request.env['stock.return.picking']
        .with_context(active_ids=picking_id.ids, active_id=picking_id.ids[0],
        active_model='stock.picking'))
    stock_return_picking = stock_return_picking_form.save()
    stock_return_picking._onchange_picking_id()

    qty_stock_move = {}
    for prm in stock_return_picking.product_return_moves:
        sm = request.env['stock.move'].search([('id', '=', prm.move_id.id), ('product_id', '=', prm.product_id.id)])
        qty_stock_move[prm.product_id.id] = (qty_stock_move.get(prm.product_id.id) or 0) + prm.quantity

    stock_return_picking_action = stock_return_picking.create_returns()
    return_pick = request.env['stock.picking'].browse(stock_return_picking_action['res_id'])
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