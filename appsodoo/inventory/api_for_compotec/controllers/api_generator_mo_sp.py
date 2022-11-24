import json, copy
from odoo import http, _
from odoo.http import request
from .api import RequestError, ApiController
from odoo.exceptions import ValidationError


class GeneratorMOSP(http.Controller):
    ###########
    # MAPPING #
    ###########
    
    def mapping_generator_mosp(self, generatormosp:object, ret_lines=False):
        res = []
        model_obj = request.env['generator.mo.or.sp']
        for i in generatormosp:
            temp_res = i.read(list(set(model_obj._fields)))

            if ret_lines:
                generator_mosp_lines = self.mapping_generator_mosp_lines(i.line_ids)
                temp_res[0].update({'line_ids': generator_mosp_lines})

                required_items = self.mapping_required_items(i.required_items)
                temp_res[0].update({'required_items': required_items})
            
            res.append(temp_res[0])
        
        return res

    def mapping_generator_mosp_lines(self, generator_mosp_lines:object, ret_lines=False):
        res = []
        model_obj = request.env['generator.mosp.line']
        for i in generator_mosp_lines: 
            res.append(i.read(list(set(model_obj._fields)))[0])

            if ret_lines:
                bom_components = self.mapping_generator_comp_lines(i.bom_components)
                res[0].update({'bom_components': bom_components})
        
        return res

    def mapping_generator_comp_lines(self, bom_components:object):
        res = []
        model_obj = request.env['gen.mosp.comp.line']
        for i in bom_components: 
            res.append(i.read(list(set(model_obj._fields)))[0])
        
        return res

    def mapping_required_items(self, required_items:object):
        res = []
        model_obj = request.env['gen.mosp.comp.line']
        for i in required_items: 
            res.append(i.read(list(set(model_obj._fields)))[0])
        
        return res

    ######################
    # GENERATOR MO OR SP #
    ######################

    @http.route(["/generatormosp/get"], type="json", auth="public", method="GET", scrf=False)
    def get_generatormosp(self, **kwargs):
        """ get 'generator.mo.or.sp' """
        try:
            ret_lines = False
            if kwargs.get('ret_lines'):
                ret_lines = kwargs.get('ret_lines')
                del kwargs['ret_lines']

            generator_mo_or_sp = request.env['generator.mo.or.sp'].sudo().search(kwargs.get('search') or [])
            generator_mo_or_sp = self.mapping_generator_mosp(generator_mo_or_sp, ret_lines)
            return ApiController().response_sucess(generator_mo_or_sp, kwargs, "/generatormosp/get/")
        except Exception as e:
            return ApiController().response_failed(e, kwargs, "/generatormosp/get/")

    @http.route(['/generatormosp/create'], type="json", auth="public", method="POST", scrf=False)
    def create_generatormosp(self, **kwargs):
        """ create generator.mo.or.sp """      
        required_fields = ["job"]
        request.env.cr.savepoint()
        try:
            ret_lines = False
            if kwargs.get('ret_lines'):
                ret_lines = kwargs.get('ret_lines')
                del kwargs['ret_lines']

            res = ApiController().create_document('generator.mo.or.sp', required_fields, kwargs)
            generator_mosp = self.mapping_generator_mosp(res, ret_lines)
            if len(generator_mosp) > 0: generator_mosp = generator_mosp[0]
            request.env.cr.commit()   
            
            return ApiController().response_sucess(generator_mosp, kwargs, "/generatormosp/create")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, kwargs, "/generatormosp/create") 

    @http.route(["/generatormosp/update"], type="json", auth="public", method="GET", scrf=False)
    def update_generatormosp(self, updates, **kwargs):
        """ update Generator MO or SP """
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
                    'updates': row,
                    'ret_lines': row.get("ret_lines")
                }
                # cause ret_lines only for flag return with lines detail
                if "ret_lines" in row: del row['ret_lines']

                cur_generator_mosp = ApiController().update_document(                    
                    'generator.mo.or.sp',
                    row, 
                    require_fields,
                    ["required_items", "line_ids"]
                )
                
                if kwargs.get('draft'):
                    cur_generator_mosp.action_draft()
                elif kwargs.get('submit'):
                    cur_generator_mosp.action_submit()
                elif kwargs.get('cancel'):
                    cur_generator_mosp.action_cancel()

                request.env.cr.commit()
                generator_mosp = self.mapping_generator_mosp(cur_generator_mosp, True if params.get('ret_lines') else False)
                if len(generator_mosp) > 0: generator_mosp = generator_mosp[0]
                result.append(generator_mosp)

            return ApiController().response_sucess(result, updates, "/generatormosp/update")
        except Exception as e:
            request.env.cr.rollback()   
            return ApiController().response_failed(e, updates, "/generatormosp/update")

    @http.route(["/generatormosp/delete"], type="json", auth="public", method="POST", scrf=False)
    def delete_generatormosp(self, ids):
        """ delete Generator MO or Sp

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
            result = ApiController().delete_document('generator.mo.or.sp', ids)
            request.env.cr.commit()
            return ApiController().response_sucess(result, ids, "/generatormosp/delete/")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, ids, "/generatormosp/delete")

    #######################
    # GENERATOR MOSP LINE #
    #######################

    @http.route(["/generatormosp/line/get"], type="json", auth="public", method="GET", scrf=False)
    def get_generatormosp_line(self, **kwargs):
        """ get 'generator.mosp.line' """
        try:
            ret_lines = False
            if kwargs.get('ret_lines'):
                ret_lines = kwargs.get('ret_lines')
                del kwargs['ret_lines']

            generator_mosp_lines = request.env['generator.mosp.line'].sudo().search(kwargs.get('search') or [])
            generator_mosp_lines = self.mapping_generator_mosp_lines(generator_mosp_lines, ret_lines)
            return ApiController().response_sucess(generator_mosp_lines, kwargs, "/generatormosp/line/get/")
        except Exception as e:
            return ApiController().response_failed(e, kwargs, "/generatormosp/line/get/")

    @http.route(['/generatormosp/line/create'], type="json", auth="public", method="POST", scrf=False)
    def create_generatormosp_line(self, **kwargs):
        """ create generator.mosp.line """      
        required_fields = ["generator_mosp_id", "product_id"]
        request.env.cr.savepoint()
        try:
            ret_lines = False
            if kwargs.get('ret_lines'):
                ret_lines = kwargs.get('ret_lines')
                del kwargs['ret_lines']

            res = ApiController().create_document('generator.mosp.line', required_fields, kwargs)
            generator_mosp_line = self.mapping_generator_mosp_lines(res, ret_lines)
            if len(generator_mosp_line) > 0: generator_mosp_line = generator_mosp_line[0]
            request.env.cr.commit()   
            
            return ApiController().response_sucess(generator_mosp_line, kwargs, "/generatormosp/line/create")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, kwargs, "/generatormosp/line/create") 

    @http.route(["/generatormosp/line/update"], type="json", auth="public", method="GET", scrf=False)
    def update_generatormosp_line(self, updates, **kwargs):
        """ update generator.mosp.line """
        request.env.cr.savepoint()
        require_fields = ['id']
        result = []

        # convert into list
        if type(updates) == dict:
            updates = [updates]

        try:
            for row in updates:
                ret_lines = row.get("ret_lines") or False
                # cause ret_lines only for flag return with lines detail
                if "ret_lines" in row: del row['ret_lines']

                cur_generator_mosp_lines = ApiController().update_document(                    
                    'generator.mosp.line',
                    row, 
                    require_fields,
                    ['bom_components']
                )

                request.env.cr.commit()
                generator_mosp_lines = self.mapping_generator_mosp_lines(cur_generator_mosp_lines, ret_lines)
                if len(generator_mosp_lines) > 0: generator_mosp_lines = generator_mosp_lines[0]
                result.append(generator_mosp_lines)

            return ApiController().response_sucess(result, updates, "/generatormosp/line/update")
        except Exception as e:
            request.env.cr.rollback()   
            return ApiController().response_failed(e, updates, "/generatormosp/line/update")

    @http.route(["/generatormosp/line/delete"], type="json", auth="public", method="POST", scrf=False)
    def delete_generatormosp_line(self, ids):
        """ delete generator.mosp.line 

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
            result = ApiController().delete_document('generator.mosp.line', ids)
            request.env.cr.commit()
            return ApiController().response_sucess(result, ids, "/generatormosp/line/delete/")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, ids, "/generatormosp/line/delete")

    ##########################
    # GENERATOR MOSP BOMLINE #
    ##########################    
    
    @http.route(["/generatormosp/line/comp/get"], type="json", auth="public", method="GET", scrf=False)
    def get_generatormosp_comp_line(self, **kwargs):
        """ get 'gen.mosp.comp.line' """
        try:
            datas = request.env['gen.mosp.comp.line'].sudo().search(kwargs.get('search') or [])
            datas = self.mapping_generator_comp_lines(datas)
            return ApiController().response_sucess(datas, kwargs, "/generatormosp/line/comp/get/")
        except Exception as e:
            return ApiController().response_failed(e, kwargs, "/generatormosp/line/comp/get/")

    @http.route(['/generatormosp/line/comp/create'], type="json", auth="public", method="POST", scrf=False)
    def create_generatormosp_comp_line(self, **kwargs):
        """ create gen.mosp.comp.line """      
        required_fields = ["generate_mosp_line_id", "product_id"]
        request.env.cr.savepoint()
        try:
            res = ApiController().create_document('gen.mosp.comp.line', required_fields, kwargs)
            datas = self.mapping_generator_comp_lines(res)
            if len(datas) > 0: datas = datas[0]
            request.env.cr.commit()   
            
            return ApiController().response_sucess(datas, kwargs, "/generatormosp/line/comp/create")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, kwargs, "/generatormosp/line/comp/create") 

    @http.route(["/generatormosp/line/comp/update"], type="json", auth="public", method="GET", scrf=False)
    def update_generatormosp_comp_line(self, updates, **kwargs):
        """ update generator.mosp.line """
        request.env.cr.savepoint()
        require_fields = ['id']
        result = []

        # convert into list
        if type(updates) == dict:
            updates = [updates]

        try:
            for row in updates:
                cur_generator_mosp_lines = ApiController().update_document(                    
                    'gen.mosp.comp.line',
                    row, 
                    require_fields
                )

                request.env.cr.commit()
                generator_mosp_lines = self.mapping_generator_comp_lines(cur_generator_mosp_lines)
                if len(generator_mosp_lines) > 0: generator_mosp_lines = generator_mosp_lines[0]
                result.append(generator_mosp_lines)

            return ApiController().response_sucess(result, updates, "/generatormosp/line/comp/update")
        except Exception as e:
            request.env.cr.rollback()   
            return ApiController().response_failed(e, updates, "/generatormosp/line/comp/update")

    @http.route(["/generatormosp/line/comp/delete"], type="json", auth="public", method="POST", scrf=False)
    def delete_generatormosp_comp_line(self, ids):
        """ delete gen.mosp.comp.line 

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
            result = ApiController().delete_document('gen.mosp.comp.line', ids)
            request.env.cr.commit()
            return ApiController().response_sucess(result, ids, "/generatormosp/line/comp/delete/")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, ids, "/generatormosp/line/comp/delete")

    #################
    # REQUIRED ITEM #
    #################

    @http.route(["/generatormosp/reqitems/get"], type="json", auth="public", method="GET", scrf=False)
    def get_generatormosp_reqitems_line(self, **kwargs):
        """ get 'required.items' """
        try:
            datas = request.env['required.items'].sudo().search(kwargs.get('search') or [])
            datas = self.mapping_generator_comp_lines(datas)
            return ApiController().response_sucess(datas, kwargs, "/generatormosp/reqitems/get/")
        except Exception as e:
            return ApiController().response_failed(e, kwargs, "/generatormosp/reqitems/get/")