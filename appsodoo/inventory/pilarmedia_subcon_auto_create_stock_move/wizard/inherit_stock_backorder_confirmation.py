from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ..models.inherit_stock_picking import make_another_stock_pick_if_subcon

class StockBackorderConfirmation(models.TransientModel):
    _inherit = 'stock.backorder.confirmation'

    def _process(self, cancel_backorder=False):
        for sp in self.pick_ids:            
            super()._process(cancel_backorder)
            
            if sp.picking_type_id.is_subcon:
                make_another_stock_pick_if_subcon(sp)    

    

    
