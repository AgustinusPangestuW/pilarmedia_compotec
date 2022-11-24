import json, copy
from odoo import http, _
from odoo.http import request
from .api import RequestError, ApiController


class MasterNG(http.Controller):
    def mapping_master_ng(self, master_ng:object):
        res = []
        model_obj = request.env['master.ng']
        for i in master_ng:
            temp_res = i.read(list(set(model_obj._fields)))            
            res.append(temp_res[0])
        
        return res

    ########
    # CRUD #
    ########

    @http.route(["/masterng/get"], type="json", method="GET", auth="public", scrf=False)
    def get_masterng(self, **kwargs):
        """ Get table Master NG 
        
        parameters
        ----------
        search : list
            ex : [["id", "in", [2,4,5]], ["active", "=", true]]
        """
        try:
            result = request.env['master.ng'].sudo().search(kwargs.get('search') or [])
            result = self.mapping_master_ng(result)
            return ApiController().response_sucess(result, kwargs, "/masterng/get/")
        except Exception as e:
            return ApiController().response_failed(e, kwargs, "/masterng/get/")

    @http.route(["/masterng/create"], type="json", method="POST", auth="public", scrf=False)
    def create_masterng(self, **kwargs):
        """ create table Master NG """
        required_fields = ["name"]
        request.env.cr.savepoint()
        try:
            res = ApiController().create_document('master.ng', required_fields, kwargs)
            master_ng = self.mapping_master_ng(res)
            if len(master_ng) > 0: master_ng = master_ng[0]
            request.env.cr.commit()   

            return ApiController().response_sucess(master_ng, kwargs, "/masterng/create")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, kwargs, "/masterng/create") 

    @http.route(["/masterng/update"], type="json", method="POST", auth="public", scrf=False)
    def update_masterng(self, updates):
        """ update table master NG """
        request.env.cr.savepoint()
        require_fields = ['id']
        result = []

        # convert into list
        if type(updates) == dict:
            updates = [updates]

        try:
            for row in updates:
                params = {
                    'id': row.get('id'),
                    'updates': row
                }

                cur_master_ng = ApiController().update_document('master.ng', row, require_fields)

                request.env.cr.commit()
                master_ng = self.mapping_master_ng(cur_master_ng)
                if len(master_ng) > 0: master_ng = master_ng[0]
                result.append(master_ng)

            return ApiController().response_sucess(result, updates, "/master_ng/update")
        except Exception as e:
            request.env.cr.rollback()   
            return ApiController().response_failed(e, updates, "/master_ng/update")

    @http.route(["/masterng/delete"], type="json", method="POST", auth="public", scrf=False)
    def delete_master_ng(self, ids):
        """ delete master ng 

        parameters
        ----------
        ids : list of integer
            ex : [1,4,66,3]
        """
        request.env.cr.savepoint()

        # VALIDATION
        if type(ids) != list:
            raise ApiController().RequestError(_("key ids must be list of integer")) 

        try:
            result = ApiController().delete_document('master.ng', ids)
            request.env.cr.commit()
            return ApiController().response_sucess(result, ids, "/masterng/delete/")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, ids, "/masterng/delete")