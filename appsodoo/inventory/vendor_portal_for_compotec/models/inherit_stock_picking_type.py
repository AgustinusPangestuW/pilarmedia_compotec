from odoo import models, fields, api, _
from odoo.exceptions import UserError

class InheritStockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    name_base_on_supplier = fields.Boolean(string='Create name base on supplier code ?')
    