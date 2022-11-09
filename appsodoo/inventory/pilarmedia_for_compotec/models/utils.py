from odoo import _
from odoo.http import request
from odoo.exceptions import UserError

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
        for line in rec.move_ids_without_package:
            if line.reserved_availability < line.product_uom_qty:
                raise UserError(_('Item {} pada location {} diperlukan Qty {} {}.').format(
                    line.product_id.name, 
                    rec.location_id.location_id.name + '/' + rec.location_id.name,
                    line.product_uom_qty,
                    line.product_uom.name
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