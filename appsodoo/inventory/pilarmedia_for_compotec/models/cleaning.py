from datetime import datetime
from odoo import models, fields, api

class Cleaning(models.Model):
    _name = 'cleaning'
    _rec_name = "user"

    datetime = fields.Datetime(string="Tanggal dan Waktu", default=datetime.now())
    user = fields.Many2one('employee.custom', string='Nama User', required=True)
    product = fields.Many2one('product.product', string='Product', domain=[('active', '=', True)], required=True)
    res_ok = fields.Integer(string='Hasil OK')
    res_ng = fields.Integer(string='Hasil NG') 
    rework = fields.Char(string='Rework')
    description = fields.Text(string='Description')