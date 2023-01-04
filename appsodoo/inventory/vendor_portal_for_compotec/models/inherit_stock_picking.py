from odoo import models, fields, api, _
from odoo.exceptions import UserError

class InheritStockPicking(models.Model):
    _inherit = 'stock.picking'

    vendor_purchase = fields.Many2one('res.partner', string='Vendor Purchase', compute="get_vendor")

    @api.depends('origin')
    def get_vendor(self):
        for rec in self:
            rec.vendor_purchase = None
            if rec.origin:
                order_ids = self.env['purchase.order'].sudo().search([('name', '=', rec.origin)])
                for i in order_ids:
                    rec.vendor_purchase = i.partner_id.id

    def action_done(self):
        res = super().action_done()
        self.set_delivery_date()
        return res

    def set_delivery_date(self):
        for rec in self:
            if rec.origin and rec.vendor_purchase:
                order_ids = self.env['purchase.order'].sudo().search([('name', '=', rec.origin)])
                for i in order_ids:
                    if not i.delivery_date or (i.delivery_date and i.delivery_date <= rec.date_done.date()):
                        i.delivery_date = rec.date_done

    