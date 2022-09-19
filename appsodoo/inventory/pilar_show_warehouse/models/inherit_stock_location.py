from odoo import models, fields, api, _
from odoo.exceptions import UserError

class InheritStockLocation(models.Model):
    _inherit = 'stock.location'

    wh_name = fields.Char(string='Warehouse Name',compute='_compute_wh',store=False)

    @api.depends('complete_name')
    def _compute_wh(self):
        for doc in self:
            cn = doc.complete_name.split('/')
            wh = self.env["stock.warehouse"].search([("code", "=", cn)]).name
            doc.wh_name = wh
    



    