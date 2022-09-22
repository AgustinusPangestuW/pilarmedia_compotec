from odoo import models, fields, api, _

class InheritResUsers(models.Model):
    _inherit = 'res.users'

    warehouses = fields.Many2many(
        'stock.warehouse', 
        string='Warehouses',
        relation='res_users_warehouse_rel'
    )    