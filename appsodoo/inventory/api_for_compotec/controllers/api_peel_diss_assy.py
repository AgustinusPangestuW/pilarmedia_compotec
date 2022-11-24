import json, copy
from odoo import http, _
from odoo.http import request
from .api import RequestError, ApiController


class APIPeelDissAssy(http.Controller):
    def mapping_values(self, peel_diss_assy:object):
        return [{
            'id': i.id,
            'name': i.name,
            'date': i.date,
            'job': i.job.name,
            'job_id': i.job.id,
            'peel_diss_assy_lines': [{
                'id': l.id,
                'peel_diss_assy_id': l.peel_diss_assy_id.id,
                'qty': l.qty,
                'operator': l.user.name,
                'operator_id': l.user.id,
                'product': l.product_id.name,
                'product_id': l.product_id.id,
                'bom': l.bom_id.product_tmpl_id.name, 
                'bom_id': l.bom_id.id, 
                'description': l.description,
                'peel_diss_assy_line_component': [{
                    'id': c.id,
                    'peel_diss_assy_line_id': c.peel_diss_assy_line_id.id,
                    'product_id': c.product_id.id,
                    'product': c.product_id.name, 
                    'peeled_total': c.peeled_total,
                    'ok': c.ok,
                    'ng': c.ng,
                } for c in l.peel_diss_assy_component_line]
            } for l in i.peel_diss_assy_line]
        } for i in peel_diss_assy]

    ###########
    # MAPPING #
    ###########

    def mapping_peeldissassy(self, peeldissassy:object, ret_lines=False):
        res = []
        model_obj = request.env['peel.diss.assy']
        for i in peeldissassy:
            temp_res = i.read(list(set(model_obj._fields)))

            if ret_lines:
                wholesalejob_lines = self.mapping_peeldissassy_lines(i.peel_diss_assy_line)
                temp_res[0].update({'peel_diss_assy_line': wholesalejob_lines})
            
            res.append(temp_res[0])
        
        return res

    def mapping_peeldissassy_lines(self, peel_diss_assy_line:object, ret_lines=False):
        res = []
        model_obj = request.env['peel.diss.assy.line']
        for i in peel_diss_assy_line: 
            res.append(i.read(list(set(model_obj._fields)))[0])

            if ret_lines:
                peel_diss_assy_components = self.mapping_peeldissassy_components(i.peel_diss_assy_component_line)
                res[0].update({'peel_diss_assy_component_line': peel_diss_assy_components})
        
        return res

    def mapping_peeldissassy_components(self, peel_diss_assy_components:object):
        res = []
        model_obj = request.env['peel.diss.assy.component.line']
        for i in peel_diss_assy_components: 
            res.append(i.read(list(set(model_obj._fields)))[0])

        return res

    ##################
    # PEEL DISS ASSY #
    ##################

    @http.route(['/peeldissassy/get'], type="json", auth="public", method="GET", csrf=False)
    def get(self, **kwargs):
        """
        REST API GET for table `Peel Diss Assy`

        parameters:
        -----------
        kwargs['search']: list of list
            ex: [['id', '=', '1']]
        """
        try:
            res = request.env['peel.diss.assy'].sudo().search(kwargs.get('search') or [])
            peel_diss_assys = self.mapping_values(res)
            return ApiController().response_sucess(peel_diss_assys, kwargs, "/peeldissassy/get")
        except Exception as e:
            return ApiController().response_failed(e, kwargs, "/peeldissassy/get")

    @http.route(['/peeldissassy/create'], type="json", auth="public", method="POST", csrf=False)
    def create(self, **kwargs):
        """
        REST API POST for create table `peel_diss_assy`
        """
        request.env.cr.savepoint()
        try:
            for d in kwargs:
                # rubah data kwargs yang bertipe list of dict menjadi list of tuple agar tidak hardcode
                if type(kwargs[d]) == list:
                    # lines
                    if len(kwargs[d]) > 0 and type(kwargs[d][0]) == dict:
                        kwargs[d] = [(0,0, 
                            {
                                # val Peel Diss Assy Component
                                key: [(0,0,val_wt) for val_wt in val] 
                                if type(val) == list and type(val[0]) == dict 
                                else val
                            for key, val in dl.items() } 
                        ) for dl in kwargs[d]]

            res = request.env['peel.diss.assy'].sudo().create(kwargs)
            peel_diss_assys = self.mapping_values(res)
            request.env.cr.commit()                

            return ApiController().response_sucess(peel_diss_assys, kwargs, "/peeldissassy/create")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, kwargs, "/peeldissassy/create")

    @http.route(['/peeldissassy/update'], type="json", auth="public", method="POST", csrf=False)
    def update(self, id, updates, **kwargs):
        """
        REST API POST for update table `peel_diss_assy`

        parameters:
        -----------
        id: string / int (id of peel_diss_assy)
        updates: dict data for edit.
            ex: updates : {'res_ok': 10}  => it will be update field `res_ok` with val `10`
        """
        request.env.cr.savepoint()
        params = copy.deepcopy(kwargs)
        params.update({'id':id, 'updates':updates})
        try:
            cur_peel_diss_assy = ApiController().validate_base_on_id("peel.diss.assy", "peel_diss_assy", id, return_res=True)
            
            updates_peel_diss_assy = copy.deepcopy(updates)
            if 'peel_diss_assy_line' in updates_peel_diss_assy:
                del updates_peel_diss_assy['peel_diss_assy_line']
            updates_peel_diss_assy_line = copy.deepcopy(updates.get('peel_diss_assy_line'))

            # peel_diss_assy
            for k, v in updates_peel_diss_assy.items():
                cur_peel_diss_assy[k] = v

            # peel_diss_assy line
            if type(updates_peel_diss_assy_line) == list:
                # lines
                if len(updates_peel_diss_assy_line) > 0 and type(updates_peel_diss_assy_line[0]) == dict:
                    updates_peel_diss_assy_line = [(0,0, 
                        {
                            # val Peel Diss Assy Component Line
                            key: [(0,0,val_wt) for val_wt in val] 
                            if type(val) == list and type(val[0]) == dict 
                            else val
                        for key, val in dl.items() } 
                    ) for dl in updates_peel_diss_assy_line]

                # reset / delete peel_diss_assy line
                cur_peel_diss_assy.peel_diss_assy_line = [(5,0,0)]
                cur_peel_diss_assy.peel_diss_assy_line = updates_peel_diss_assy_line

            if kwargs.get('draft'):
                cur_peel_diss_assy.action_draft()
            elif kwargs.get('submit'):
                cur_peel_diss_assy.action_submit()
            elif kwargs.get('cancel'):
                cur_peel_diss_assy.action_cancel()
                
            request.env.cr.commit()   
            cur_peel_diss_assy = self.mapping_values(cur_peel_diss_assy)      
            return ApiController().response_sucess(cur_peel_diss_assy, params, "/peel_diss_assy/update")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, params, "/peel_diss_assy/update")

    @http.route(['/peeldissassy/delete'], type="json", auth="public", method="GET", scrf=False)
    def delete(self, ids, **kwargs):
        """
        REST API for delete peel_diss_assy base on ids

        Parameters:
        -----------
        ids: list (id peel_diss_assy)
        """
        request.env.cr.savepoint()
        params = copy.deepcopy(kwargs)
        params.update({'ids':ids})
        try:
            for id in ids:
                res = ApiController().validate_base_on_id("peel.diss.assy", "peel_diss_assy", id, return_res=True)
                res.unlink()

            request.env.cr.commit()                
            return ApiController().response_sucess(True, params, "/peeldissassy/delete")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, params, "/peeldissassy/delete")

    #######################
    # PEEL DISS ASSY LINE #
    #######################
    
    @http.route(["/peeldissassy/line/get"], type="json", auth="public", method="GET", scrf=False)
    def get_peeldissassy_line(self, **kwargs):
        """ get table peel.diss.assy.line """
        try:
            ret_lines = False
            if kwargs.get('ret_lines'):
                ret_lines = kwargs.get('ret_lines')
                del kwargs['ret_lines']

            peeldissassy_lines = request.env['peel.diss.assy.line'].sudo().search(kwargs.get('search') or [])
            peeldissassy_lines = self.mapping_peeldissassy_lines(peeldissassy_lines, ret_lines)
            return ApiController().response_sucess(peeldissassy_lines, kwargs, "/peeldissassy/line/get/")
        except Exception as e:
            return ApiController().response_failed(e, kwargs, "/peeldissassy/line/get/")

    @http.route(['/peeldissassy/line/create'], type="json", auth="public", method="POST", scrf=False)
    def create_peeldissassy_line(self, **kwargs):
        """ create table peel.diss.assy.line """      
        required_fields = ["peel_diss_assy_id", "user", "bom_id", "product_id"]
        request.env.cr.savepoint()
        try:
            ret_lines = False
            if kwargs.get('ret_lines'):
                ret_lines = kwargs.get('ret_lines')
                del kwargs['ret_lines']

            res = ApiController().create_document('peel.diss.assy.line', required_fields, kwargs)
            peeldissassy_lines = self.mapping_peeldissassy_lines(res, ret_lines)
            if len(peeldissassy_lines) > 0: peeldissassy_lines = peeldissassy_lines[0]
            request.env.cr.commit()   
            
            return ApiController().response_sucess(peeldissassy_lines, kwargs, "/peeldissassy/line/create")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, kwargs, "/peeldissassy/line/create")   

    @http.route(["/peeldissassy/line/update"], type="json", auth="public", method="GET", scrf=False)
    def update_peeldissassy_line(self, updates):
        """ update table peel.diss.assy.line """
        request.env.cr.savepoint()
        require_fields = ['id']
        result = []

        # convert into list
        if type(updates) == dict:
            updates = [updates]

        try:
            for row in updates:
                ret_lines = False
                if row.get('ret_lines'):
                    ret_lines = row.get('ret_lines')
                    del row['ret_lines']

                cur_peeldissassy_lines = ApiController().update_document(                    
                    'peel.diss.assy.line',
                    row, 
                    require_fields
                )

                request.env.cr.commit()
                peeldissassy_lines = self.mapping_peeldissassy_lines(cur_peeldissassy_lines, ret_lines)
                if len(peeldissassy_lines) > 0: peeldissassy_lines = peeldissassy_lines[0]
                result.append(peeldissassy_lines)

            return ApiController().response_sucess(result, updates, "/peeldisaasy/line/update")
        except Exception as e:
            request.env.cr.rollback()   
            return ApiController().response_failed(e, updates, "/peeldisaasy/line/update")

    @http.route(["/peeldissassy/line/delete"], type="json", auth="public", method="POST", scrf=False)
    def delete_detailsng(self, ids):
        """ delete table peel.diss.assy.line

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
            result = ApiController().delete_document('peel.diss.assy.line', ids)
            request.env.cr.commit()
            return ApiController().response_sucess(result, ids, "/peeldissassy/line/delete/")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, ids, "/peeldissassy/line/delete")

    #############
    # COMPONENTS #
    #############

    @http.route(["/peeldissassy/comp/get"], type="json", auth="public", method="GET", scrf=False)
    def get_peeldissassy_comp_line(self, **kwargs):
        """ get table peel.diss.assy.component.line """
        try:
            comp_lines = request.env['peel.diss.assy.component.line'].sudo().search(kwargs.get('search') or [])
            comp_lines = self.mapping_peeldissassy_components(comp_lines)
            return ApiController().response_sucess(comp_lines, kwargs, "/peeldissassy/comp/get/")
        except Exception as e:
            return ApiController().response_failed(e, kwargs, "/peeldissassy/comp/get/")

    @http.route(['/peeldissassy/comp/create'], type="json", auth="public", method="POST", scrf=False)
    def create_peeldissassy_comp_line(self, **kwargs):
        """ create table peel.diss.assy.component.line """      
        required_fields = ["peel_diss_assy_line_id", "product_id"]
        request.env.cr.savepoint()
        try:
            res = ApiController().create_document('peel.diss.assy.component.line', required_fields, kwargs)
            peeldissassy_components = self.mapping_peeldissassy_components(res)
            if len(peeldissassy_components) > 0: peeldissassy_components = peeldissassy_components[0]
            request.env.cr.commit()   
            
            return ApiController().response_sucess(peeldissassy_components, kwargs, "/peeldissassy/comp/create")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, kwargs, "/peeldissassy/comp/create")   

    @http.route(["/peeldissassy/comp/update"], type="json", auth="public", method="GET", scrf=False)
    def update_peeldissassy_comp_line(self, updates):
        """ update table peel.diss.assy.component.line """
        request.env.cr.savepoint()
        require_fields = ['id']
        result = []

        # convert into list
        if type(updates) == dict:
            updates = [updates]

        try:
            for row in updates:
                # cannot change product_id
                if row.get('product_id'):
                    raise RequestError(_("cannot change field product_id. cause product_id fetch from BOM ID."))

                cur_peeldissassy_comp_lines = ApiController().update_document(                    
                    'peel.diss.assy.component.line',
                    row, 
                    require_fields
                )

                request.env.cr.commit()
                peeldissassy_components = self.mapping_peeldissassy_components(cur_peeldissassy_comp_lines)
                if len(peeldissassy_components) > 0: peeldissassy_components = peeldissassy_components[0]
                result.append(peeldissassy_components)

            return ApiController().response_sucess(result, updates, "/peeldisaasy/comp/update")
        except Exception as e:
            request.env.cr.rollback()   
            return ApiController().response_failed(e, updates, "/peeldisaasy/comp/update")

    