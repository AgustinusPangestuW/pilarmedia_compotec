from odoo import models, fields, api, _
from odoo.exceptions import UserError

class InheritPurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition.line'

    product_id = fields.Many2one('product.product', string='Product', domain=[], required=True)

    