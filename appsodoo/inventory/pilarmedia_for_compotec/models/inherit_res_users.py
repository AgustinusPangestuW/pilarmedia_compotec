from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ResUsers(models.Model):
    _inherit = 'res.users'

    vendors = fields.Many2many(
        comodel_name='res.partner', 
        string='Vendor Subcon', 
        relation='user_partner_rel',
        domain=[('is_subcon', '=', 1)], 
        help="relation with res parner, with is_subcon = 1"
    )
    