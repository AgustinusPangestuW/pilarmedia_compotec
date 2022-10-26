import json, copy
from odoo import http, _
from odoo.http import request
from .api import RequestError, ApiController


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

            return ApiController().response_sucess(self, wrappings, kwargs, "/wrapping/create")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(self, e, kwargs, "/wrapping/create")

    @http.route(['/wrapping/update'], type="json", auth="public", method="POST", csrf=False)
    def update(self, id, updates, **kwargs):
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
        params.update({
            'id': id,
            'updates': updates
        })

        try:
            cur_wrapping = ApiController().validate_base_on_id("wrapping", "wrapping", id, return_res=True)
            
            updates_wrapping = copy.deepcopy(updates)
            if 'wrapping_deadline_line' in updates_wrapping:
                del updates_wrapping['wrapping_deadline_line']
            updates_wrapping_deadline_line = copy.deepcopy(updates.get('wrapping_deadline_line'))

            # wrapping
            for k, v in updates_wrapping.items():
                cur_wrapping[k] = v

            # wrapping deadline line
            if type(updates_wrapping_deadline_line) == list:
                # lines
                if len(updates_wrapping_deadline_line) > 0 and type(updates_wrapping_deadline_line[0]) == dict:
                    updates_wrapping_deadline_line = [(0,0, 
                        {
                            # val Wrapping Deadline Working Time Line
                            key: [(0,0,val_wt) for val_wt in val] 
                            if type(val) == list and type(val[0]) == dict 
                            else val
                        for key, val in dl.items() } 
                    ) for dl in updates_wrapping_deadline_line]

                # reset / delete wrapping deadline line
                cur_wrapping.wrapping_deadline_line = [(5,0,0)]
                cur_wrapping.wrapping_deadline_line = updates_wrapping_deadline_line

            if kwargs.get('draft'):
                cur_wrapping.action_draft()
            elif kwargs.get('submit'):
                cur_wrapping.action_submit()
            elif kwargs.get('cancel'):
                cur_wrapping.action_cancel()
                
            request.env.cr.commit()                

            return ApiController().response_sucess(cur_wrapping, params, "/wrapping/update")
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