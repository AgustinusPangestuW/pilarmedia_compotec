from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ..models.inherit_stock_picking import make_another_stock_pick_if_subcon

class InheritStockImmediateTransfer(models.TransientModel):
    _inherit = 'stock.immediate.transfer'

    def process(self):
        res = None
        for sp in self.pick_ids:
            if sp.picking_type_id.is_subcon:
                res = super().process()

                if not res:
                    res = make_another_stock_pick_if_subcon(sp)

        return res