from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    vendor = fields.Many2one(
        'res.partner', 
        string='Vendor Subcon', 
        domain=[('is_subcon', '=', 1)], 
        help="relation with res parner, with is_subcon = 1"
    )

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        if self.env.user.vendors:
            domain += [('vendor', 'in', [v.id for v in self.env.user.vendors])]
        res = super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return res
    

