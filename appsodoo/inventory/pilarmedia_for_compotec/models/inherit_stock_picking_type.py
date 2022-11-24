from odoo import models, fields, api, _
from .utils import get_location_by_vendor

class InheritStockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    is_subcon = fields.Boolean(string='Is Subcontracting Transfer')
        
    def _get_action(self, action_xmlid):
        action = super()._get_action(action_xmlid)
        action['context'].update({'default_immediate_transfer': False})
        return action

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        if self.env.user and self.env.user.vendors:
            locations = get_location_by_vendor(self)
            warehouses = self.env['stock.warehouse'].sudo().search([('vendor', 'in', [v.id for v in self.env.user.vendors])])
            if locations:
                domain += [
                    ('default_location_src_id', 'in', locations), 
                    ('warehouse_id', 'in', ['']+[w.id for w in warehouses])
                ]
        res = super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return res

    @api.model
    def _web_read_group(self, domain, fields, groupby, limit=None, offset=0, orderby=False, \
        lazy=True, expand=False, expand_limit=None, expand_orderby=False):

        if self.env.user and self.env.user.vendors:
            warehouses = self.env['stock.warehouse'].sudo().search([('vendor', 'in', [v.id for v in self.env.user.vendors])])
            if warehouses:
                domain += [('warehouse_id', 'in', ['']+[w.id for w in warehouses])]
        
        res = super()._web_read_group(domain, fields, groupby, limit=limit, offset=offset, orderby=orderby,\
            lazy=lazy, expand=expand, expand_limit=expand_limit, expand_orderby=expand_orderby)
        return res