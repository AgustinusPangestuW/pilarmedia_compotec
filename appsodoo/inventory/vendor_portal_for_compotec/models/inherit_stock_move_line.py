from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.fields import first

class InheritStockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def set_lot_auto(self):
        """
            Create lots using create_multi to avoid too much queries
            As move lines were created by product or by tracked 'serial'
            products, we apply the lot with both different approaches.
        """
        values = []
        production_lot_obj = self.env["stock.production.lot"]
        lots_by_product = dict()
        for line in self:
            values.append(line._prepare_auto_lot_values())
        active_picking_id = self.picking_id if 'picking_id' in self else None
        lots = production_lot_obj.with_context({'active_picking_id': active_picking_id.id}).create(values)
        for lot in lots:
            if lot.product_id.id not in lots_by_product:
                lots_by_product[lot.product_id.id] = lot
            else:
                lots_by_product[lot.product_id.id] += lot
        for line in self:
            lot = first(lots_by_product[line.product_id.id])
            line.lot_id = lot
            if lot.product_id.tracking == "serial":
                lots_by_product[line.product_id.id] -= lot

    