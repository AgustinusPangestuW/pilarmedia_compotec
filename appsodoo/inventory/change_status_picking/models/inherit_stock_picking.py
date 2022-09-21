from multiprocessing import context
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
        ('in_transit', 'in Transit'),
        ('delivered', 'Delivered')

    ], string='Status', compute='_compute_state',
        copy=False, index=True, readonly=True, store=True, tracking=True,
        help=" * Draft: The transfer is not confirmed yet. Reservation doesn't apply.\n"
             " * Waiting another operation: This transfer is waiting for another operation before being ready.\n"
             " * Waiting: The transfer is waiting for the availability of some products.\n(a) The shipping policy is \"As soon as possible\": no product could be reserved.\n(b) The shipping policy is \"When all products are ready\": not all the products could be reserved.\n"
             " * Ready: The transfer is ready to be processed.\n(a) The shipping policy is \"As soon as possible\": at least one product has been reserved.\n(b) The shipping policy is \"When all products are ready\": all product have been reserved.\n"
             " * Done: The transfer has been processed.\n"
             " * Cancelled: The transfer has been cancelled.\n"
             " * Transit: changed from API.\n"
             " * Delivered: changed from API.\n")
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
