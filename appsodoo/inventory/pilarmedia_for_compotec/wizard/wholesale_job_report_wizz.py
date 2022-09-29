from odoo import models, fields, api


class WholesaleJobReport(models.TransientModel):
    _name = "wholesale.job.report.wizzard"
    date_start = fields.Date(string='Date Start', required=True)
    date_end = fields.Date(string='Date End', required=True)
    company = fields.Many2one('res.company', string='Company')
    job = fields.Many2one('job', string='Job')
    shift = fields.Many2one('shift', string='Shift')

    def call_wholesale_job_report(self):
        cr = self.env.cr

        company = str(self.company.id) if self.company else ''
        job = str(self.job.id) if self.job else ''
        shift = str(self.shift.id) if self.shift else ''

        cr.execute("select wholesale_job_report(%s,%s,%s,%s,%s)",(
            self.date_start, self.date_end, company, job, shift
        ))
        waction = self.env.ref("pilarmedia_for_compotec.""wholesale_job_report_action")
        result = waction.read()[0]
        return result

    @api.onchange('date_start', 'date_end')
    def onchange_date(self):
        res={}
        if (self.date_start and self.date_end) and self.date_start > self.date_end:
            res = {'warning':{
                'title':('Warning'),
                'message':('Tanggal Akhir Lebih Kecil Dari Tanggal Mulai')}}
        if res:
            return res
