from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PilarPricelist(models.Model):
    _name = 'pilar.pricelist'
    _rec_name='product_id'

    name = fields.Char(string='Code')
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Price Item',
        domain="[('product_tmpl_id.type', '=', 'service')]"
        )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Vendor Subcon'
        )
    price = fields.Float(string='Unit Price',digits=(6,2))
    pricelist_ids = fields.One2many(comodel_name='pilar.pricelist.line', inverse_name='pricelist_id', string='Detail Product')

class PilarPricelistLine(models.Model):   
    _name = 'pilar.pricelist.line'

    name = fields.Char(string='Description')
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product Item',
        domain="[('product_tmpl_id.type', '=', 'product')]"
        )
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    unit_price = fields.Float(string='Unit Price',digits=(6,2))
    pricelist_id = fields.Many2one('pilar.pricelist', string='Pricelist')  

    @api.onchange('product_id')
    def set_uom(self):
        self.uom_id = self.product_id.product_tmpl_id.uom_id
        # return {'domain': [('id', 'in', employee_list)]}
      
   