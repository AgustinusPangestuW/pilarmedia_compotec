from multiprocessing import context
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    wholesale_job_id = fields.Many2one('wholesale.job', string='Checksheet Borongan', readonly=True)
    wrapping_id = fields.Many2one('wrapping', string='Wrapping', readonly=True)
    peel_diss_assy_id = fields.Many2one('wrapping', string='Peel Diss Assy', readonly=True)
    generator_mosp_id = fields.Many2one('generator.mo.or.sp', string='Generator MO or SP ID', readonly=True)
    log_outstanding_qty_line = fields.One2many(
        'log.outstanding.qty', 
        'picking_id', 
        string='Log Outstanding Qty Line',
        compute="_get_outstanding_qty",
        store=True,
        copy=False
    )
    vendor = fields.Many2one('res.partner', string='Vendor', compute="_fill_vendor", stored=True)
    vendor_dest_loc = fields.Many2one('res.partner', string='Vendor', compute="_fill_vendor_dest_loc")
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

    @api.depends('location_id')
    def _fill_vendor(self):
        vendor = None
        for rec in self:
            if rec.location_id:
                warehouse = self.get_warehouse(rec.location_id)
                if warehouse:
                    vendor = warehouse.vendor.id
            rec.vendor = vendor

    @api.depends('location_dest_id')
    def _fill_vendor_dest_loc(self):
        vendor = None
        for rec in self:
            if rec.location_dest_id:
                warehouse = self.get_warehouse(rec.location_dest_id)
                if warehouse:
                    vendor = warehouse.vendor.id
            rec.vendor_dest_loc = vendor

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
            # set vehicle_id base on surat_jalan_id
            stock_picking = self.env['stock.picking'].sudo().search([('id', '=', self.surat_jalan_id.id)])
            if stock_picking: self.vehicle_id = stock_picking.vehicle_id.id

            list_res = []
            for rec in self:
                for sm in self.env['stock.move'].sudo().search([('picking_id', '=', rec.surat_jalan_id.id)]):
                    done_qty = self.get_done_qty(rec.surat_jalan_id.id, sm.product_id.id) or 0
                    last_done_qty = self.get_last_done_qty(rec.surat_jalan_id.id, sm.product_id.id) or 0
                    used_qty = self.get_used_qty(rec.surat_jalan_id.id, sm.product_id) or 0

                    remaining_qty = done_qty - used_qty
                    list_res.append([0,0, {
                        'picking_id': rec.id,
                        'move_id': sm.id,
                        'sj_id': rec.surat_jalan_id.id,
                        'product_id': sm.product_id.id,
                        'qty_base_on_sj_master': done_qty,
                        'last_done_qty': last_done_qty,
                        'done_qty': used_qty,
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

    def get_bom_and_component(self, product_id:object):
        bom = self.env['mrp.bom'].sudo().search([("product_tmpl_id.id", "=", product_id.product_tmpl_id.id)])
        component = self.env['mrp.bom.line'].sudo().search([('product_id', '=', product_id.id)])

        # only get first data cause to much process if > 1 data
        if bom and len(bom) > 0: bom = bom[0]
        if component and len(component) > 0: component = component[0]

        return bom or None, component or None

    def get_done_qty_baseon_bom(self, product_id_1:object, product_id_2:object, \
        qty_2:float) -> float:
        # prodcut_id_1 => from master surat jalan
        # product_id_2 => from surat jalan used

        bom_sj, component_sj = self.get_bom_and_component(product_id_1)
        bom_sm, component_sm = self.get_bom_and_component(product_id_2)

        res = 0

        # same from BOM
        if bom_sj and bom_sm and bom_sj.id == bom_sm.id: 
            res = qty_2
        elif bom_sj and component_sm and bom_sj.id == component_sm.bom_id.id:
            # BOM in master sj and component in sj used
            bom = self.env['mrp.bom'].sudo().search([('id', '=', component_sm.bom_id.id)])
            res = qty_2 / component_sm.product_qty * bom.product_qty
        elif component_sj and bom_sm and component_sj.bom_id.id == bom_sm.id:
            # component in master SJ and BOM in sj used (stock move)
            count_sm = qty_2 / bom_sm.product_qty
            count_qty_2 = count_sm * component_sj.product_qty
            res = count_qty_2
        elif component_sj and component_sm and component_sj.bom_id.id == component_sm.bom_id.id:
            # component in master SJ and component in SJ used (stock move)
            res = qty_2
        elif not bom_sj and not component_sj and not bom_sm and not component_sm:
            # without BOM 
            res = qty_2

        return res 

    def get_last_done_qty(self, sj_id, product_id_msj):
        # qty last done in log_outstanding_qty_line
        self.env.cr.execute("""
            SELECT SUM(loq.done_qty) as done_qty
            FROM log_outstanding_qty loq
            LEFT JOIN stock_picking sp ON sp.id = loq.picking_id
            WHERE sp.surat_jalan_id = %s AND loq.product_id = %s AND sp.state = 'done' 
            GROUP BY loq.create_date
            ORDER BY loq.create_date DESC
        """ % (sj_id, product_id_msj))
        last_done_qty = self.env.cr.dictfetchone()
        if last_done_qty and 'done_qty' in last_done_qty:
            last_done_qty = last_done_qty['done_qty']
        else:
            last_done_qty = 0

        return last_done_qty

    def get_used_qty(self, sj_id, product_msj):
        # Calculate current qty base on BOM
        cur_done_qty = 0
        for sm in self.move_ids_without_package:
            cur_done_qty += self.get_done_qty_baseon_bom(product_msj, sm.product_id, sm.product_uom_qty)

        return cur_done_qty

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
