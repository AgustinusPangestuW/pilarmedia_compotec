from odoo import models, fields, api, _
from odoo.exceptions import UserError
import copy

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    stock_picking_subcont_ref_id = fields.Many2one(
        'stock.picking', 
        string='Stock Picking ID creator for Subcon', 
        tracking=True,
        readonly=True
    )
    location_dest_id_subcon = fields.Many2one('stock.location', string='Destination Location', readonly=True)
    count_stock_picking_created = fields.Integer(
        string='Count Stock Pick Created', 
        readonly=1, 
        compute="_count_stock_picking_created",
        store=1
    )

    def button_validate(self):
        for rec in self:
            if rec.picking_type_id.is_subcon:
                # ditampung ke variable untuk ditampilkan
                rec.location_dest_id_subcon = copy.deepcopy(rec.picking_type_id.default_location_dest_id.id)

                if rec.picking_type_id.transit_location_id:
                    rec.location_dest_id = rec.picking_type_id.transit_location_id.id
                else:
                    # field transit location kosong
                    raise UserError(_("Field Transit Location in Operation Type %s is null." % rec.picking_type_id.name ))

        new_sm = {}
        for rec in self:
            if rec.picking_type_id.is_subcon:
                new_sm.update({
                    'picking_type_id': rec.picking_type_id.operation_type_id.id,
                    'location_id': rec.picking_type_id.operation_type_id.default_location_src_id.id,
                    'location_dest_id': rec.picking_type_id.operation_type_id.default_location_dest_id.id,
                    'surat_jalan_id': rec.surat_jalan_id,
                    'stock_picking_subcont_ref_id': rec.id,
                    'move_lines': []
                })
                for line in rec.move_lines:
                    new_sm['move_lines'].append((0,0, {
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.product_uom_qty,
                        'description_picking': line.description_picking,
                        'product_uom': line.product_uom.id,
                        'name': line.name
                    }))    
            
        st_subcon_created = self.env['stock.picking'].sudo().create(new_sm)
        st_subcon_created.action_confirm()
        st_subcon_created.action_assign()
        
        self._count_stock_picking_created()
        self = super(StockPicking, self).button_validate()

    def _count_stock_picking_created(self):
        for rec in self:
            rec.count_stock_picking_created = rec.env['stock.picking'].sudo().search_count([('stock_picking_subcont_ref_id', '=', rec.id)])

    def action_see_stock_move_created(self):
        list_domain = []
        if 'active_id' in self.env.context:
            list_domain.append(('stock_picking_subcont_ref_id', '=', self.env.context['active_id']))
        
        return {
            'name':_('Transfers'),
            'domain':list_domain,
            'res_model':'stock.picking',
            'view_mode':'tree,form',
            'type':'ir.actions.act_window',
        }


