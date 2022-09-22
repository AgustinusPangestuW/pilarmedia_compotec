from datetime import datetime
from odoo import models, fields, api

class TransitLog(models.Model):
    _name = 'transit.log'
    _rec_name = "picking_id"

    picking_id = fields.Many2one('stock.picking', string='Stock Picking ID', required=True)
    long = fields.Char(string='Longitude')
    lat = fields.Char(string='Latitude')
    gps_id = fields.Char(string='GPS ID')
    datetime = fields.Datetime(string='Date', default=datetime.now(), required=True)