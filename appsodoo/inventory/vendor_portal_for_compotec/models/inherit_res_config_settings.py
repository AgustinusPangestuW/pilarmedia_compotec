
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class resConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    vendor_pricelist_base_on = fields.Selection(
        selection=[
            ('standard', 'First Pricelist'),
            ('last_purchase', 'Last Purchase'),
            ('average_purchase', 'Average Purchase'),
        ],
        default="standard",
        string="Vendor pricelist base on", 
        config_parameter='vendor_pricelist_base_on'
    )
        
    def get_values(self):
        res = super(resConfigSettings, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        vendor_pricelist_base_on = ICPSudo.get_param('vendor_pricelist_base_on')
        res.update(
            vendor_pricelist_base_on=vendor_pricelist_base_on
        )
        return res

