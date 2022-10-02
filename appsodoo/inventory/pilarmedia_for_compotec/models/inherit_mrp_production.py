from odoo import models, fields, api, _
from odoo.exceptions import UserError

class MRPProduction(models.Model):
    _inherit = 'mrp.production'

    peel_diss_assy_id = fields.Many2one('peel.diss.assy', string='Peel Diss Assy')
    wrapping_id = fields.Many2one('wrapping', string='Wrapping')

    