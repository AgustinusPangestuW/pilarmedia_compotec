import json, copy, werkzeug
from odoo import http, _
from odoo.http import request


class ApiController(http.Controller):
    @http.route(['/api/create_transit_log/'], type="json", auth="public", method=['POST'], csrf=False)
    def create_transit_log(self, **kwargs):
        """
        REST API POST for create table transit_log

        `system will be execute authenticate when kwargs['id_user'] is None`
        """
        request.env.cr.savepoint()

        try:
            if not kwargs.get('id_user'):
                self.authenticate(kwargs.get('db'), kwargs.get('login'), kwargs.get('password'), kwargs.get('base_location'))

            # hapus parameter untuk execute auth
            kwargs = self.clear_param_auth(kwargs)

            # value kwargs ditampung ke temp_kwargs untuk proses create `transit_log`
            temp_kwargs = copy.deepcopy(kwargs)
            for d in temp_kwargs:
                # rubah data kwargs yang bertipe list of dict menjadi list of tuple agar tidak hardcode
                if type(temp_kwargs[d]) == list:
                    temp_kwargs[d] = [(0,0, dl) for dl in temp_kwargs[d]]

            res = request.env['transit.log'].sudo().create(temp_kwargs)
            request.env.cr.commit()

            return {
                'status': 200,
                'message': 'success'
            }

        except Exception as e:

            request.env.cr.rollback()
            return {
                'message': "Error",
                'error-descrip': str(e)
            }

    @http.route(['/api/update_status_picking/'], type="json", auth="public", method=['POST'], csrf=False)
    def update_status_picking(self, **kwargs):
        """
        REST API POST for update state pada table `stock_picking`

        `system will be execute authenticate when kwargs['id_user'] is None`
        """
        request.env.cr.savepoint()

        try:
            if not kwargs.get('id_user'):
                self.authenticate(kwargs.get('db'), kwargs.get('login'), kwargs.get('password'), kwargs.get('base_location'))

            # hapus parameter untuk execute auth
            kwargs = self.clear_param_auth(kwargs)

            if kwargs.get('state') in ['in_transit', 'delivered']:
                res = request.env['stock.picking'].sudo().search(
                    [('id', '=', kwargs['picking_id'])]).write({'state': kwargs['state']})
                request.env.cr.commit()

                return {
                    'status': 200,
                    'message': 'success'
                }
            else:
                return {
                    'message': "Error",
                    'error-descrip': str('can only update state to (in_transit / delivered)')
                }

        except Exception as e:

            request.env.cr.rollback()
            return {
                'error': "Error",
                'error-descrip': str(e)
            }

    @http.route('/web/session/authenticate', type='json', auth="public")
    def authenticate(self, db, login, password, base_location=None):
        request.session.authenticate(db, login, password)
        return request.env['ir.http'].session_info()

    def clear_param_auth(self, kwargs):
        if 'id_user' in kwargs: del kwargs['id_user']
        if 'db' in kwargs: del kwargs['db']
        if 'login' in kwargs: del kwargs['login']
        if 'password' in kwargs: del kwargs['password']
        if 'base_location' in kwargs: del kwargs['base_location']
        return kwargs