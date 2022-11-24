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
    qty_base_on_sj_master = fields.Float(string='Qty', readonly=True, help="Qty base on Master Surat Jalan")    
    last_done_qty = fields.Float(string='Last Done Qty', readonly=True, help="Done Qty before this transaction")    
    done_qty = fields.Float(string='Done Qty', readonly=True, help="Done Qty in this transaction")    
    remaining_qty = fields.Float(string='Remaining Qty', readonly=True, compute="calculate_remaining_qty", store=True)    
    # bom_id = fields.Many2one('mrp.bom', string='BOM ID')

    @api.depends('done_qty', 'qty_base_on_sj_master', 'last_done_qty')
    def calculate_remaining_qty(self):
        for rec in self:
            rec.remaining_qty = rec.qty_base_on_sj_master - (rec.done_qty + rec.last_done_qty)