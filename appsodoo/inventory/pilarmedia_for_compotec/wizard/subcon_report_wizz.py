from odoo import models, fields, api


class SubconReport(models.TransientModel):
    _name = "subcon.report.wizzard"
    date_start = fields.Date(string='Date Start', required=True)
    date_end = fields.Date(string='Date End', required=True)
    vendor = fields.Many2one('res.partner', string='Subcon', domain="[('is_subcon', '=', True)]")

    def call_subcon_report(self):
        cr = self.env.cr

        vendor = str(self.vendor.id) if self.vendor else ''

        cr.execute("select subcon_report(%s,%s,%s)",(
            self.date_start, self.date_end, vendor
        ))
        waction = self.env.ref("pilarmedia_for_compotec.""subcon_report_action")
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
