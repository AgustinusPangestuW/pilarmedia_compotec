from odoo import models, fields, api

class EmployeeCustom(models.Model):
    _name = 'employee.custom'

    name = fields.Char(string='Nama Pegawai', required=True)
    position = fields.Char(string='Jabatan')
    vendor = fields.Many2one('res.partner', string='Vendor Subcon')