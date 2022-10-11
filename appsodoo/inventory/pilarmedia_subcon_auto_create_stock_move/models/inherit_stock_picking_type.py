from odoo import models, fields, api, _
from odoo.exceptions import UserError

class InheritStockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    approvals = fields.Many2many(
        comodel_name='res.users', 
        relation='users_approvals_rel',
        string='Approvals'
    )
   
    