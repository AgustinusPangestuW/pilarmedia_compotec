from odoo import models, fields, api

class LogOutstandingQty(models.Model):
    _name = 'log.outstanding.qty'

    move_id = fields.Many2one(
        'stock.move', 
        string='Stock Move ID', 
        ondelete="cascade",
        index=True,
        readonly=True
    )
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    picking_id = fields.Many2one('stock.picking', string='Stock Picking ID', readonly=True)
    done_qty = fields.Float(string='Done Qty', readonly=True)    
    remaining_qty = fields.Float(string='Remaining Qty', readonly=True)    