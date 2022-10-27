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

            return ApiController().response_sucess(self, peel_diss_assys, kwargs, "/peeldissassy/create")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(self, e, kwargs, "/peeldissassy/create")

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