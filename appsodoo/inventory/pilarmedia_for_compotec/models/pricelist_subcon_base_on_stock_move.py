from odoo import models, fields, api

class PricelistSubconBaseonStockMove(models.Model):
    _name = 'pricelist.subcon.baseon.stockmove'

    move_id = fields.Many2one(
        'stock.move', 
        string='Stock Move ID',
        readonly=True,
        index=True,
        ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product', 
        string='Product', 
        readonly=True,
        compute="_onchange_product",
        store=True
    )
    price_total = fields.Float(
        string='Price Total', 
        readonly=True,
        compute="_calculate_total_price",
        store=True
    )
    qty_in_stock_move_line = fields.Float(
        string='Qty', 
        readonly=1,
        compute="_onchange_qty",
        store=True
    )
    uom_in_stock_move_line = fields.Char(
        string='UOM', 
        readonly=1,
        compute="_onchange_uom",
        store=True
    )
    vendor = fields.Many2one(
        'res.partner', 
        string='Vendor', 
        compute="_onchange_vendor", 
        store=True
    )
    lines = fields.One2many(
        'pricelist.subcon.baseon.stockmove.line', 
        'pricelist_subcon_id', 
        'Line'
    )
   
    @api.depends('lines.price_total')
    def _calculate_total_price(self):
        price_total = 0

        for rec in self:
            for line in rec.lines:
                price_total += line.price_total
        
            rec.update({'price_total': price_total})    

    @api.depends('move_id.picking_id.vendor')
    def _onchange_vendor(self):
        vendor = None
        for rec in self:
            if rec.move_id.picking_id.vendor:
                vendor = rec.move_id.picking_id.vendor
            rec.update({'vendor': vendor})

    @api.depends('move_id.product_id')
    def _onchange_product(self):
        product_id = None
        for rec in self:
            if rec.move_id.product_id:
                product_id = rec.move_id.product_id.id
            rec.update({'product_id': product_id})

    @api.depends('move_id.product_uom_qty')
    def _onchange_qty(self):
        qty = 0
        for rec in self:
            if rec.move_id.product_uom_qty:
                qty = rec.move_id.product_uom_qty
            rec.update({'qty_in_stock_move_line': qty})

    @api.depends('move_id.product_uom')
    def _onchange_uom(self):
        uom_name = ''
        for rec in self:
            if rec.move_id.product_uom:
                uom_name = rec.move_id.product_uom.name
            rec.update({'uom_in_stock_move_line': uom_name})


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

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        # auto calculate when uom == 'set'
        if self.env.context.get('product_id') and self.env.context.get('qty') and self.env.context.get('uom') == "set":
            product = self.env['product.product'].sudo().search([('id', '=', self.env.context.get('product_id'))])
            if len(product):
                bom = self.env['mrp.bom'].sudo().search([('product_tmpl_id', '=', product[0].product_tmpl_id.id)])
                if bom and len(bom) > 0:
                    res['qty'] = self.env.context.get('qty') * bom[0].product_qty

        return res

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