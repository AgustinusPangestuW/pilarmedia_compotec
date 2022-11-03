from email.policy import default
from odoo import models, fields, api
from .inherit_models_model import inheritModel


class Job(inheritModel):
    _name = 'job'

    name = fields.Char(string='Nama Pengerjaan', required=True)
    active = fields.Boolean(string='Active', default="1")
    description = fields.Text(string='Description')
    op_type_ng = fields.Many2one('stock.picking.type', string='Stock Picking Type NG', required=True) 
    op_type_ok = fields.Many2one('stock.picking.type', string='Stock Picking Type OK', required=True)
    for_form = fields.Selection([
        ("wrapping","Wrapping"),
        ("peel_diss_assy","Kupas Diss Assy"),
        ("wholesale_job","Checksheet Borongan")
    ], string='Form')
    generate_document = fields.Selection([
        ("mo","MO (Manufactoring Order)"),
        ("transfer","Transfer / Stock Picking")
    ], string='Create document to?')
    source_location_ng = fields.Many2one(
        'stock.location', 
        string='Source Location NG', 
        required=True,
        readonly=False,
        compute="_compute_from_operation_ng",
        store=True
    )
    dest_location_ng = fields.Many2one(
        'stock.location', 
        string='Destination Location NG', 
        required=True,
        readonly=False,
        compute="_compute_from_operation_ng",
        store=True
    )
    source_location_ok = fields.Many2one(
        'stock.location', 
        string='Source Location OK', 
        required=True,
        readonly=False,
        compute="_compute_from_operation_ok",
        store=True
    )
    dest_location_ok = fields.Many2one(
        'stock.location', 
        string='Destination Location OK', 
        required=True,
        readonly=False,
        compute="_compute_from_operation_ok",
        store=True
    )    

    @api.depends("op_type_ng")
    def _compute_from_operation_ng(self):
        for rec in self:
            if rec.op_type_ng:
                if not rec.source_location_ng:
                    rec.source_location_ng = rec.op_type_ng.default_location_src_id
                if not rec.dest_location_ng:
                    rec.dest_location_ng = rec.op_type_ng.default_location_dest_id
    
    @api.depends("op_type_ok")
    def _compute_from_operation_ok(self):
        for rec in self:
            if rec.op_type_ok:
                if not rec.source_location_ok:
                    rec.source_location_ok = rec.op_type_ok.default_location_src_id
                if not rec.dest_location_ok:
                    rec.dest_location_ok = rec.op_type_ok.default_location_dest_id