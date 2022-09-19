from odoo import models, fields, api

class PilarSuratJalan(models.Model):
    _name = 'pilar.surat.jalan'

    name = fields.Char(string='Nomor')
    date_sj = fields.Date(string='Tanggal', default=fields.Date.today())
    vendor_id = fields.Many2one('res.partner', string='Vendor')
    remark = fields.Text(string='Note')
    jasa_ids = fields.One2many('pilar.jasa.subcon', 'sj_id', string='Jasa Subcon')
    product_ids = fields.One2many('pilar.product.subcon', 'sj_id', string='Product Subcon')

from odoo import models, fields, api

class PilarJasaSubcon(models.Model):
    _name = 'pilar.jasa.subcon'
    _rec_name='product_id'

    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Price Item',
        domain="[('product_tmpl_id.type', '=', 'service')]"
        )
    price = fields.Float(string='Unit Price',digits=(6,2))    