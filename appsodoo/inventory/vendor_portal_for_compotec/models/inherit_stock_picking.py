from odoo import models, fields, api, _
from odoo.exceptions import UserError

class InheritStockPicking(models.Model):
    _inherit = 'stock.picking'

    vendor_purchase = fields.Many2one('res.partner', string='Vendor Purchase')

    