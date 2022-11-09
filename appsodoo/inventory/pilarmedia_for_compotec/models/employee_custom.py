from odoo import models, fields, api
from .inherit_models_model import inheritModel

class EmployeeCustom(inheritModel):
    _name = 'employee.custom'

    name = fields.Char(string='Nama Pegawai', required=True)
    position = fields.Char(string='Jabatan')
    vendor = fields.Many2one(
        'res.partner', 
        string='Vendor Subcon', 
        domain=[('is_subcon', '=', 1)], 
        help="relation with res parner, with is_subcon = 1"
    )


def _get_domain_user(self):
    return [('vendor', 'in', [v.id for v in self.env.user.vendors])]