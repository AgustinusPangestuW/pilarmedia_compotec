from odoo import models, fields, api, _

class InheritStockPickingType(models.Model):
    _inherit = 'stock.picking.type'
        
    def _get_action(self, action_xmlid):
        action = super()._get_action(action_xmlid)
        action['context'].update({'default_immediate_transfer': False})
        return action