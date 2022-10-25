import json, copy
from odoo import http, _
from odoo.http import request
from .api import ApiController
from odoo.exceptions import ValidationError

class ConfigCompotecApi(http.Controller):
    @http.route(['/getemployeecompotec/'], type="json", auth="public", method=['GET'])
    def getEmployeeCompotec(self, **kwargs):
        """
        REST API for get employee_custom

        parameters:
        -----------
        kwargs['search'] : list of list
            ex: [['vendor', 'in', ['HBR']]]
            format: [["fields", "operator", "parameter"]]

        returns:
        --------
        employees : list of dict
        """
        try:
            employees = [{
                "name": i.name,
                "position": i.position,
                "vendor_id": i.vendor.id,
                "vendor": i.vendor.name
            } for i in request.env['employee.custom'].sudo().search((kwargs.get('search') or []))]
            return ApiController.response_sucess(ApiController, {'employees': employees}, kwargs, "/getemployeecompotec/")
        except Exception as e:
            return ApiController.response_failed(ApiController, e, kwargs, "/getemployeecompotec/") 

    @http.route(['/getlot/'], type="json", auth="public", method=['GET'])
    def getLot(self, **kwargs):
        """
        REST API for get Lot
        """
        try:            
            lots, max = [], 0
            request.env.cr.execute(""" SELECT MAX(name::integer) as max_name FROM lot """)
            res = request.env.cr.dictfetchone()

            max = res['max_name'] if 'max_name' in res else 0 
            lots = [{
                'name': int(i.name),
                'description': i.description
            } for i in request.env['lot'].sudo().search([])]

            return ApiController.response_sucess(ApiController, {'lots': lots, "max": max}, kwargs, "/getlot/")
        except Exception as e:
            return ApiController.response_failed(ApiController, e, kwargs, "/getlot/")

    @http.route(['/getshift/'], type="json", auth="public", method=["GET"])
    def getShift(self, **kwargs):
        """
        REST API for get Shift
        """
        try:
            shifts = request.env['shift'].sudo().search(kwargs.get('search') or [])

            shifts = [{
                'active': i.active,
                'shift_id': i.id,
                'shift': i.name,
                'description': i.description or '',
                'working_times': [{
                    'sequence': wt.sequence,
                    'working_time_id': wt.working_time.id,
                    'working_time': wt.working_time.name
                } for wt in i.shift_line]
            } for i in shifts]

            return ApiController.response_sucess(ApiController, {"shifts": shifts}, kwargs, "/getshift/")
        except Exception as e:
            return ApiController.response_failed(ApiController, e, kwargs, "/getshift/")