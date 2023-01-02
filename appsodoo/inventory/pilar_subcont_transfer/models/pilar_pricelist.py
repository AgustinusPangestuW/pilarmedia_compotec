from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PilarPricelist(models.Model):
    _name = 'pilar.pricelist'
    _rec_name='name'

    name = fields.Char(string='Code', required=True)
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Price Item',
        domain="[('product_tmpl_id.type', '=', 'service')]",
        required=True
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Vendor Subcon',
        required=True,
        domain="[('is_subcon', '=', True)]"
    )
    service_description = fields.Text(string='Jenis Jasa')
    price = fields.Float(string='Unit Price',digits=(6,2))
    pricelist_ids = fields.One2many(comodel_name='pilar.pricelist.line', inverse_name='pricelist_id', string='Detail Product')
    transport = fields.Boolean(string='Transport ?')
    dest_vendor = fields.Many2one('res.partner', string='Destination Vendor', domain="[('is_subcon', '=', True)]")

    @api.onchange('product_id')
    def fetch_name(self):
        for rec in self:
            rec.service_description = rec.product_id.name or ""

    @api.onchange('pricelist_ids', 'pricelist_ids.unit_price')
    def calculate_unit_price_line(self):
        for rec in self:
            rec.price = sum([line.unit_price for line in rec.pricelist_ids])

    def name_get(self):
        res = []
        for rec in self:
            kedua = ''
            # if rec.service_description :
            #     kedua = ' - ' + rec.service_description
            res.append((rec.id,'[%s] %s %s' % (rec.name,rec.product_id.name, kedua )))
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if not args:
            args = []
        domain = args + ['|','|',('name',operator,name),('product_id.name',operator,name),('service_description',operator,name)]
        res = super().search(domain, limit=limit).name_get()
        return res


class PilarPricelistLine(models.Model):   
    _name = 'pilar.pricelist.line'

    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Service',
        domain="[('product_tmpl_id.type', '=', 'service')]",
        required=True
    )
    unit_price = fields.Float(string='Unit Price',digits=(6,2))
    pricelist_id = fields.Many2one('pilar.pricelist', string='Pricelist', ondelete='cascade', index=1) 

    @api.onchange('product_id')
    def compute_unit_price(self):
        for rec in self:
            # get unit price base on product_id in another pricelist
            if rec.product_id:
                pricelist = self.env['pilar.pricelist'].sudo().search([('product_id', '=', rec.product_id.id)])
                for i in pricelist:
                    rec.unit_price = i.price 
      
   