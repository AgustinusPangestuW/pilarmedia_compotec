from odoo import models, fields, api, _
from odoo.exceptions import UserError

class InheritPurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    states = fields.Selection([
        ("draft", "Draft"),
        ("to_approve", "To be approved"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("done", "Done"),
    ])
        