from odoo import models, fields, api, _
from odoo.exceptions import UserError

class InheritMrpBOM(models.Model):
    _inherit = 'mrp.bom'

    initial_bom = fields.Boolean(string='Initial BOM ?', help="if active is for flag BOM initial Product")   
                        