from odoo import models, fields, api, _
from odoo.exceptions import UserError

class MRPProduction(models.Model):
    _inherit = 'mrp.production'

    peel_diss_assy_id = fields.Many2one('peel.diss.assy', string='Peel Diss Assy')
    wrapping_id = fields.Many2one('wrapping', string='Wrapping')

    def button_mark_done(self):
        super(MRPProduction, self).button_mark_done()

        if self.wrapping_id:
            op_type_ng = self.wrapping_id.job.op_type_ng
            total_ng = 0    

            for wl in self.wrapping_id.wrapping_deadline_line:
                if wl.product.id == self.product_id.id:
                    total_ng += wl.ng

            lot_id = ""
            for f in self.finished_move_line_ids:
                lot_id = f.lot_id

            if total_ng:
                new_scrap = {
                    'product_id': self.product_id.id,
                    'scrap_qty': total_ng,
                    'product_uom_id': self.product_id.uom_id.id,
                    'location_id': op_type_ng.default_location_src_id.id,
                    'scrap_location_id': op_type_ng.default_location_dest_id.id,
                    'production_id': self.id,
                    'lot_id': lot_id.id
                }
                new_scrap = self.env['stock.scrap'].sudo().create(new_scrap)

                new_scrap.action_validate()
                return new_scrap.action_validate()