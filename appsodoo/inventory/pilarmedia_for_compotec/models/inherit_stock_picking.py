from multiprocessing import context
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    wholesale_job_id = fields.Many2one('wholesale.job', string='Checksheet Borongan', readonly=True)
    log_outstanding_qty_line = fields.One2many(
        'log.outstanding.qty', 
        'picking_id', 
        string='Log Outstanding Qty Line',
        compute="_get_outstanding_qty",
        store=True,
        copy=False
    )
    pricelist_subcons = fields.One2many(
        'pricelist.subcon.baseon.stockmove', 
        'picking_id', 
        string='Pricelist subcon',
        store=True,
        copy=False
    )
    vendor = fields.Many2one('res.partner', string='Vendor', compute="_fill_vendor", stored=True)
    vendor_dest_loc_subcon = fields.Many2one('res.partner', string='Vendor', compute="_fill_vendor_dest_loc_subcon")
    location_dest_id_subcon = fields.Many2one(
        'stock.location', 
        string='Destination Location', 
        readonly=True,
        copy=False
    )

    def button_validate(self):
        self._get_outstanding_qty()
        return super().button_validate()

    def write(self, vals):
        list_res = []
        for sm in self.move_ids_without_package:
            exists = False
            for ps in self.pricelist_subcons:
                if ps.picking_id.id == self.id and (ps.move_id.id == sm.id or sm.product_id.id == ps.product_id.id):
                    exists = True
                    break
            
            if not exists:
                list_res.append([0,0, {
                    'picking_id': self.id,
                    'move_id': sm.id,
                    'product_id': sm.product_id.id,
                    'price_total': 0,
                    'vendor': self.vendor.id,
                    'lines': []
                }])

        if list_res:
            vals.update({'pricelist_subcons': list_res})
    
        return super().write(vals)

    @api.depends('location_id')
    def _fill_vendor(self):
        vendor = None
        for rec in self:
            if rec.location_id:
                warehouse = self.get_warehouse(rec.location_id)
                if warehouse:
                    vendor = warehouse.vendor.id
            rec.vendor = vendor

    @api.depends('location_dest_id_subcon')
    def _fill_vendor_dest_loc_subcon(self):
        vendor = None
        for rec in self:
            if rec.location_dest_id_subcon:
                warehouse = self.get_warehouse(rec.location_dest_id_subcon)
                if warehouse:
                    vendor = warehouse.vendor.id
            rec.vendor_dest_loc_subcon = vendor

    @api.depends('surat_jalan_id')
    def _get_outstanding_qty(self):
        # reset to null
        self.update({'log_outstanding_qty_line': [(5,0,0)]})

        if self.surat_jalan_id:
            list_res = []
            for rec in self:
                for sm in rec.move_ids_without_package:
                    done_qty = self.get_done_qty(rec.surat_jalan_id.id, sm.product_id.id)
                    used_qty = self.get_used_qty(rec.surat_jalan_id.id, sm.product_id.id) or 0

                    if done_qty != None:
                        remaining_qty = done_qty - used_qty
                        list_res.append([0,0, {
                            'picking_id': rec.id,
                            'move_id': sm.id,
                            'product_id': sm.product_id.id,
                            'done_qty': done_qty,
                            'remaining_qty': remaining_qty
                        }])
                rec.update({
                    'log_outstanding_qty_line': list_res
                })
            

    def get_done_qty(self, sj, product_id):
        self.env.cr.execute("""
            SELECT SUM(sm.product_uom_qty) as done_qty
            FROM stock_picking sp
            LEFT JOIN stock_move sm ON sm.picking_id = sp.id
            WHERE sp.id = %s and sm.product_id = %s
        """ % (sj, product_id))
        res = self.env.cr.dictfetchone()

        if res == None:
            return res
        elif 'done_qty' in res:
            return res['done_qty']
        else:
            return 0

    def get_used_qty(self, sj, product_id):
        self.env.cr.execute("""
            SELECT SUM(sml.qty_done) as used_qty
            FROM stock_picking sp
            LEFT JOIN stock_move sm ON sm.picking_id = sp.id
            LEFT JOIN stock_move_line sml ON sml.move_id = sm.id
            WHERE sp.surat_jalan_id = %s AND sp.state = 'done' 
                AND sm.product_id = %s AND sp.master_sj = false
        """ % (sj, product_id))
        res = self.env.cr.dictfetchone()
        if res and 'used_qty' in res:
            return res['used_qty']
        else:
            return 0

    def get_warehouse(self, location):
        parent_loc = location.location_id

        wrh_in_currenct_loc = self.env['stock.warehouse'].sudo().search([('view_location_id', '=', location.id)])
        if wrh_in_currenct_loc:
            return wrh_in_currenct_loc
        
        if parent_loc:
            wrh_in_parent_loc = self.env['stock.warehouse'].sudo().search([('view_location_id', '=', parent_loc.id)])
            if wrh_in_parent_loc:
                return wrh_in_parent_loc
            else:
                self.get_warehouse(parent_loc)

        return ""
