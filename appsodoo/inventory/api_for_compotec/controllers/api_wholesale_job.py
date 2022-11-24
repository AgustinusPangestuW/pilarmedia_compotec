import json, copy
from odoo import http, _
from odoo.exceptions import ValidationError
from odoo.http import request
from .api import RequestError, ApiController


class APIWholesaleJob(http.Controller):
    def mapping_values(self, wholesalejob:object):     
        return [{
            'id': rec.id,
            'name': rec.name,
            'date': rec.date,
            'job': rec.job.name,
            'job_id': rec.job.id,
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

    #############
    ## MAPPING ##
    #############

    def mapping_wholesalejob(self, si:object, ret_lines=False):
        res = []
        model_obj = request.env['wholesale.job']
        for i in si:
            temp_res = i.read(list(set(model_obj._fields)))

            if ret_lines:
                wholesalejob_lines = self.mapping_wholesalejob_lines(i.wholesale_job_lines)
                temp_res[0].update({'wholesale_job_lines': wholesalejob_lines})
            
            res.append(temp_res[0])
        
        return res

    def mapping_wholesalejob_lines(self, wholesalejob_lines:object, ret_lines=False):
        res = []
        model_obj = request.env['wholesale.job.line']
        for i in wholesalejob_lines: 
            res.append(i.read(list(set(model_obj._fields)))[0])

            if ret_lines:
                wholesalejob_lot_lines = self.mapping_wholesalejob_lot_lines(i.wholesale_job_lot_lines)
                res[0].update({'wholesale_job_lot_lines': wholesalejob_lot_lines})

                wholesalejob_detail_ng = self.mapping_detail_ng(i.ng_ids)
                res[0].update({'ng_ids': wholesalejob_detail_ng})
        
        return res
    
    def mapping_wholesalejob_lot_lines(self, wholesalejob_lot_lines:object):
        res = []
        model_obj = request.env['wholesale.job.lot.line']
        for i in wholesalejob_lot_lines:
            res = i.read(list(set(model_obj._fields)))            
            res.append(res[0])
        
        return res

    def mapping_detail_ng(self, detail_ng:object):
        res = []
        model_obj = request.env['details.ng']
        for i in detail_ng:
            temp_res = i.read(list(set(model_obj._fields)))            
            res.append(temp_res[0])
        
        return res

    def mapping_lot_line(self, wholesale_job_lot_line:object):
        res = []
        model_obj = request.env['wholesale.job.lot.line']
        for i in wholesale_job_lot_line:
            res.append(i.read(list(set(model_obj._fields)))[0])
        
        return res

    def mapping_details_ng(self, details_ng:object):
        res = []
        model_obj = request.env['details.ng']
        for i in details_ng:
            res.append(i.read(list(set(model_obj._fields)))[0])
        
        return res

    #################
    # WHOLESALE JOB #
    #################

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
            wholesale_jobs = self.mapping_wholesalejob(res)
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

            wholesale_jobs = self.mapping_wholesalejob(res)
            if len(wholesale_jobs) > 0: wholesale_jobs = wholesale_jobs[0]
            request.env.cr.commit()   
            
            return ApiController().response_sucess(wholesale_jobs, kwargs, "/wholesalejob/create")
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
            wholesale_jobs = self.mapping_wholesalejob(cur_wholesale_job)
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

    ######################
    # WHOLESALE JOB LINE #
    ######################   

    @http.route(["/wholesalejob/line/get"], type="json", auth="public", method="GET", scrf=False)
    def get_line(self, **kwargs):
        """ get wholesale job line """
        try:
            ret_lines = False
            if kwargs.get('ret_lines'):
                ret_lines = kwargs.get('ret_lines')
                del kwargs['ret_lines']

            wholesale_job_lines = request.env['wholesale.job.line'].sudo().search(kwargs.get('search') or [])
            wholesale_job_lines = self.mapping_wholesalejob_lines(wholesale_job_lines, ret_lines)
            return ApiController().response_sucess(wholesale_job_lines, kwargs, "/wholesalejob/line/get/")
        except Exception as e:
            return ApiController().response_failed(e, kwargs, "/wholesalejob/line/get/")

    @http.route(['/wholesalejob/line/create'], type="json", auth="public", method="POST", scrf=False)
    def create_wholesalejob_line(self, **kwargs):
        """ create wholesales job line """      
        required_fields = ["wholesale_job_id", "product_id", "operator"]
        request.env.cr.savepoint()
        try:
            ret_lines = False
            if kwargs.get('ret_lines'):
                ret_lines = kwargs.get('ret_lines')
                del kwargs['ret_lines']

            res = ApiController().create_document('wholesale.job.line', required_fields, kwargs)
            wholesale_job_lines = self.mapping_wholesalejob_lines(res, ret_lines)
            if len(wholesale_job_lines) > 0: wholesale_job_lines = wholesale_job_lines[0]
            request.env.cr.commit()   
            
            return ApiController().response_sucess(wholesale_job_lines, kwargs, "/wholesalejob/line/create")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, kwargs, "/wholesalejob/line/create") 

    @http.route(["/wholesalejob/line/update"], type="json", auth="public", method="GET", scrf=False)
    def update_wholesalejob_line(self, updates, **kwargs):
        """ update Wholesale Job Line """
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

                cur_wholesale_job_line = ApiController().update_document(                    
                    'wholesale.job.line',
                    row, 
                    require_fields,
                    ['wholesale_job_lot_lines', "ng_ids"]
                )

                request.env.cr.commit()
                wholesale_job_lines = self.mapping_wholesalejob_lines(cur_wholesale_job_line, True if params.get('ret_lines') else False)
                if len(wholesale_job_lines) > 0: wholesale_job_lines = wholesale_job_lines[0]
                result.append(wholesale_job_lines)

            return ApiController().response_sucess(result, updates, "/wholesalejob/line/update")
        except Exception as e:
            request.env.cr.rollback()   
            return ApiController().response_failed(e, updates, "/wholesalejob/line/update")

    @http.route(["/wholesalejob/line/delete"], type="json", auth="public", method="POST", scrf=False)
    def delete_wholesalejob_line(self, ids):
        """ delete wholesale job line 

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
            result = ApiController().delete_document('wholesale.job.line', ids)
            request.env.cr.commit()
            return ApiController().response_sucess(result, ids, "/wholesalejob/line/delete/")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, ids, "/wholesalejob/line/delete")

    #############
    # DETAIL NG #
    #############

    @http.route(["/detailsng/get"], type="json", auth="public", method="GET", scrf=False)
    def get_detailsng(self, **kwargs):
        """ get table detailsng """
        try:
            details_ng = request.env['details.ng'].sudo().search(kwargs.get('search') or [])
            details_ng = self.mapping_details_ng(details_ng)
            return ApiController().response_sucess(details_ng, kwargs, "/detailsng/get/")
        except Exception as e:
            return ApiController().response_failed(e, kwargs, "/detailsng/get/")

    @http.route(['/detailsng/create'], type="json", auth="public", method="POST", scrf=False)
    def create_detailsng(self, **kwargs):
        """ create table details.ng """      
        required_fields = ["wholesale_job_line_id"]
        request.env.cr.savepoint()
        try:
            res = ApiController().create_document('details.ng', required_fields, kwargs)
            details_ng = self.mapping_details_ng(res)
            if len(details_ng) > 0: details_ng = details_ng[0]
            request.env.cr.commit()   
            
            return ApiController().response_sucess(details_ng, kwargs, "/detailsng/create")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, kwargs, "/detailsng/create")   

    @http.route(["/detailsng/update"], type="json", auth="public", method="GET", scrf=False)
    def update_detailsng(self, updates, **kwargs):
        """ update table details.ng """
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

                cur_details_ng = ApiController().update_document(                    
                    'details.ng',
                    row, 
                    require_fields
                )

                request.env.cr.commit()
                details_ng = self.mapping_details_ng(cur_details_ng)
                if len(details_ng) > 0: details_ng = details_ng[0]
                result.append(details_ng)

            return ApiController().response_sucess(result, updates, "/detailsng/update")
        except Exception as e:
            request.env.cr.rollback()   
            return ApiController().response_failed(e, updates, "/detailsng/update")

    @http.route(["/detailsng/delete"], type="json", auth="public", method="POST", scrf=False)
    def delete_detailsng(self, ids):
        """ delete table details.ng

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
            result = ApiController().delete_document('details.ng', ids)
            request.env.cr.commit()
            return ApiController().response_sucess(result, ids, "/detailsng/delete/")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, ids, "/detailsng/delete")

    ##########################
    # DETAIL LOT  / LOT LINE #
    ##########################

    @http.route(["/lotline/get"], type="json", auth="public", method="GET", scrf=False)
    def get_lotline(self, **kwargs):
        """ get table wholesale.job.lot.line """
        try:
            lot_line = request.env['wholesale.job.lot.line'].sudo().search(kwargs.get('search') or [])
            lot_line = self.mapping_lot_line(lot_line)
            return ApiController().response_sucess(lot_line, kwargs, "/lotline/get/")
        except Exception as e:
            return ApiController().response_failed(e, kwargs, "/lotline/get/")

    @http.route(['/lotline/add'], type="json", auth="public", method="POST", scrf=False)
    def create_lotline(self, wholesale_job_line_id):
        """ create table wholesale.job.lot.line """     
        request.env.cr.savepoint()
        try:
            res = ApiController().validate_base_on_id('wholesale.job.line', 'wholesale_job_line', wholesale_job_line_id, return_res=True)
            res = res.add_job_lot_lines()

            if 'wholesale_job_lot_lines' not in res or len(res['wholesale_job_lot_lines']) <= 0:
                raise RequestError(_("wholesale job lot line is not exist in data."))

            lot_line = self.mapping_lot_line(res.wholesale_job_lot_lines[-1])
            if len(lot_line) > 0: lot_line = lot_line[0]
            request.env.cr.commit()   
            
            return ApiController().response_sucess(lot_line, wholesale_job_line_id, "/lotline/add")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, wholesale_job_line_id, "/lotline/add")   

    @http.route(["/lotline/update"], type="json", auth="public", method="GET", scrf=False)
    def update_lotline(self, updates, **kwargs):
        """ update table wholesale.job.lot.line """
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

                cur_lot_line = ApiController().update_document(                    
                    'wholesale.job.lot.line',
                    row, 
                    require_fields
                )

                request.env.cr.commit()
                lot_line = self.mapping_lot_line(cur_lot_line)
                if len(lot_line) > 0: lot_line = lot_line[0]
                result.append(lot_line)

            return ApiController().response_sucess(result, updates, "/lotline/update")
        except Exception as e:
            request.env.cr.rollback()   
            return ApiController().response_failed(e, updates, "/lotline/update")

    @http.route(["/lotline/remove"], type="json", auth="public", method="POST", scrf=False)
    def delete_lotline(self, wholesale_job_line_id):
        """ delete table wholesale.job.lot.line

        parameters
        ----------
        wholesale_job_line_id : list of integer
            ex : [1,4,66,3]
        """
        request.env.cr.savepoint()
        try:
            result = ApiController().validate_base_on_id('wholesale.job.line', 'wholesale_job_line', wholesale_job_line_id, return_res=True)
            res = result.remove_job_lot_lines()
            sucess = False
            if res: 
                sucess = True
            request.env.cr.commit()
            return ApiController().response_sucess({'sucess': sucess, 'id': wholesale_job_line_id}, wholesale_job_line_id, "/lotline/remove/")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, {'sucess': False, 'id': wholesale_job_line_id}, "/lotline/remove")
