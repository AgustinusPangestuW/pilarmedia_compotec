from odoo import models, fields, api
from .inherit_models_model import inheritModel
from datetime import datetime

class EmployeeCustom(inheritModel):
    _name = 'employee.custom'
    _description = "Operator"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Nama Pegawai', required=True)
    no = fields.Char(string='No', readonly=True)
    position = fields.Char(string='Jabatan')
    vendor = fields.Many2one(
        'res.partner', 
        string='Vendor Subcon', 
        domain=[('is_subcon', '=', 1)], 
        help="relation with res parner, with is_subcon = 1"
    )
    no_ktp = fields.Char(string='No KTP', required=True, copy=0)
    join_date = fields.Date(string='Join Date', default=fields.Date.today(), required=True)
    address = fields.Text(string='Address')

    _sql_constraints = [
        ('unique_noktp_operator', 'unique(no_ktp)', 'No KTP must be unique per Operator!'),
    ]

    def name_get(self):
        new_res = []
        for rec in self:
            name = ("%s - %s" % (rec.no, rec.name)) if rec.no else ""
            new_res.append((rec.id, name))

        return new_res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if not args:
            args = []
        domain = args + [('no',operator,name)]
        res = super().search(domain, limit=limit).name_get()
        return res

    @api.model
    def create(self, vals_list):
        def get_max_no(year:str, month:str):
            res = self.env.cr.execute("""
                SELECT MAX(e.no) as max_no
                FROM employee_custom e
                WHERE e.no like '{}%'
            """.format(year))
            res = self.env.cr.dictfetchone()
            index = 0
            if res:
                index = int(res['max_no'][-4:] if res['max_no'] else 0) + 1
            else:
                index += 1
            return str(year+month+'-'+(str(index).rjust(4,'0')))
        
        if type(vals_list.get('join_date')) == "str":
            join_date = datetime.strptime(vals_list.get('join_date'), '%Y-%m-%d').date()
        else:
            join_date = vals_list.get('join_date')
        year_join = join_date.strftime('%y')
        month_join = join_date.strftime('%m')
        vals_list['no'] =  get_max_no(year_join, month_join)
        return super().create(vals_list) 

def _get_domain_user(self):
    vendors_in_user = [v.id for v in self.env.user.vendors]
    return [('vendor', 'in', [False]+vendors_in_user)]   