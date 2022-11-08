from odoo import _
from odoo.exceptions import UserError

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