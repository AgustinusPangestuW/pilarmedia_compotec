from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class MRPProduction(models.Model):
    _inherit = 'mrp.production'

    peel_diss_assy_id = fields.Many2one('peel.diss.assy', string='Peel Diss Assy', readonly=True, ondelete="restrict")
    wrapping_id = fields.Many2one('wrapping', string='Wrapping', readonly=True, ondelete="restrict")
    wholesale_job_id = fields.Many2one('wholesale.job', string='Wholesale Job', readonly=True, ondelete="restrict")
    generator_mosp_id = fields.Many2one('generator.mo.or.sp', string='Generator MO or SP ID', readonly=True, ondelete="restrict")

    def button_mark_done(self):
        super(MRPProduction, self).button_mark_done()
        
        location, doc_creator = {'source': None, 'dest': None}, None
        if self.wrapping_id or self.peel_diss_assy_id or self.wholesale_job_id or self.generator_mosp_id:
            temp_scrap = []
            total_ng = 0    

            if self.wrapping_id :
                doc_creator = self.wrapping_id
                op_type_ng = self.wrapping_id.job.op_type_ng
                temp_scrap.append({'product_id': self.product_id, 'total_ng': 0})
                for wl in self.wrapping_id.wrapping_deadline_line:
                    if wl.product.id == self.product_id.id:
                        temp_scrap[0]['total_ng'] += wl.ng
            elif self.wholesale_job_id:
                doc_creator = self.wholesale_job_id
                op_type_ng = self.wholesale_job_id.job.op_type_ng
                temp_scrap.append({'product_id': self.product_id, 'total_ng': 0})
                for wsj in self.wholesale_job_id.wholesale_job_lines:
                    if wsj.product_id.id == self.product_id.id:
                        temp_scrap[0]['total_ng'] += wsj.total_ng
            elif self.generator_mosp_id:
                doc_creator = self.generator_mosp_id
                temp_scrap.append({'product_id': self.product_id, 'total_ng': 0})
                for line in self.generator_mosp_id.line_ids:
                    if line.product_id.id == self.product_id.id:
                        temp_scrap[0]['total_ng'] += line.ng
            elif self.peel_diss_assy_id:
                doc_creator = self.peel_diss_assy_id
                op_type_ng = self.peel_diss_assy_id.job.op_type_ng
                for line in self.peel_diss_assy_id.peel_diss_assy_line:
                    if line.product_id.id == self.product_id.id:
                        for fg in line.peel_diss_assy_fg_line:
                            if fg.ng > 0:
                                temp_scrap.append({'product_id': fg.product_id, 'total_ng': fg.ng})

            if doc_creator:
                location.update({
                    'source': doc_creator.job.source_location_ng,
                    'dest': doc_creator.job.dest_location_ng
                })

            lot_id = ""
            for f in self.finished_move_line_ids:
                for s in temp_scrap:
                    if s['product_id'].id == f.product_id.id:
                        s.update({'lot_id': f.lot_id})

            for s in temp_scrap:
                validate_exist_stock(self, s['product_id'], location.get('source') or None, s['total_ng'])

                new_scrap = {
                    'product_id': s['product_id'].id,
                    'scrap_qty': s['total_ng'],
                    'product_uom_id': s['product_id'].uom_id.id,
                    'location_id': location.get('source').id if location.get('source') else None,
                    'scrap_location_id': location.get('dest').id if location.get('dest') else None,
                    'production_id': self.id,
                    'lot_id': s['lot_id'].id
                }
                new_scrap = self.env['stock.scrap'].sudo().create(new_scrap)
                new_scrap.action_validate()

def validate_exist_stock(self, product, location, qty):
    stock_quants = self.env['stock.quant'].sudo().search([
        ('location_id', '=', location.id), 
        ('product_id', '=', product.id)
    ])

    current_stock = 0
    for s in stock_quants:
        current_stock += s.quantity - s.reserved_quantity

    if current_stock < qty:
        raise ValidationError(_("Item %s need stock %s %s in location %s for continue process scrap." % (
            product.name, qty, product.uom_id.name, location.display_name
        )))