from odoo import models, fields, api, _
from odoo.exceptions import UserError

class InheritProductTemplate(models.Model):
    _inherit = 'product.template'

    pocket_factor = fields.Integer(string='Kantong', help="this field for default value when fetch in checksheet borongan.")
    qty_available = fields.Float(groups="stock.group_stock_manager")
    virtual_available = fields.Float(groups="stock.group_stock_manager")
    standard_price = fields.Float(groups="stock.group_stock_manager")
    lst_price  = fields.Float(groups="stock.group_stock_manager")