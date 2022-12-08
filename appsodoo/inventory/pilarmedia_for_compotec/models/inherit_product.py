from odoo import models, fields, api, _
from odoo.exceptions import UserError

class InheritProduct(models.Model):
    _inherit = 'product.product'

    qty_available = fields.Float(groups="stock.group_stock_user")
    virtual_available = fields.Float(groups="stock.group_stock_user")
    standard_price = fields.Float(groups="stock.group_stock_user")
    lst_price  = fields.Float(groups="stock.group_stock_user")

    