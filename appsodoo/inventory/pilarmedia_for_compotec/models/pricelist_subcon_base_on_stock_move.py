from odoo import models, fields, api

class PricelistSubconBaseonStockMove(models.Model):
    _name = 'pricelist.subcon.baseon.stockmove'

    picking_id = fields.Many2one(
        'stock.picking', 
        string='Stock Picking ID', 
        readonly=True,
        index=True
    )
    move_id = fields.Many2one(
        'stock.move', 
        string='Stock Move ID',
        readonly=True,
        index=True,
        ondelete='cascade'
    )
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    price_total = fields.Float(
        string='Price Total', 
        readonly=True,
        compute="_calculate_total_price",
        store=True
    )
    vendor = fields.Many2one('res.partner', string='Vendor', compute="_onchange_vendor", store=True)
    lines = fields.One2many('pricelist.subcon.baseon.stockmove.line', 'pricelist_subcon_id', 'Line')
   
    @api.depends('lines.price_total')
    def _calculate_total_price(self):
        price_total = 0

        for rec in self:
            for line in rec.lines:
                price_total += line.price_total
        
            rec.update({'price_total': price_total})    

    @api.depends('picking_id.vendor')
    def _onchange_vendor(self):
        vendor = None
        for rec in self:
            if rec.picking_id.vendor:
                vendor = rec.picking_id.vendor
            rec.update({'vendor': vendor})


class PricelistSubconBaseonStockMoveLine(models.Model):
    _name = 'pricelist.subcon.baseon.stockmove.line'

    pricelist_subcon_id = fields.Many2one(
        'pricelist.subcon.baseon.stockmove', 
        'Pricelist Subcon ID',
        index=True, 
        ondelete='cascade'
    )
    pricelist_id = fields.Many2one(
        'pilar.pricelist', 
        string='Pricelist Subcon', 
        reuqired=True
    )
    price = fields.Float(string='Price', compute="_get_price", store=True, readonly=False)
    qty = fields.Float(string='Quantity', default="1")
    price_total = fields.Float(
        string='Price Total', 
        readonly=True,
        compute="_calculate_total_price",
        store=True
    )

    @api.depends('pricelist_id')
    def _get_price(self):
        for rec in self:
            if rec.pricelist_id:
                rec.update({'price': rec.pricelist_id.price or 0})

    @api.depends('price', 'qty')
    def _calculate_total_price(self):
        for rec in self:
            price = rec.price or 0
            qty = rec.qty or 0
            rec.update({
                'price_total': price * qty
            })