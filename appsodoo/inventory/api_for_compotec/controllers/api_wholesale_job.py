import json, copy
from odoo import http, _
from odoo.http import request
from .api import RequestError, ApiController


class APIWholesaleJob(http.Controller):
    def mapping_values(self, wholesalejob:object):     
        return [{
            'id': rec.id,
            'name': rec.name,
            'date': rec.date,
            'job': rec.job_id.name,
            'job_id': rec.job_id.id,
            'shift': rec.shift.name,
            'shift_id': rec.shift.id,
            'opearation_type_id_ng': rec.operation_type_id_ng.id,
            'opearation_type_ng': rec.operation_type_id_ng.name,
            'operation_type_id_ok': rec.operation_type_id_ok.id,
            'operation_type_ok': rec.operation_type_id_ok.name,
            'company': rec.company_id.name,
            'company_id': rec.company_id.id,
            'checked_coordinator': rec.checked_coordinator.name,
            'checked_coordinator_id': rec.checked_coordinator.id,
            'checked_qc': rec.checked_qc.name,
            'checked_qc_id': rec.checked_qc.id,
            'wholesale_job_lines': [{
                'id': lines.id,
                'wholesale_job_id': lines.wholesale_job_id.id,
                "product_id": lines.product_id.id,
                "product": lines.product_id.name,
                'job': lines.job_id.name,
                'job_id': lines.job_id.id,
                'operator': lines.operator.name,
                'operator_id': lines.operator.id,
                'total_ok': lines.total_ok,
                'total_ng': lines.total_ng,
                'total_set': lines.total_set,
                'total_pcs': lines.total_pcs,
                'is_set': lines.is_set,
                'factor': lines.factor,
                'biggest_lot': int(lines.biggest_lot.name),
                'wholesale_job_lot_lines': [{
                    'id': lot_lines.id,
                    'wholesale_job_line_id': lot_lines.wholesale_job_line_id.id,
                    'lot_id': lot_lines.lot_id,
                    'ok': lot_lines.ok,
                    'ng': lot_lines.ng
                } for lot_lines in lines.wholesale_job_lot_lines]
            } for lines in rec.wholesale_job_lines]
        } for rec in wholesalejob]

    @http.route(['/wholesalejob/get'], type="json", auth="public", method="GET", csrf=False)
    def get(self, **kwargs):
        """
        REST API GET for table `wholesalejob`

        parameters:
        -----------
        kwargs['search']: list of list
            ex: [['id', '=', '1']]
        """
        try:
            res = request.env['wholesale.job'].sudo().search(kwargs.get('search') or [])
            wholesale_jobs = self.mapping_values(res)
            return ApiController().response_sucess(wholesale_jobs, kwargs, "/wholesalejob/get")
        except Exception as e:
            return ApiController().response_failed(e, kwargs, "/wholesalejob/get")

    @http.route(['/wholesalejob/create'], type="json", auth="public", method="POST", csrf=False)
    def create(self, **kwargs):
        """
        REST API POST for create table `wholesalejob`
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
                                # val wholesalejob Lines
                                key: [(0,0,val_wt) for val_wt in val] 
                                if type(val) == list and type(val[0]) == dict 
                                else val
                            for key, val in dl.items() } 
                        ) for dl in kwargs[d]]

            res = request.env['wholesale.job'].sudo().create(kwargs)
            wholesale_jobs = self.mapping_values(res)
            request.env.cr.commit()                

            return ApiController.response_sucess(ApiController, wholesale_jobs, kwargs, "/wholesalejob/create")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, kwargs, "/wholesalejob/create")    

    @http.route(['/wholesalejob/update'], type="json", auth="public", method="POST", csrf=False)
    def update(self, id, updates, **kwargs):
        """
        REST API POST for update table `wholesalejob`

        parameters:
        -----------
        id: string / int (id of wholesalejob)
        updates: dict data for edit.
            ex: updates : {'res_ok': 10}  => it will be update field `res_ok` with val `10`
        """
        request.env.cr.savepoint()
        params = copy.deepcopy(kwargs)
        params.update({
            'id': id,
            'updates': updates
        })

        try:
            cur_wholesale_job = ApiController().validate_base_on_id("wholesale.job", "wholesale_job", id, return_res=True)
            
            updates_wholesale_job = copy.deepcopy(updates)
            if 'wholesale_job_lines' in updates_wholesale_job:
                del updates_wholesale_job['wholesale_job_lines']
            updates_wholesale_job_lines = copy.deepcopy(updates.get('wholesale_job_lines'))

            # wholesale job
            for k, v in updates_wholesale_job.items():
                cur_wholesale_job[k] = v

            # update/new/delete wholesalejob line
            cur_wholesale_job['wholesale_job_lines'] = ApiController().updates_lines(updates_wholesale_job_lines)

            if kwargs.get('draft'):
                cur_wholesale_job.action_draft()
            elif kwargs.get('submit'):
                cur_wholesale_job.action_submit()
            elif kwargs.get('cancel'):
                cur_wholesale_job.action_cancel()
            
            request.env.cr.commit()              
            wholesale_jobs = self.mapping_values(cur_wholesale_job)
            if len(wholesale_jobs) > 0: wholesale_jobs = wholesale_jobs[0]
            return ApiController().response_sucess(wholesale_jobs, params, "/wholesalejob/update")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, params, "/wholesalejob/update")

    @http.route(['/wholesalejob/delete'], type="json", auth="public", method="GET", scrf=False)
    def delete(self, ids, **kwargs):
        """
        REST API for delete wholesalejob base on ids

        Parameters:
        -----------
        ids: list (id wholesale_job)
        """
        request.env.cr.savepoint()
        params = copy.deepcopy(kwargs)
        params.update({'ids':ids})
        try:
            for id in ids:
                res = ApiController().validate_base_on_id("wholesale.job", "wholesale_job", id, return_res=True)
                res.unlink()

            request.env.cr.commit()    
            return ApiController().response_sucess(res, params, "/wholesalejob/delete")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, params, "/wholesalejob/delete")
