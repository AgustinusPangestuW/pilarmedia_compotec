from odoo import models, fields, api


class WholesaleJobReport(models.TransientModel):
    _name = "wholesale.job.report.wizzard"
    date_start = fields.Date(string='Date Start')
    date_end = fields.Date(string='Date End')

    def call_wholesale_job_report(self):
        cr = self.env.cr
        cr.execute("select wholesale_job_report(%s,%s)",(self.date_start, self.date_end))
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
