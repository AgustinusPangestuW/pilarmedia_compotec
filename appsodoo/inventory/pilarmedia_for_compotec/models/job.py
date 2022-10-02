from email.policy import default
from odoo import models, fields, api

class Job(models.Model):
    _name = 'job'

    name = fields.Char(string='Nama Pengerjaan', required=True)
    active = fields.Boolean(string='Active', default="1")
    description = fields.Text(string='Description')
    op_type_ng = fields.Many2one('stock.picking.type', string='Stock Picking Type NG', required=True) 
    op_type_ok = fields.Many2one('stock.picking.type', string='Stock Picking Type OK', required=True)