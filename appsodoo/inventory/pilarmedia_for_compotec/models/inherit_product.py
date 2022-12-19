from odoo import models, fields, api, _
from odoo.exceptions import UserError

class InheritProduct(models.Model):
    _inherit = 'product.product'


    