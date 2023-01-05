from odoo import models, fields, api, _
from odoo.exceptions import UserError

class InheritAccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    wholesale_job_line_id = fields.Many2one(
        'wholesale.job.line', 
        string='Wholesale Job Line ID', 
        ondelete='restrict',
        help="created base on Wholesale Job"
    )





    