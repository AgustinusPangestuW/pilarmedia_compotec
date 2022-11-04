from odoo import models, fields, api, _
from odoo.exceptions import UserError

class MRPProduction(models.Model):
    _inherit = 'mrp.production'

    peel_diss_assy_id = fields.Many2one('peel.diss.assy', string='Peel Diss Assy')
    wrapping_id = fields.Many2one('wrapping', string='Wrapping')
    wholesale_job_id = fields.Many2one('wholesale.job', string='Wholesale Job', readonly=True)

    def button_mark_done(self):
        super(MRPProduction, self).button_mark_done()
        
        location, doc_creator = {'source': None, 'dest': None}, None
        if self.wrapping_id or self.peel_diss_assy_id or self.wholesale_job_id:
            total_ng = 0    

            if self.wrapping_id :
                doc_creator = self.wrapping_id
                op_type_ng = self.wrapping_id.job.op_type_ng
                for wl in self.wrapping_id.wrapping_deadline_line:
                    if wl.product.id == self.product_id.id:
                        total_ng += wl.ng
            elif self.wholesale_job_id:
                doc_creator = self.wholesale_job_id
                op_type_ng = self.wholesale_job_id.job.op_type_ng
                for wsj in self.wholesale_job_id.wholesale_job_lines:
                    if wsj.product_id.id == self.product_id.id:
                        total_ng += wsj.total_ng
            elif self.peel_diss_assy_id:
                doc_creator = self.peel_diss_assy_id
                op_type_ng = self.peel_diss_assy_id.job.op_type_ng
                for line in self.peel_diss_assy_id.peel_diss_assy_line:
                    if line.product_id.id == self.product_id.id:
                        total_row = 0
                        for c in line.peel_diss_assy_component_line:
                            total_ng += c.ng
                            total_row += 1
                        total_ng = int(total_ng / total_row)

            if doc_creator:
                location.update({
                    'source': doc_creator.job.source_location_ng,
                    'dest': doc_creator.job.dest_location_ng
                })

            lot_id = ""
            for f in self.finished_move_line_ids:
                lot_id = f.lot_id

            if total_ng:
                new_scrap = {
                    'product_id': self.product_id.id,
                    'scrap_qty': total_ng,
                    'product_uom_id': self.product_id.uom_id.id,
                    'location_id': location.get('source').id if location.get('source') else None,
                    'scrap_location_id': location.get('dest').id if location.get('dest') else None,
                    'production_id': self.id,
                    'lot_id': lot_id.id
                }
                new_scrap = self.env['stock.scrap'].sudo().create(new_scrap)
                return new_scrap.action_validate()