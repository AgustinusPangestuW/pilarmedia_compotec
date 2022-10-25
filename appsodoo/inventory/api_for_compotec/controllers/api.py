import json, copy, datetime
from odoo import http, _
from odoo.http import request
from odoo.exceptions import ValidationError
from odoo.tools import date_utils


class ApiController(http.Controller):
    def validate_product(self, product_id):
        product = request.env['product.product'].sudo().search([('id', '=', product_id)])
        if not product: 
            raise RequestError(_("product with id %s is not found." % product_id))
    
    def validate_warehouses(self, warehouses:list):
        for id in warehouses:
            warehouse = request.env['stock.warehouse'].sudo().search([('id', '=', id)])
            if not warehouse:
                raise RequestError(_("warehouse with id %s is not found." % id))

    def validate_base_on_id(self, db:str, des_db:str, id, return_res=False):
        res = request.env[db].sudo().search([('id', '=', id)])
        if not res:
            raise RequestError(_("%s with id %s is not found." % (des_db, id)))

        if return_res:
            return res

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

    def response_sucess(self, res='', req={}, method=""):
        # validate res must be filled
        if type(res) == list and len(res) == 0:
            return self.response_failed(self, "data result is null", req, method)

        request.env['api.log'].sudo().create({
            "datetime": datetime.datetime.now(),
            "sucess": True,
            "method": method,
            "request": req,
            "result": json.dumps(res, indent=4, sort_keys=True, default=date_utils.json_default) \
                if type(res) == list or type(res) == dict else str(res)
        })

        return {
            'status': 200,
            'response': 'sucess',
            'message': res
        }

    def response_failed(self, res, req={}, method=""):
        request.env['api.log'].sudo().create({
            "datetime": datetime.datetime.now(),
            "sucess": False,
            "method": method,
            "request": req,
            "result": json.dumps(res, indent=4, sort_keys=True, default=date_utils.json_default) \
                if type(res) == dict or type(res) == dict else str(res)
        })

        return {
            'response': 'failed',
            'error-descrip': str(res)
        }

class RequestError(Exception):
    def __init__(self, message):
        self.message = message

        super().__init__(message)

    def __str__(self):
        return self.message