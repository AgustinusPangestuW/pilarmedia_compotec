from odoo import models, fields, api, _
from odoo.exceptions import UserError

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

    @api.depends('seller_ids')
    def get_vendor_from_seller_ids(self):
        for rec in self:
            rec.vendors = [(4, i.name.id) for i in rec.seller_ids]
   