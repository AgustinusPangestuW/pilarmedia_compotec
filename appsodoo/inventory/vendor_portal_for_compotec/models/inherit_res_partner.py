from odoo import models, fields, api, _
from odoo.exceptions import UserError

class InheritResPartner(models.Model):
    _inherit = 'res.partner'

    with_confirm_date = fields.Boolean(string='With Confirmation Date ?', default=1)
    npwp = fields.Char(string='NPWP')
    npwp_name = fields.Char(string='Nama NPWP')
    npwp_address = fields.Char(string='Alamat NPWP')
    product_categories = fields.Many2many(
        comodel_name='product.category', 
        relation='prod_categ_res_partner',
        string='Product Categories'
    )
   