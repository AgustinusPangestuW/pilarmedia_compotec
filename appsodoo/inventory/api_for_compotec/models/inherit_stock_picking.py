from multiprocessing import context
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    state = fields.Selection(selection_add=[
        ('in_transit', 'in Transit'),
        ('delivered', 'Delivered')
    ])
    is_transit = fields.Boolean(string='is Transit', compute="_compute_is_transit")

    def action_see_transit_log(self):
        list_domain = []
        if 'active_id' in self.env.context:
            list_domain.append(('picking_id', '=', self.env.context['active_id']))
        
        return {
            'name':_('Transit Log'),
            'domain':list_domain,
            'res_model':'transit.log',
            'view_mode':'tree,form',
            'type':'ir.actions.act_window',
        }

    def _compute_is_transit(self):
        for field in self:
            field.is_transit = bool(self.env['stock.picking.type.for.transit'].search_count([('picking_type_id', '=', self.picking_type_id.id)]))
