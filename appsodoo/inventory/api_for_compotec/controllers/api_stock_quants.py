import json, copy
from odoo import http, _
from odoo.http import request
from .api import ApiController


class apiStockQuants(ApiController):

    def get_income_stock(self, product_id, locations=[]):
        locations_str = [str(i) for i in locations]

        res = request.env.cr.execute("""
            SELECT SUM(sm.product_uom_qty) as done_qty
            FROM stock_move sm
            WHERE sm.product_id = {} AND
                sm.state = 'done' AND sm.location_dest_id in ({})
        """.format(product_id, (',').join(locations_str)))
        res = request.env.cr.dictfetchone()

        return res['done_qty'] or 0

    def get_stock_out(self, product_id, locations=[]):
        locations_str = [str(i) for i in locations]

        request.env.cr.execute("""
            SELECT SUM(sm.product_uom_qty) as done_qty
            FROM stock_move sm
            WHERE sm.product_id = {} AND
                sm.state = 'done' AND location_id in ({})
        """.format(product_id, (',').join(locations_str)))
        res = request.env.cr.dictfetchone()

        return res['done_qty'] or 0

    @http.route(['/stocklist/'], type="json", auth="public", method=['POST'])
    def stocklist(self, warehouses=[], **kwargs):
        """
        REST API POST for get product in warehouse
        """
        try:
            if type(warehouses) != list:
                return self.response_failed('warehouses must be list.')

            # Get All Location base on warehouse 
            warehouses = request.env['stock.warehouse'].sudo().search([('id', 'in', warehouses)])
            list_locations = []
            for w in warehouses:
                list_locations = self.get_location_from_warehouse(w.view_location_id.id)

            res = []
            if list_locations:
                stock_quants = request.env['stock.quant'].sudo().search([('location_id', 'in', list_locations)])
                
                if stock_quants:
                    res = [{
                            'product_id': sq.product_id.id,
                            'product': sq.product_id.name,
                            'barcode': sq.product_id.barcode or None,
                            'uom': sq.product_id.uom_id.name,
                            'uom_id': sq.product_id.uom_id.id,
                            'qty': sq.quantity,
                            'reserved_qty': sq.reserved_quantity,
                            'location_id': sq.location_id.id or None,
                            'location': (sq.location_id.location_id.name or "") + '/' + sq.location_id.name
                        } for sq in stock_quants
                    ]

            return self.response_sucess({'items': res}, kwargs, "stocklist")

        except Exception as e:
            return self.response_failed(e, kwargs, "stocklist")

    @http.route(['/quantity/'], type="json", auth="public", method=['POST'])
    def quantity(self, product_id, warehouses=[], **kwargs):
        """
        REST API POST for get Qty Product in spesific warehouse
        """
        try:
            # VALIDATE
            self.validate_product(product_id)
            if type(warehouses) != list:
                return self.response_failed('warehouses must be list.')
            else:
                self.validate_warehouses(warehouses)

            # Get All Location base on warehouse 
            warehouses = request.env['stock.warehouse'].sudo().search([('id', 'in', warehouses)])
            list_locations = []
            for w in warehouses:
                list_locations = self.get_location_from_warehouse(w.view_location_id.id)

            res = {'uom_id': None, 'qty': None, 'reserved_qty': None}
            if list_locations:
                stock_quants = request.env['stock.quant'].sudo().search([
                    ('location_id', 'in', list_locations), 
                    ('product_id', '=', product_id)
                ])
                
                if stock_quants:
                    res['income_stock'] = self.get_income_stock(product_id, list_locations)
                    res['stock_out'] = self.get_stock_out(product_id, list_locations)
                    res['qty_manual'] = res['income_stock'] - res['stock_out']
                    
                    for sq in stock_quants:
                        res.update({
                            'uom_id': sq.product_id.uom_id.id, 
                            'uom': sq.product_id.uom_id.name,
                            'reserved_qty': (res.get('reserved_qty') or 0) + sq.reserved_quantity,
                            'qty': (res.get('qty') or 0) + sq.quantity
                        })

            return self.response_sucess(res, kwargs, "quantity")

        except Exception as e:
            return self.response_failed(e, kwargs, "quantity")