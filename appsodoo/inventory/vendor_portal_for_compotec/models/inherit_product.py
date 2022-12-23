from odoo import models, fields, api, _
from odoo.exceptions import UserError

class InheritProductTemplate(models.Model):
    _inherit = 'product.template'

    supplier_item_code = fields.Char(string='Supplier Item Code')
    vendors = fields.Many2many(
        comodel_name='res.partner', 
        relation='res_partner_product_template',
        string='Vendors',
        compute="get_vendor_from_seller_ids",
        store=True
    )
    # qty_available = fields.Float(groups="stock.group_stock_manager")
    # virtual_available = fields.Float(groups="stock.group_stock_manager")
    # standard_price = fields.Float(groups="stock.group_stock_manager")
    # lst_price  = fields.Float(groups="stock.group_stock_manager")

    @api.depends('seller_ids')
    def get_vendor_from_seller_ids(self):
        for rec in self:
            rec.vendors = [(4, i.name.id) for i in rec.seller_ids]

    @api.model
    def create(self, vals):
        if self.env.user.partner_id.supplier_rank:
            vals['vendors'] = [(4,self.env.user.partner_id.id)]

        return super().create(vals)

class InheritProduct(models.Model):
    _inherit = 'product.product'

    supplier_item_code = fields.Char(string='Supplier Item Code')
    vendors = fields.Many2many(
        comodel_name='res.partner', 
        relation='res_partner_product',
        string='Vendors',
        compute="get_vendor_from_seller_ids",
        store=True
    )
    # qty_available = fields.Float(groups="stock.group_stock_manager")
    # virtual_available = fields.Float(groups="stock.group_stock_manager")
    # standard_price = fields.Float(groups="stock.group_stock_manager")
    # lst_price  = fields.Float(groups="stock.group_stock_manager")

    @api.depends('seller_ids')
    def get_vendor_from_seller_ids(self):
        for rec in self:
            rec.vendors = [(4, i.name.id) for i in rec.seller_ids]
   