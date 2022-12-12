from odoo import models, fields, api, _
from odoo.exceptions import UserError
from itertools import groupby
from datetime import date

class InheritPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    base_on_purchase_requests = fields.Text('Base on Purchase Requests', 
        compute="get_purchase_requests", store=True)
    posting_date = fields.Date(string='Posting Date', default=date.today())
    document_date = fields.Date(string='Document Date')
    delivery_date = fields.Date(string='Delivery Date')
    with_confirm_date = fields.Boolean(string='with confirm date?', store=1, compute="get_from_res_partner")

    @api.depends('partner_id', 'partner_id.with_confirm_date')
    def get_from_res_partner(self):
        for rec in self:
            rec.with_confirm_date = rec.partner_id.with_confirm_date if rec.partner_id else 0
    
    @api.depends('order_line')
    def get_purchase_requests(self):
        for rec in self:
            purchase_requests = []
            for line in rec.order_line:
                purchase_requests = [pr.request_id.name for pr in line.purchase_request_lines]

            purchase_requests = [k for k,_ in groupby(purchase_requests)]
            rec.base_on_purchase_requests = ",".join(purchase_requests) or ""


class INheritPurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    expense = fields.Selection([("opex","OPEX"),("capex","CAPEX")], string='Expense', compute='get_from_pr', store=True)
    remarks = fields.Text(string='Remarks')
    base_on_purchase_requests = fields.Text(string='PR Code', compute="get_from_pr", store=True)
    item_code = fields.Char(string='Item Code', compute="fetch_info_item")
    item_name = fields.Char(string='Item Name', compute="fetch_info_item")
    supplier_item_code = fields.Char(string='Supplier Item Code', compute="fetch_info_item")

    @api.depends('purchase_request_lines')
    def get_from_pr(self):
        for rec in self:
            purchase_requests = [pr.request_id.name for pr in rec.purchase_request_lines]
            purchase_requests = [k for k,_ in groupby(purchase_requests)]
            rec.base_on_purchase_requests = ",".join(purchase_requests) or ""

            if not rec.expense:
                expense = ""
                for pr in rec.purchase_request_lines:
                    expense = pr.expense
                rec.expense = expense

    @api.depends('product_id')
    def fetch_info_item(self):
        for rec in self:
            rec.item_code = rec.product_id.default_code if rec.product_id else ""
            rec.item_name = rec.product_id.name if rec.product_id else ""
            rec.supplier_item_code = rec.product_id.supplier_item_code if rec.product_id else ""