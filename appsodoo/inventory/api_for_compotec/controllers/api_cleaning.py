import json, copy
from odoo import http, _
from odoo.http import request
from .api import RequestError, ApiController


class APICleaning(http.Controller):
    def mapping_values(self, cleaning:object):
        return [{
            'id': i.id,
            'name': i.name,
            'datetime': i.datetime,
            'employee_id': i.user.id,
            'employee': i.user.name,
            'product_id': i.product.id,
            'product': i.product.name,
            'ok': i.res_ok,
            'ng': i.res_ng,
            'rework': i.rework,
            'description': i.description
        } for i in cleaning]

    @http.route(['/cleaning/get'], type="json", auth="public", method="GET", csrf=False)
    def get(self, **kwargs):
        """
        REST API GET for table `Cleaning`

        parameters:
        -----------
        kwargs['search']: list of list
            ex: [['id', '=', '1']]
        """
        try:
            res = request.env['cleaning'].sudo().search(kwargs.get('search') or [])
            cleanings = self.mapping_values(res)
            return ApiController().response_sucess(cleanings, kwargs, "/cleaning/get")
        except Exception as e:
            return ApiController().response_failed(e, kwargs, "/cleaning/get")

    @http.route(['/cleaning/create'], type="json", auth="public", method="POST", csrf=False)
    def create(self, **kwargs):
        """
        REST API POST for create table `Cleaning`
        """
        request.env.cr.savepoint()
        try:
            # value kwargs ditampung ke temp_kwargs untuk proses create `transit_log`
            temp_kwargs = copy.deepcopy(kwargs)
            for d in temp_kwargs:
                # rubah data kwargs yang bertipe list of dict menjadi list of tuple agar tidak hardcode
                if type(temp_kwargs[d]) == list:
                    temp_kwargs[d] = [(0,0, dl) for dl in temp_kwargs[d]]

            res = request.env['cleaning'].sudo().create(temp_kwargs)
            cleanings = self.mapping_values(res)
            request.env.cr.commit()                

            return ApiController().response_sucess(cleanings, kwargs, "/cleaning/create")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, kwargs, "/cleaning/create")

    @http.route(['/cleaning/update'], type="json", auth="public", method="POST", csrf=False)
    def update(self, ids, updates, **kwargs):
        """
        REST API POST for update table `Cleaning`

        parameters:
        -----------
        id: string / int (id of cleaning)
        updates: dict data for edit.
            ex: updates : {'res_ok': 10}  => it will be update field `res_ok` with val `10`
        
        """
        request.env.cr.savepoint()
        params = copy.deepcopy(kwargs)
        params.update({
            'ids': ids,
            'updates': updates
        })
        try:
            for id in ids:
                ApiController().validate_base_on_id("cleaning", "Cleaning", id, return_res=True)

            res = request.env['cleaning'].sudo().search([('id', 'in', ids)]).write(updates)

            for id in ids:
                if kwargs.get('draft'):
                    request.env['cleaning'].sudo().search([('id', 'in', ids)]).action_submit()
                elif kwargs.get('submit'):
                    request.env['cleaning'].sudo().search([('id', 'in', ids)]).action_submit()
                elif kwargs.get('cancel'):
                    request.env['cleaning'].sudo().search([('id', 'in', ids)]).action_cancel()

            request.env.cr.commit()                

            return ApiController().response_sucess(res, params, "/cleaning/update")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, params, "/cleaning/update")

    @http.route(['/cleaning/delete'], type="json", auth="public", method="GET", scrf=False)
    def delete(self, ids, **kwargs):
        """
        REST API for delete cleaning base on ids

        Parameters:
        -----------
        ids: list (id cleaning)
        """
        request.env.cr.savepoint()
        params = copy.deepcopy(kwargs)
        params.update({'ids':ids})
        try:
            for id in ids:
                ApiController().validate_base_on_id("cleaning", "Cleaning", id)
            res = request.env['cleaning'].sudo().search([('id', 'in', ids)]).unlink()
            request.env.cr.commit()                

            return ApiController().response_sucess(res, params, "/cleaning/delete")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, params, "/cleaning/delete")