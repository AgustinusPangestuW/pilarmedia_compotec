from odoo import models, fields, api, _
from odoo.exceptions import UserError

class InheritStockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    approvals = fields.Many2many(
        comodel_name='res.users', 
        relation='users_approvals_rel',
        string='Approvals'
    )
   
    count_picking_need_approval = fields.Integer(compute='_compute_picking_status')
    count_picking_rejected = fields.Integer(compute='_compute_picking_status')
    count_picking_approved = fields.Integer(compute='_compute_picking_status')

    def _compute_picking_status(self):
        id_stock_pick_approva = [i.id for i in self if self.env.user in i.approvals]
        domains = {
            'count_picking_rejected': [('state', '=', 'reject')],
            'count_picking_approved': [('approved_by', '!=', False), ('state', '=', 'done')],
            'count_picking_need_approval': [('state', '=', 'need_approval'), ('picking_type_id', 'in', id_stock_pick_approva)]
        }
        for field in domains:
            data = self.env['stock.picking'].read_group(domains[field] +
                [('picking_type_id', 'in', self.ids)],
                ['picking_type_id'], ['picking_type_id'])
            count = {
                x['picking_type_id'][0]: x['picking_type_id_count']
                for x in data if x['picking_type_id']
            }
            for record in self:
                record[field] = count.get(record.id, 0)

    def get_action_picking_tree_rejected(self):
        return self._get_action('pilarmedia_subcon_auto_create_stock_move.action_picking_tree_rejected')

    def get_action_picking_tree_approved(self):
        return self._get_action('pilarmedia_subcon_auto_create_stock_move.action_picking_tree_approved')

    def get_action_picking_tree_need_approval(self):
        return self._get_action('pilarmedia_subcon_auto_create_stock_move.action_picking_tree_need_approval')