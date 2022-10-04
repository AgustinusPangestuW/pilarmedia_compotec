from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ..models.inherit_stock_picking import edit_dest_loc_into_transit, make_another_stock_pick_if_subcon

class StockBackorderConfirmation(models.TransientModel):
    _inherit = 'stock.backorder.confirmation'

    def process(self):
        for stock_picking in self.pick_ids:
            sp = edit_dest_loc_into_transit(stock_picking)
            
            res_validate = super().process()

            if res_validate:
                return res_validate

            sp = make_another_stock_pick_if_subcon(sp)
        return self

    

    
