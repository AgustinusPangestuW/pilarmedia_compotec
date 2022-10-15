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
    sj_id = fields.Many2one('stock.picking', string='Surat Jalan ID', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    picking_id = fields.Many2one('stock.picking', string='Stock Picking ID', readonly=True)
    qty_base_on_sj_master = fields.Float(string='Qty', readonly=True)    
    done_qty = fields.Float(string='Done Qty', readonly=True)    
    remaining_qty = fields.Float(string='Remaining Qty', readonly=True)    