from odoo import models, fields, api

class StockPickingTypeForTransit(models.Model):
    _name = 'stock.picking.type.for.transit'
    _description = 'list of Stock Picking Type for base transit'
    _rec_name = "picking_type_id"

    picking_type_id = fields.Many2one('stock.picking.type', string='Stock Picking Type', required=True)