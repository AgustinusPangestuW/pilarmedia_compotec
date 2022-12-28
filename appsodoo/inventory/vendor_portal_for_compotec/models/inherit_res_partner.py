from odoo import models, fields, api, _
from odoo.exceptions import UserError

class InheritResPartner(models.Model):
    _inherit = 'res.partner'

    code = fields.Char(string='Code', copy=False)
    is_approve = fields.Boolean(string='Approve?', copy=False, default=1, readonly=True)
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
    payment_periode = fields.Selection([("10/25","10/25"),("non_10/25","Bukan 10/25")], string='Payment Periode',default="non_10/25")

    _sql_constraints = [
        ('vendor_code_uniq', 'unique(code)', 'Code Vendor must be unique!'),
    ]
   
    def approve_vendor(self):
        for rec in self:
            user = self.env['res.users'].sudo().search([('partner_id', '=', rec.id)])
            new_vendor = rec.copy()
            new_vendor.is_approve = 1
            temp = new_vendor.read()

            # MAPPING VALUE
            new_temp = {}  
            for i in temp[0]:
                if type(temp[0][i]) not in (tuple, dict, list):
                    new_temp[i] = temp[0][i]

            new_vendor = self.env['res.partner'].create(new_temp)
            new_vendor.name = rec.name
            user.partner_id = new_vendor.id
            rec.action_archive()
            view = self.env.ref('base.view_partner_form')

            return {
                'name': _('Vendors'),
                'view_mode': 'form',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'res_id': new_vendor.id,
                'res_model': 'res.partner',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'context': dict(
                    self.env.context
                )
            }