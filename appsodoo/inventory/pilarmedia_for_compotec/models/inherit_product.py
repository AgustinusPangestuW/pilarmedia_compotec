from odoo import models, fields, api, _
from odoo.exceptions import UserError

class InheritProduct(models.Model):
    _inherit = 'product.product'

    qty_available = fields.Float(groups="group_stock_manager")
    virtual_available = fields.Float(groups="group_stock_manager")
    standard_price = fields.Float(groups="group_stock_manager")
    lst_price  = fields.Float(groups="group_stock_manager")

    