import json, copy, werkzeug
from odoo import http, _
from odoo.http import request


class ApiController(http.Controller):
    @http.route(['/api/create_transit_log/'], type="json", auth="public", method=['POST'], csrf=False)
    def create_transit_log(self, **kwargs):
        """
        REST API POST for create table transit_log
        """
        request.env.cr.savepoint()

        try:
            # value kwargs ditampung ke temp_kwargs untuk proses create `transit_log`
            temp_kwargs = copy.deepcopy(kwargs)
            for d in temp_kwargs:
                # rubah data kwargs yang bertipe list of dict menjadi list of tuple agar tidak hardcode
                if type(temp_kwargs[d]) == list:
                    temp_kwargs[d] = [(0,0, dl) for dl in temp_kwargs[d]]

            request.env['transit.log'].sudo().create(temp_kwargs)
            request.env.cr.commit()

            return {
                'status': 200,
                'message': 'success',
                'response': kwargs
            }

        except Exception as e:

            request.env.cr.rollback()
            return {
                'error': "Error",
                'error-descrip': str(e)
            }

    @http.route(['/api/update_status_picking/'], type="json", auth="public", method=['POST'], csrf=False)
    def update_status_picking(self, **kwargs):
        """
        REST API POST for create table transit_log
        """
        request.env.cr.savepoint()

        try:
            if kwargs.get('state') in ['in_transit', 'delivered']:
                request.env['stock.picking'].sudo().search(
                    [('id', '=', kwargs['picking_id'])]).write({'state': kwargs['state']})
                request.env.cr.commit()

                return {
                    'status': 200,
                    'message': 'success',
                    'response': kwargs
                }
            else:
                return {
                    'error': "Error",
                    'error-descrip': str('can only update state to (in_transit / delivered)')
                }

        except Exception as e:

            request.env.cr.rollback()
            return {
                'error': "Error",
                'error-descrip': str(e)
            }

    