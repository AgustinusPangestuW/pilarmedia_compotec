from odoo import models, fields, api

class EmployeeCustom(models.Model):
    _name = 'employee.custom'

    name = fields.Char(string='Nama Pegawai', required=True)
    position = fields.Char(string='Jabatan')
    vendor = fields.Many2one(
        'res.partner', 
        string='Vendor Subcon', 
        domain=[('is_subcon', '=', 1)], 
        help="relation with res parner, with is_subcon = 1"
    )