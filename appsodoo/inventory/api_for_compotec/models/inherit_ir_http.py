from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        result = super(IrHttp, self).session_info()
        if 'uid' in result:
            warehouses = request.env['res.users'].sudo().search([('id', '=', result['uid'])]).warehouses
            result.update({'warehouses':  [{w.id:w.name} for w in warehouses]})
        return result