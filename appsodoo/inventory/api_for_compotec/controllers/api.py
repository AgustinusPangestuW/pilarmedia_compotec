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
    
    def updates_lines(self, lines=[]):
        # lines
        list_lines = []
        if type(lines) == list:
            for line in lines:
                dict_line = {}
                for key, val in line.items():
                    if type(val) == list and type(val[0]) == dict:
                        # another line
                        dict_line[key] = self.updates_lines(val)
                    else: 
                        # data
                        dict_line[key] = val
                    
                # update/delete
                if line.get('id'):
                    if line.get('delete'): list_lines.append((2, line['id'], dict_line))
                    else: list_lines.append((1, line['id'], dict_line))
                # new
                else:
                    list_lines.append((0,0, dict_line))

        return list_lines

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
        # # validate res must be filled
        # if type(res) == list and len(res) == 0:
        #     return self.response_failed("data result is null", req, method)

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
            'error-descrip': res
        }

    ############
    ### CRUD ###
    ############

    def create_document(self, model, required_fields, kwargs):
        def validate_required_field(kwargs, require_fields):
            key_in_kwargs = list(kwargs.keys())
            if not all(item in key_in_kwargs for item in require_fields):
                raise RequestError(_("parameter %s need for process create document.") % (
                    ", ".join(require_fields)
                ))

        validate_required_field(kwargs, required_fields)
        for d in kwargs:
            # rubah data kwargs yang bertipe list of dict menjadi list of tuple agar tidak hardcode
            if type(kwargs[d]) == list:
                # lines
                if len(kwargs[d]) > 0 and type(kwargs[d][0]) == dict:
                    kwargs[d] = [(0,0, 
                        {
                            # val Lines
                            key: [(0,0,val_wt) for val_wt in val] 
                            if type(val) == list and type(val[0]) == dict 
                            else val
                        for key, val in dl.items() } 
                    ) for dl in kwargs[d]]

        return request.env[model].sudo().create(kwargs)

    def update_document(self, cur_model, row, required_fields, child_table=[]):
        def validate_required_field(row, require_fields):
            key_in_row = list(row.keys())
            if not all(item in key_in_row for item in require_fields):
                raise RequestError(_("parameter %s need for process update document.") % (
                    ", ".join(require_fields)
                ))
        
        validate_required_field(row, required_fields)
        result = self.validate_base_on_id(cur_model, cur_model.replace('.', '_'), row.get('id'), return_res=True)
        del row['id']
        update_lines = copy.deepcopy(row)

        for field in child_table:
            if field in update_lines:
                del update_lines[field]    
            another_line = copy.deepcopy(row.get(field))

            # update/new/delete line (child table in current line)
            result[field] = self.updates_lines(another_line)

        # current line
        for k, v in update_lines.items():
            result[k] = v

        return result

    def delete_document(self, model, ids):
        result = []
        for id in ids:
            if type(id) != int:
                raise self.RequestError(_("value in ids (%s) must be integer" % (id)))

            res = self.validate_base_on_id(model, model.replace('.', '_'), id, return_res=True)
            res.unlink()
            if res:
                result.append({"idx": id, "success": True})

        return result

class RequestError(Exception):
    def __init__(self, message):
        self.message = message

        super().__init__(message)

    def __str__(self):
        return self.message

