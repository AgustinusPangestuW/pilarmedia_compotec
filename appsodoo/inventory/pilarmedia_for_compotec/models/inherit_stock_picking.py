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

    def button_validate(self):
        self._get_outstanding_qty()
        return super().button_validate()

    def write(self, vals):
        list_res = []
        for sm in self.move_ids_without_package:
            exists = False
            for ps in self.pricelist_subcons:
                if ps.picking_id.id == self.id and ps.move_id.id == sm.id:
                    exists = True
                    break
            
            if not exists:
                list_res.append([0,0, {
                    'picking_id': self.id,
                    'move_id': sm.id,
                    'product_id': sm.product_id.id,
                    'price_total': 0,
                    'lines': []
                }])

        if list_res:
            vals.update({'pricelist_subcons': list_res})
    
        return super().write(vals)

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
            SELECT SUM(sm.product_uom_qty) as used_qty
            FROM stock_picking sp
            LEFT JOIN stock_move sm ON sm.picking_id = sp.id
            WHERE sp.surat_jalan_id = %s AND sp.state = 'done' 
                AND sm.product_id = %s
        """ % (sj, product_id))
        res = self.env.cr.dictfetchone()
        if res and 'used_qty' in res:
            return res['used_qty']
        else:
            return 0