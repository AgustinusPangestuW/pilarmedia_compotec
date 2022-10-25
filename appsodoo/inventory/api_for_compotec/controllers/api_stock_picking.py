import json, copy
from odoo import http, _
from odoo.http import request
from .api import ApiController, RequestError


class apiStockPicking(http.Controller):
    def mapping_values(self, transit_log:object):
        return [{
            'picking_id': rec.picking_id.id,
            'picking': rec.picking_id.name,
            'long': rec.long or None,
            'lat': rec.lat or None,
            'gps_id': rec.gps_id or None,
            'datetime': rec.datetime 
        } for rec in transit_log]

    @http.route(['/updateloc/'], type="json", auth="public", method=['POST'], csrf=False)
    def updateloc(self, **kwargs):
        """
        REST API POST for create table transit_log
        """
        request.env.cr.savepoint()

        try:
            if not kwargs.get('uid') and (kwargs.get('db') and kwargs.get('login') and kwargs.get('password')):
                ApiController.authenticate(ApiController, kwargs.get('db'), kwargs.get('login'), kwargs.get('password'), kwargs.get('base_location'))

            # hapus parameter untuk execute auth
            kwargs = ApiController.clear_param_auth(ApiController, kwargs)
            # value kwargs ditampung ke temp_kwargs untuk proses create `transit_log`
            temp_kwargs = copy.deepcopy(kwargs)
            for d in temp_kwargs:
                # rubah data kwargs yang bertipe list of dict menjadi list of tuple agar tidak hardcode
                if type(temp_kwargs[d]) == list:
                    temp_kwargs[d] = [(0,0, dl) for dl in temp_kwargs[d]]

            res = request.env['transit.log'].sudo().create(temp_kwargs)
            transit_logs = self.mapping_values(res)
            if transit_logs: transit_logs = transit_logs[0]
            request.env.cr.commit()     
            return ApiController.response_sucess(ApiController, transit_logs, kwargs, "updateloc")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController.response_failed(ApiController, e, kwargs, "updateloc")

    @http.route(['/updatepicking/'], type="json", auth="public", method=['POST'], csrf=False)
    def updatepicking(self, **kwargs):
        """
        REST API POST for update state pada table `stock_picking`
        """
        request.env.cr.savepoint()
        try:
            if not kwargs.get('uid') and (kwargs.get('db') and kwargs.get('login') and kwargs.get('password')):
                ApiController.authenticate(ApiController, kwargs.get('db'), kwargs.get('login'), kwargs.get('password'), kwargs.get('base_location'))

            # hapus parameter untuk execute auth
            kwargs = ApiController.clear_param_auth(ApiController, kwargs)
            if kwargs.get('state') in ['in_transit', 'delivered']:
                res = request.env['stock.picking'].sudo().search(
                    [('id', '=', kwargs['picking_id'])]).write({'state': kwargs['state']})
                request.env.cr.commit()
            
                return ApiController.response_sucess(ApiController, res, kwargs, "updatepicking")
            else:
                raise RequestError('can only update state to (in_transit / delivered)')

        except Exception as e:
            request.env.cr.rollback()
            return ApiController.response_failed(ApiController, e, kwargs, "updatepicking")