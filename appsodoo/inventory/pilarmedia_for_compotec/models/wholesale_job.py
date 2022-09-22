from odoo import models, fields, api
from datetime import datetime

class WholesaleJob(models.Model):
    _name = 'wholesale.job'
    _rec_name = "date"

    date = fields.Date(string="Date", required=True, default=datetime.now().date())
    job = fields.Many2one('job', string='Job', required=True, domain=[('active', '=', 1)])
    user = fields.Many2one('res.partner', string='Nama', required=True)
    product = fields.Many2one('product.product', string='Produk')
    total_lot = fields.Float(string="Jumlah Lot", readonly=True, compute='_calculate_total_lot', store=True)
    checked_coordinator = fields.Many2one('res.partner', string='Checked Coordinator')
    checked_qc = fields.Many2one('res.partner', string='Checked QC')
    lot_line = fields.One2many('lot', 'lot_id', 'Lot Line')

    @api.depends('lot_line.total_lot')
    def _calculate_total_lot(self):
        total_lot = 0
        for rec in self:
            for line in rec.lot_line:
                total_lot += line.total_lot

            self.total_lot = total_lot


class Lot(models.Model):
    _name = "lot"
    _rec_name = "lot_id"
    
    lot_id = fields.Integer(string='Lot ID')
    total_lot = fields.Float("Lot")
    sequence = fields.Integer(string='Sequence')