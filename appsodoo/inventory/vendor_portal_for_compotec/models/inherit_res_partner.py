from odoo import models, fields, api, _
from odoo.exceptions import UserError

class InheritResPartner(models.Model):
    _inherit = 'res.partner'

    code = fields.Char(string='Code', copy=False)
    is_approve = fields.Boolean(string='Approve?', copy=False, default=1)
    is_supplier = fields.Boolean(string='Is Supplier?', copy=False)
    with_confirm_date = fields.Boolean(string='With Confirmation Date ?', default=1)
    npwp = fields.Char(string='NPWP')
    npwp_name = fields.Char(string='Nama NPWP')
    npwp_address = fields.Char(string='Alamat NPWP')
    product_categories = fields.Many2many(
        comodel_name='product.category', 
        relation='prod_categ_res_partner',
        string='Product Categories'
    )

    _sql_constraints = [
        ('vendor_code_uniq', 'unique(code)', 'Code Vendor must be unique!'),
    ]
   