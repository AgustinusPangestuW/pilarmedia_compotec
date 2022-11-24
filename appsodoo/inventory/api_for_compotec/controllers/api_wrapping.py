import json, copy
from odoo import http, _
from odoo.http import request
from .api import RequestError, ApiController
from odoo.exceptions import ValidationError


class APIWrapping(http.Controller):
    def mapping_values(self, wrapping:object):
        return [{
            'id': i.id,
            'name': i.name,
            'date': i.date,
            'job': i.job.name,
            'job_id': i.job.id,
            'shift': i.shift.name,
            'shift_id': i.shift.id,
            'keeper': i.keeper.name,
            'keeper_id': i.keeper.id,
            'leader': i.leader.name,
            'leader_id': i.leader.id,
            'operators_absent': [{'name':v.name, 'id':v.id} for v in i.operator_absent_ids],
            'backups': [{'name':v.name, 'id':v.id} for v in i.backup_ids],
            'wrapping_lines': [{
                'id': v.id,
                'wrapping_id': v.wrapping_deadline_id.id,
                'product': v.product.name,
                'product_id': v.product.id,
                'machine': v.shift_deadline.name,
                'machine_id': v.shift_deadline.id,
                'operators': [{'id':o.id, 'name':o.name} for o in v.operator_ids],
                'note': v.note,
                'total_ok': v.total_ok,
                'ng': v.ng,
                'total': v.total,
                'uom': v.total_ok_uom.name,
                'uom_id': v.total_ok_uom.id,
                'working_time_lines': [{
                    'id': wt.id,
                    'wrapping_line_id': wt.wrapping_deadline_working_time_id.id,
                    'working_time': wt.name,
                    'working_time_id': wt.id,
                    'output': wt.output, 
                    'break_time': wt.break_time,
                    'rest_time': wt.rest_time,
                    'plastic_roll_change_time': wt.plastic_roll_change_time,
                    'product_change_time': wt.product_change_time
                } for wt in v.wrapping_deadline_working_time_line]
            } for v in i.wrapping_deadline_line]
        } for i in wrapping]

    ###########
    # MAPPING #
    ###########

    def mapping_wrapping(self, wrapping:object, ret_lines=False):
        res = []
        model_obj = request.env['wrapping']
        for i in wrapping:
            temp_res = i.read(list(set(model_obj._fields)))

            if ret_lines:
                wrapping_lines = self.mapping_wrapping_lines(i.wrapping_deadline_line)
                temp_res[0].update({'wrapping_deadline_line': wrapping_lines})
            
            res.append(temp_res[0])
        
        return res

    def mapping_wrapping_lines(self, wrapping_deadline_line:object, ret_lines=False):
        res = []
        model_obj = request.env['wrapping.deadline.line']
        for i in wrapping_deadline_line: 
            res.append(i.read(list(set(model_obj._fields)))[0])

            if ret_lines:
                working_time_lines = self.mapping_wrapping_workingtime_lines(i.wrapping_working_time_line)
                res[0].update({'wrapping_working_time_line': working_time_lines})
        
        return res

    def mapping_working_time_lines(self, wrapping_working_times:object):
        res = []
        model_obj = request.env['wrapping.deadline.working.time.line']
        for i in wrapping_working_times: 
            res.append(i.read(list(set(model_obj._fields)))[0])
        
        return res

    ############
    # WRAPPING #
    ############

    @http.route(['/wrapping/get'], type="json", auth="public", method="GET", csrf=False)
    def get(self, **kwargs):
        """
        REST API GET for table `Wrapping`

        parameters:
        -----------
        kwargs['search']: list of list
            ex: [['id', '=', '1']]
        """
        try:
            res = request.env['wrapping'].sudo().search(kwargs.get('search') or [])
            wrappings = self.mapping_values(res)
            return ApiController().response_sucess(wrappings, kwargs, "/wrapping/get")
        except Exception as e:
            return ApiController().response_failed(e, kwargs, "/wrapping/get")

    @http.route(['/wrapping/create'], type="json", auth="public", method="POST", csrf=False)
    def create(self, **kwargs):
        """
        REST API POST for create table `wrapping`
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
                                # val Wrapping Deadline Working Time Line
                                key: [(0,0,val_wt) for val_wt in val] 
                                if type(val) == list and type(val[0]) == dict 
                                else val
                            for key, val in dl.items() } 
                        ) for dl in kwargs[d]]

            res = request.env['wrapping'].sudo().create(kwargs)
            wrappings = self.mapping_values(res)
            request.env.cr.commit()                

            return ApiController().response_sucess(wrappings, kwargs, "/wrapping/create")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, kwargs, "/wrapping/create")

    @http.route(['/wrapping/update'], type="json", auth="public", method="POST", csrf=False)
    def update(self, updates, **kwargs):
        """
        REST API POST for update table `wrapping`

        parameters:
        -----------
        id: string / int (id of wrapping)
        updates: dict data for edit.
            ex: updates : {'res_ok': 10}  => it will be update field `res_ok` with val `10`
        """
        request.env.cr.savepoint()
        params = copy.deepcopy(kwargs)
        params.update({'updates': updates})

        try:
            if type(updates) != list: raise ValidationError(_("value in key updates must be list of dict."))
            res_updates = []
            for rec in updates:
                if not rec.get('id'): raise ValidationError(_("key `id` is required for process update."))

                cur_wrapping = ApiController().validate_base_on_id("wrapping", "wrapping", int(rec['id']), return_res=True)
                updates_wrapping = copy.deepcopy(rec)
                if 'wrapping_deadline_line' in updates_wrapping:
                    del updates_wrapping['wrapping_deadline_line']
                updates_wrapping_deadline_line = copy.deepcopy(rec.get('wrapping_deadline_line'))

                # wrapping
                for k, v in updates_wrapping.items():
                    if k not in ['draft', 'submit', 'cancel', "id"]:
                        if v and type(v) == list and type(v[0]) == dict:
                            cur_wrapping[k] = ApiController().updates_lines(v)
                        else: cur_wrapping[k] = v

                # wrapping deadline line
                cur_wrapping["wrapping_deadline_line"] = ApiController().updates_lines(updates_wrapping_deadline_line)

                if rec.get('draft'):
                    cur_wrapping.action_draft()
                elif rec.get('submit'):
                    cur_wrapping.action_submit()
                elif rec.get('cancel'):
                    cur_wrapping.action_cancel()

                wrappings_row = self.mapping_values(cur_wrapping)
                res_updates.append(wrappings_row)
                    
            request.env.cr.commit()

            return ApiController().response_sucess(res_updates, params, "/wrapping/update")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, params, "/wrapping/update")

    @http.route(['/wrapping/delete'], type="json", auth="public", method="GET", scrf=False)
    def delete(self, ids, **kwargs):
        """
        REST API for delete wrapping base on ids

        Parameters:
        -----------
        ids: list (id wrapping)
        """
        request.env.cr.savepoint()
        params = copy.deepcopy(kwargs)
        params.update({'ids':ids})
        try:
            for id in ids:
                ApiController().validate_base_on_id("wrapping", "wrapping", id)
            res = request.env['wrapping'].sudo().search([('id', 'in', ids)]).unlink()
            request.env.cr.commit()                

            return ApiController().response_sucess(res, params, "/wrapping/delete")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, params, "/wrapping/delete")

    #################
    # WRAPPING LINE #
    #################
    
    @http.route(["/wrapping/line/get"], type="json", auth="public", method="GET", scrf=False)
    def get_wrapping_line(self, **kwargs):
        """ get wrapping.deadline.line """
        try:
            ret_lines = False
            if kwargs.get('ret_lines'):
                ret_lines = kwargs.get('ret_lines')
                del kwargs['ret_lines']

            wrapping_lines = request.env['wrapping.deadline.line'].sudo().search(kwargs.get('search') or [])
            wrapping_lines = self.mapping_wrapping_lines(wrapping_lines, ret_lines)
            return ApiController().response_sucess(wrapping_lines, kwargs, "/wrapping/line/get/")
        except Exception as e:
            return ApiController().response_failed(e, kwargs, "/wrapping/line/get/")

    @http.route(['/wrapping/line/create'], type="json", auth="public", method="POST", scrf=False)
    def create_wrapping_line(self, **kwargs):
        """ create wrapping.deadline.line """      
        required_fields = ["wrapping_deadline_id", "product", "shift_deadline"]
        request.env.cr.savepoint()
        try:
            ret_lines = False
            if kwargs.get('ret_lines'):
                ret_lines = kwargs.get('ret_lines')
                del kwargs['ret_lines']

            res = ApiController().create_document('wrapping.deadline.line', required_fields, kwargs)
            wrapping_lines = self.mapping_wrapping_lines(res, ret_lines)
            if len(wrapping_lines) > 0: wrapping_lines = wrapping_lines[0]
            request.env.cr.commit()   
            
            return ApiController().response_sucess(wrapping_lines, kwargs, "/wrapping/line/create")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, kwargs, "/wrapping/line/create") 

    @http.route(["/wrapping/line/update"], type="json", auth="public", method="GET", scrf=False)
    def update_wrapping_line(self, updates, **kwargs):
        """ update wrapping.deadline.line """
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

                cur_wrapping_line = ApiController().update_document(                    
                    'wrapping.deadline.line',
                    row, 
                    require_fields,
                    ['wrapping_deadline_working_time_line']
                )

                request.env.cr.commit()
                wrapping_line = self.mapping_wrapping_lines(cur_wrapping_line, True if params.get('ret_lines') else False)
                if len(wrapping_line) > 0: wrapping_line = wrapping_line[0]
                result.append(wrapping_line)

            return ApiController().response_sucess(result, updates, "/wrapping/line/update")
        except Exception as e:
            request.env.cr.rollback()   
            return ApiController().response_failed(e, updates, "/wrapping/line/update")

    @http.route(["/wrapping/line/delete"], type="json", auth="public", method="POST", scrf=False)
    def delete_wrapping_line(self, ids):
        """ delete wrapping.deadline.line

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
            result = ApiController().delete_document('wrapping.deadline.line', ids)
            request.env.cr.commit()
            return ApiController().response_sucess(result, ids, "/wrapping/line/delete/")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, ids, "/wrapping/line/delete")

    #########################
    # WRAPPING WORKING TIME #
    #########################
    
    @http.route(["/wrapping/workingtime/get"], type="json", auth="public", method="GET", scrf=False)
    def get_wrapping_workingtime_line(self, **kwargs):
        """ get wrapping.deadline.working.time.line """
        try:
            working_time_lines = request.env['wrapping.deadline.working.time.line'].sudo().search(kwargs.get('search') or [])
            working_time_lines = self.mapping_working_time_lines(working_time_lines)
            return ApiController().response_sucess(working_time_lines, kwargs, "/wrapping/workingtime/get/")
        except Exception as e:
            return ApiController().response_failed(e, kwargs, "/wrapping/workingtime/get/")

    @http.route(['/wrapping/workingtime/create'], type="json", auth="public", method="POST", scrf=False)
    def create_wrapping_workingtime_line(self, **kwargs):
        """ create wrapping.deadline.working.time.line """      
        required_fields = ["wrapping_deadline_working_time_id", "working_time"]
        request.env.cr.savepoint()
        try:
            res = ApiController().create_document('wrapping.deadline.working.time.line', required_fields, kwargs)
            working_time_lines = self.mapping_working_time_lines(res)
            if len(working_time_lines) > 0: working_time_lines = working_time_lines[0]
            request.env.cr.commit()   
            
            return ApiController().response_sucess(working_time_lines, kwargs, "/wrapping/workingtime/create")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, kwargs, "/wrapping/workingtime/create") 

    @http.route(["/wrapping/workingtime/update"], type="json", auth="public", method="GET", scrf=False)
    def update_wrapping_workingtime_line(self, updates, **kwargs):
        """ update wrapping.deadline.working.time.line """
        request.env.cr.savepoint()
        require_fields = ['id']
        result = []

        # convert into list
        if type(updates) == dict:
            updates = [updates]

        try:
            for row in updates:
                cur_working_time_lines = ApiController().update_document(                    
                    'wrapping.deadline.working.time.line',
                    row, 
                    require_fields
                )

                request.env.cr.commit()
                working_time_lines = self.mapping_working_time_lines(cur_working_time_lines)
                if len(working_time_lines) > 0: working_time_lines = working_time_lines[0]
                result.append(working_time_lines)

            return ApiController().response_sucess(result, updates, "/wrapping/workingtime/update")
        except Exception as e:
            request.env.cr.rollback()   
            return ApiController().response_failed(e, updates, "/wrapping/workingtime/update")

    @http.route(["/wrapping/workingtime/delete"], type="json", auth="public", method="POST", scrf=False)
    def delete_wrapping_workingtime_line(self, ids):
        """ delete wrapping.deadline.working.time.line

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
            result = ApiController().delete_document('wrapping.deadline.working.time.line', ids)
            request.env.cr.commit()
            return ApiController().response_sucess(result, ids, "/wrapping/workingtime/delete/")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, ids, "/wrapping/workingtime/delete")
