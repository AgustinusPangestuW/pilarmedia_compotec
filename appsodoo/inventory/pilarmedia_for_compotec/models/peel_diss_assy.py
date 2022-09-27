from odoo import models, fields, api
from datetime import datetime

class PeelDissAssy(models.Model):
    _name = 'peel.diss.assy'
    _description = "Form Kupas Diss Assy"
    _rec_name = "date"

    date = fields.Date(string='Tangal',default=datetime.now().date(), required=True)
    total_ok = fields.Float(
        string='Total Ok', 
        readonly=True, 
        compute="_calculate_total_ok", 
        store=True
    )
    total_ng = fields.Float(
        string="Total NG", 
        readonly=True, 
        compute="_calculate_total_ng", 
        store=True
    )
    total_ok_ng = fields.Float(
        string="Total (OK + NG)", 
        readonly=True, 
        compute="_calculate_total_ok_ng", 
        store=True
    )
    peel_diss_assy_line = fields.One2many('peel.diss.assy.line', 'peel_diss_assy_line_id', 'Line')

    @api.depends('peel_diss_assy_line.ok')
    def _calculate_total_ok(self):
        total_ok = 0
        for line in self.peel_diss_assy_line:
            total_ok += line.ok
        self.update({'total_ok': total_ok})

    @api.depends('peel_diss_assy_line.ng')
    def _calculate_total_ng(self):
        total_ng = 0
        for line in self.peel_diss_assy_line:
            total_ng += line.ng
        self.update({'total_ng': total_ng})

    @api.depends('total_ng', 'total_ok')
    def _calculate_total_ok_ng(self):
        total = 0
        for rec in self:
            total += rec.total_ok + rec.total_ng
        self.update({'total_ok_ng': total})


class PeelDissAssyLine(models.Model):
    _name = "peel.diss.assy.line"
    _description = "Detail Job of Peel Diss Assy"

    peel_diss_assy_line_id = fields.Many2one(
        'peel.diss.assy', 
        'Peel Diss Assy Line ID', 
        ondelete='cascade', 
        index=True, 
        copy=False
    )
    job = fields.Many2one('job', string='Job', required=True)
    user = fields.Many2one('employee.custom', string='Nama', required=True)
    product = fields.Many2one('product.product', string='Produk', required=True)
    peeled_total = fields.Float(string="Total yang dikupas")
    ok = fields.Float(string='OK')
    ng = fields.Float(string='NG')
    description = fields.Text(string="Description")