from odoo import models, fields, api, _
from odoo.exceptions import UserError

class InheritProductTemplate(models.Model):
    _inherit = 'product.template'

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

    def fill_base_on_partner(self):
        user = self.env.user
        if user and user.partner_id.is_approve:
            return 1
        else: 
            return 0

    sale_ok = fields.Boolean('Can be Sold', default=fill_base_on_partner)
    purchase_ok = fields.Boolean('Can be Purchased', default=fill_base_on_partner)

    @api.depends('seller_ids')
    def get_vendor_from_seller_ids(self):
        for rec in self:
            rec.vendors = [(4, i.name.id) for i in rec.seller_ids]

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

    def fill_base_on_partner(self):
        user = self.env.user
        if user and user.partner_id.is_approve:
            return 1
        else: 
            return 0

    sale_ok = fields.Boolean('Can be Sold', default=fill_base_on_partner)
    purchase_ok = fields.Boolean('Can be Purchased', default=fill_base_on_partner)

    @api.depends('seller_ids')
    def get_vendor_from_seller_ids(self):
        for rec in self:
            rec.vendors = [(4, i.name.id) for i in rec.seller_ids]
   