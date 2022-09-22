import json, copy
from odoo import http, _
from odoo.http import request


class ApiController(http.Controller):
    @http.route(['/updateloc/'], type="json", auth="public", method=['POST'], csrf=False)
    def updateloc(self, **kwargs):
        """
        REST API POST for create table transit_log

        `system will be execute authenticate when kwargs['id_user'] is None`
        """
        request.env.cr.savepoint()

        try:
            if not kwargs.get('uid') and (kwargs.get('db') and kwargs.get('login') and kwargs.get('password')):
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

            return self.response_sucess(res.id)

        except Exception as e:
            request.env.cr.rollback()
            return self.response_failed(e)

    @http.route(['/updatepicking/'], type="json", auth="public", method=['POST'], csrf=False)
    def updatepicking(self, **kwargs):
        """
        REST API POST for update state pada table `stock_picking`

        `system will be execute authenticate when kwargs['id_user'] is None`
        """
        request.env.cr.savepoint()

        try:
            if not kwargs.get('uid') and (kwargs.get('db') and kwargs.get('login') and kwargs.get('password')):
                self.authenticate(kwargs.get('db'), kwargs.get('login'), kwargs.get('password'), kwargs.get('base_location'))

            # hapus parameter untuk execute auth
            kwargs = self.clear_param_auth(kwargs)

            if kwargs.get('state') in ['in_transit', 'delivered']:
                res = request.env['stock.picking'].sudo().search(
                    [('id', '=', kwargs['picking_id'])]).write({'state': kwargs['state']})
                request.env.cr.commit()

                return self.response_sucess(res)
            else:
                return self.response_failed('can only update state to (in_transit / delivered)')

        except Exception as e:
            request.env.cr.rollback()
            return self.response_failed(e)

    @http.route('/authenticate', type='json', auth="public")
    def authenticate(self, db, login, password, base_location=None):
        try:
            request.session.authenticate(db, login, password)
            res = request.env['ir.http'].session_info()

            # get warehouses in user
            if 'uid' in res:
                warehouses = request.env['res.users'].sudo().search([('id', '=', res['uid'])]).warehouses
                res['warehouses'] =  [{w.id:w.name} for w in warehouses]

            return self.response_sucess(res)
        except Exception as e:
            return self.response_failed(e)

    def clear_param_auth(self, kwargs):
        if 'uid' in kwargs: del kwargs['uid']
        if 'db' in kwargs: del kwargs['db']
        if 'login' in kwargs: del kwargs['login']
        if 'password' in kwargs: del kwargs['password']
        if 'base_location' in kwargs: del kwargs['base_location']
        return kwargs

    def response_sucess(self, res=''):
        return {
            'status': 200,
            'response': 'sucess',
            'message': res
        }

    def response_failed(self, res):
        return {
            'response': 'failed',
            'error-descrip': str(res)
        }