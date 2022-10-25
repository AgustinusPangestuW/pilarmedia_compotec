import json, copy
from odoo import http, _
from odoo.http import request
from .api import ApiController, RequestError


class APIBOM(http.Controller):    
    def mapping_values(self, bom:object):
        return [{
            "id": rec.id,
            "product_tmpl_id": rec.product_tmpl_id.id,
            "product_tmpl": rec.product_tmpl_id.name,
            "product_id": rec.product_id.id or None,
            "product": rec.product_id.name or "",
            "qty": rec.product_qty,
            "uom_id": rec.product_uom_id.id,
            "uom": rec.product_uom_id.name,
            "code": rec.code or "",
            "type": rec.type or None,
            "company": rec.company_id.name,
            "company_id": rec.company_id.id,
            "consumption": rec.consumption or None,
            "bom_line_ids": [{
                "component": c.product_id.name,
                "component_id": c.product_id.id,
                "qty": c.product_qty,
                "uom": c.product_uom_id.name,
                "uom_id": c.product_uom_id.id
            } for c in rec.bom_line_ids]
        } for rec in bom]

    @http.route(['/bom/get'], type="json", auth="public", method="GET", csrf=False)
    def get(self, **kwargs):
        """
        REST API GET for table `bom`

        parameters:
        -----------
        kwargs['search']: list of list
            ex: [['id', '=', '1']]
        """
        try:
            res = request.env['mrp.bom'].sudo().search(kwargs.get('search') or [])
            boms = self.mapping_values(res)
            return ApiController.response_sucess(ApiController, boms, kwargs, "/bom/get")
        except Exception as e:
            return ApiController.response_failed(ApiController, e, kwargs, "/bom/get")

    @http.route(['/bom/getbaseoncomponent'], type="json", auth="public", method="GET", csrf=False)
    def get_base_on_component(self, product_ids, **kwargs):
        """
        REST API GET for table `bom`

        parameters:
        -----------
        product_ids: list of int
            ex: [1,2,3]
        kwargs['search']: list of list
            ex: [['id', '=', 2]]
        """
        try:
            ids = [line.bom_id.id for line in request.env['mrp.bom.line'].sudo().search([('product_id', 'in', product_ids)])]
            searchs = (kwargs.get('search') or []) + [('id', 'in', ids)]
            res = request.env['mrp.bom'].sudo().search(searchs or [])
            boms = self.mapping_values(res)
            return ApiController.response_sucess(ApiController, boms, kwargs, "/bom/getbaseoncomponent/")
        except Exception as e:
            return ApiController.response_failed(ApiController, e, kwargs, "/bom/getbaseoncomponent/")
