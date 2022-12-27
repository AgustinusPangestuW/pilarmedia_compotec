from odoo import models, fields, api, _
from odoo.exceptions import UserError
import datetime

class InheritStockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    @api.model_create_multi
    def create(self, vals_list):
        def get_max_name(supplier_code, date):
            res = self.env.cr.execute("""
                SELECT MAX(name) as max_name
                FROM stock_production_lot sm
                WHERE name like '{}%'
            """.format(str(supplier_code)+'-'+str(date)+'-'))
            res = self.env.cr.dictfetchone()
            index = 0
            if res:
                index = int(res['max_name'][-4:] if res['max_name'] else 0) + 1
            else:
                index += 1
            return str(supplier_code)+'-'+str(date)+'-'+(str(index).rjust(4,'0'))

        for l in vals_list:
            active_picking_id = self.env.context.get('active_picking_id', False)
            if active_picking_id:
                picking_id = self.env['stock.picking'].browse(active_picking_id)
                if picking_id and picking_id.picking_type_id.auto_create_lot and \
                    picking_id.picking_type_id.name_base_on_supplier:
                    # format name base on MOM 22122022 (suppliercode-DDMMYY-XXXX)
                    if picking_id.vendor_purchase:
                        vendor_code = picking_id.vendor_purchase.code
                        today = datetime.date.today()
                        date = today.strftime('%d%m%y')
                        l['name'] = get_max_name(vendor_code, date)

        return super().create(vals_list)
