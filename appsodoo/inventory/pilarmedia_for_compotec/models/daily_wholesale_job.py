from email.policy import default
from odoo import models, fields, api
from datetime import datetime

class DailyWholesaleJob(models.Model):
    _name = 'daily.wholesale.job'
    _description = "Pekerjaan borongan harian"
    _rec_name = "date"

    date = fields.Date(string='Date', required=True, default=datetime.now().date())
    daily_wholesale_job_line = fields.One2many(
        'daily.wholesale.job.line', 
        'daily_wholesale_job_line_id', 
        'Daily Wholesale Job Line'
    )
    total_ok = fields.Float(string='Total Ok', readonly=True, compute="_calculate_total_ok", store=True)
    total_ng = fields.Float(string='Total NG', readonly=True, compute="_calculate_total_ng", store=True)
    total_ok_ng = fields.Float(string='Total (OK and NG)', readonly=True, compute="_calculate_total_ok_ng", store=True)

    is_with_type = fields.Boolean(string='is With Type', default=False)

    @api.depends('daily_wholesale_job_line.ok')
    def _calculate_total_ok(self):
        total_ok = 0
        for line in self.daily_wholesale_job_line:
            total_ok += line.ok
        
        self.update({'total_ok': total_ok})

    @api.depends('daily_wholesale_job_line.ng')
    def _calculate_total_ng(self):
        total_ng = 0
        for line in self.daily_wholesale_job_line:
            total_ng += line.ng

        self.update({'total_ng': total_ng})

    @api.depends('total_ok', 'total_ng')
    def _calculate_total_ok_ng(self):
        total_ok_ng = 0
        for rec in self:
            total_ok_ng += rec.total_ok + rec.total_ng

        self.update({'total_ok_ng': total_ok_ng})


class DailyWholesaleJobLine(models.Model):
    _name = "daily.wholesale.job.line"
    _description = "List of job in current date"
    _rec_name = "job"

    daily_wholesale_job_line_id = fields.Many2one('daily.wholesale.job', 'Daily Wholesale Job Line ID')
    job = fields.Many2one('job', string='Job', required=True, domain=[('active', '=', True)])
    user = fields.Many2one('res.partner', string='User', required=True)
    ok = fields.Float(string='Ok')
    ng = fields.Float(string='NG')  
    verify_tim = fields.Char(string='Verifikasi Tim Random')
    description = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence')
    type = fields.Char(string='Type')