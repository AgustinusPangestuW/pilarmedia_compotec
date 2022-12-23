from odoo import models, fields, api, _
from odoo.exceptions import UserError
from itertools import groupby
from datetime import date

class InheritPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    base_on_purchase_requests = fields.Text('Base on Purchase Requests', 
        compute="get_purchase_requests", store=True)
    posting_date = fields.Date(string='Posting Date', default=date.today())
    is_editable = fields.Boolean(string='Is Editable?', readonly=1)
    document_date = fields.Date(string='Document Date')
    delivery_date = fields.Date(string='Delivery Date')
    with_confirm_date = fields.Boolean(string='with confirm date?', store=1, compute="get_from_res_partner")
    payment_method = fields.Selection([("cash","Cash"),("card","Card")], string='Payment Method')
    pr_state = fields.Selection([
            ("no_receipt","No Receipt"),
            ("partial","Receipt Partially"), 
            ('full', 'Receipt Finished')
        ], string='Receipt Status', compute="_compute_pr_state", store=True, default="no_receipt")

    @api.depends('order_line', 'order_line.qty_received')
    def _compute_pr_state(self):
        for rec in self:
            for i in rec.order_line:
                qty_need_receipt = i.qty_received - i.product_qty
                if qty_need_receipt < 0 and abs(qty_need_receipt) != i.product_qty:
                    rec.pr_state = "partial"
                    break
                elif qty_need_receipt >= 0:
                    rec.pr_state = "full"
                else:
                    rec.pr_state = "no_receipt"

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

    def create_receipt_base_on_po(self, ret_raise=False):
        receipt_created = []
        for rec in self:
            if rec.state == "purchase" and not rec.picking_count:
                rec.make_receipt()
                sp = self.env['stock.picking'].sudo().search([('origin', '=', rec.display_name)])
                if sp:
                    receipt_created.append(str(sp[0].display_name))

        if ret_raise:
            type = ''
            if receipt_created:
                message = _("Sucessfull Create Stock picking at [%s]" % (", ".join(receipt_created))) 
                type = 'success'
            else:
                message = _("Sucessfull, nothing create receipt / Stock Picking. system will create stock picking at PO (state = 'Purchase Order' & don't have receipt) ") 
                type = 'primary'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message,
                    'type': type,
                    'sticky': True
                }
            }

    @api.onchange('partner_id')
    def _set_supplier_item_code(self):
        for rec in self:
            for line in rec.order_line:
                if line.product_id and rec.partner_id:
                    for i in line.product_id.seller_ids:
                        if i.name.id == rec.partner_id.id:
                            line.supplier_item_code = i.product_code


class INheritPurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    expense = fields.Selection([("opex","OPEX"),("capex","CAPEX")], string='Expense', 
        compute='get_from_pr', store=True, readonly=False)
    is_editable = fields.Boolean(string='Is Editable?', readonly=1)
    remarks = fields.Text(string='Remarks')
    base_on_purchase_requests = fields.Text(string='PR Code', compute="get_from_pr", store=True)
    item_code = fields.Char(string='Item Code', compute="fetch_info_item")
    item_name = fields.Char(string='Item Name', compute="fetch_info_item")
    supplier_item_code = fields.Char(string='Supplier Item Code', compute="fetch_info_item", readonly=False, store=True)
    item_catalog = fields.Many2one('item.catalog', string='Item Catalog')

    @api.onchange('product_id')
    def _set_supplier_item_code(self):
        for rec in self:
            if rec.product_id and rec.order_id.partner_id:
                for i in rec.product_id.seller_ids:
                    if i.name.id == rec.order_id.partner_id.id:
                        rec.supplier_item_code = i.product_code

    @api.onchange('item_catalog')
    def get_value_base_on_item_catalog(self):
        for rec in self:
            if rec.item_catalog:
                rec.price_unit = rec.item_catalog.price

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