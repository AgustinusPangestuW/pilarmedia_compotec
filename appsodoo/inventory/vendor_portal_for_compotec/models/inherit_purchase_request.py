from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date

class InheritPurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    po_state = fields.Selection(
        selection=[
            ('no_po', 'Belum PO'),
            ('partial_po', 'PO Sebagian'),
            ('full_po', 'PO Selesai')
        ], default="no_po", string='PO Status', compute="set_po_state", store=True)
    state = fields.Selection(string='PR Status')
    purchase_count = fields.Integer(store=True)
    date_start = fields.Date(string="Posting Date")
    valid_until = fields.Date(string='Valid Until')
    document_date = fields.Date(string='Document Date')
    require_date = fields.Date(string='Require Date')

    @api.depends("line_ids", "line_ids.purchase_lines")
    def _compute_purchase_count(self):
        for rec in self:
            rec.purchase_count = len(rec.mapped("line_ids.purchase_lines.order_id"))

    @api.depends('line_ids', 'line_ids.pending_qty_to_receive', 'line_ids.qty_in_progress')
    def set_po_state(self):
        process_to_po = False
        full_po = True
        for rec in self:
            for l in rec.line_ids:
                if l.pending_qty_to_receive - l.qty_in_progress < l.product_qty:
                    process_to_po = True
                    if l.pending_qty_to_receive - l.qty_in_progress > 0:
                        full_po = False

            if process_to_po:
                if full_po: rec.po_state = "full_po"
                else: rec.po_state = "partial_po"
            else: rec.po_state = "no_po"

    def action_view_purchase_order_history(self):
        action = self.env.ref("purchase.purchase_rfq").read()[0]
        lines = self.mapped("line_ids.purchase_lines.order_id")
        action["domain"] = [("id", "in", lines.ids)]
        return action

    def create_po_base_on_pr(self):
        approved_ids = []
        for rec in self:
            if rec.state == "approved":
                approved_ids.append(rec.id)
        
        action = self.env.ref('purchase_request.action_purchase_request_line_make_purchase_order').read()[0]   
        action['context'] = dict(self.env.context)
        action['context']['active_ids'] = approved_ids
        return action

class InheritPurchaseOrderLine(models.Model):
    _inherit = 'purchase.request.line'

    expense = fields.Selection([("capex","CAPEX"),("opex","OPEX")], string='Expense', store=True)
    item_code = fields.Char(string='Item Code', compute="fetch_info_item")
    item_name = fields.Char(string='Item Name', compute="fetch_info_item")
    supplier_item_code = fields.Char(string='Supplier Item Code', compute="fetch_info_item")
    
    @api.depends('product_id')
    def fetch_info_item(self):
        for rec in self:
            rec.item_code = rec.product_id.default_code if rec.product_id else ""
            rec.item_name = rec.product_id.name if rec.product_id else ""
            rec.supplier_item_code = rec.product_id.supplier_item_code if rec.product_id else ""

    