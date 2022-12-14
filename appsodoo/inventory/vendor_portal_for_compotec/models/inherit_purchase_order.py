from odoo import models, fields, api, _
from odoo.exceptions import UserError
from itertools import groupby
from datetime import date, datetime

class InheritPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    base_on_purchase_requests = fields.Text('Base on Purchase Requests', 
        compute="get_purchase_requests", store=True)
    posting_date = fields.Date(string='Posting Date', default=date.today())
    is_editable = fields.Boolean(string='Is Editable?', readonly=1)
    document_date = fields.Date(string='Document Date')
    delivery_date = fields.Date(string='Delivery Date', readonly=True)
    with_confirm_date = fields.Boolean(string='with confirm date?', store=1, compute="get_from_res_partner")
    payment_method = fields.Selection([("cash","Cash"),("card","Card")], string='Payment Method')
    pr_state = fields.Selection([
            ("no_receipt","No Receipt"),
            ("partial","Receipt Partially"), 
            ('full', 'Receipt Finished')
        ], string='Receipt Status', compute="_compute_pr_state", store=True, default="no_receipt")
    custom_css = fields.Html(string='CSS', sanitize=False, compute='_compute_css', store=False)

    @api.depends('state')
    def _compute_css(self):
        for rec in self:
            if rec.state in ['purchase', 'done', 'lock']:
                rec.custom_css = '<style>.o_form_button_edit {display: none !important;}</style>'
            else:
                rec.custom_css = False

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

    def _create_picking(self):
        res = super()._create_picking()
        
        for rec in self:
            stock_picking_ids = self.env['stock.picking'].sudo().search([('origin', '=', rec.display_name)])
            for sp in stock_picking_ids:
                sp.vendor_purchase = rec.partner_id.id

        return res

    @api.onchange('partner_id', 'order_line.product_id')
    def _set_supplier_item_code(self):
        for rec in self:
            for line in rec.order_line:
                if line.product_id and rec.partner_id:
                    for i in line.product_id.seller_ids:
                        if i.name.id == rec.partner_id.id:
                            line.supplier_item_code = i.product_code

    def _add_supplier_to_product(self):
        def get_avg_price_purchase(id_product:int, partner_id:int, date:str):
            self.env.cr.execute("""
                SELECT AVG(pol.product_qty * pol.price_unit) as avg_price
                FROM purchase_order_line pol
                LEFT JOIN purchase_order po ON  po.id = pol.order_id
                WHERE pol.product_id = %s AND po.partner_id = %s AND po.date_approve <= '%s'
            """ % (id_product, partner_id, date))
            return self.env.cr.fetchone()[0] or 0.0

        ICPSudo = self.env['ir.config_parameter'].sudo()
        vendor_pricelist_base_on = ICPSudo.get_param('vendor_pricelist_base_on')
        first_pricelist = False

        if vendor_pricelist_base_on in ('last_purchase', 'average_purchase'):
            for rec in self:
                for line in rec.order_line:
                    # Do not add a contact as a supplier
                    partner = rec.partner_id if not rec.partner_id.parent_id else rec.partner_id.parent_id
                    seller = line.product_id._select_seller(
                        partner_id=line.partner_id,
                        quantity=line.product_qty,
                        date=line.order_id.date_order and line.order_id.date_order.date(),
                        uom_id=line.product_uom
                    )

                    # if have pricelist for update new price 
                    if seller:
                        # Convert the price in the right currency.
                        currency = partner.property_purchase_currency_id or self.env.company.currency_id
                        price = self.currency_id._convert(line.price_unit, currency, line.company_id, line.date_order or fields.Date.today(), round=False)
                        # Compute the price for the template's UoM, because the supplier's UoM is related to that UoM.
                        if line.product_id.product_tmpl_id.uom_po_id != line.product_uom:
                            default_uom = line.product_id.product_tmpl_id.uom_po_id
                            price = line.product_uom._compute_price(price, default_uom)

                        if vendor_pricelist_base_on == "last_purchase":
                            seller.price = price
                        elif vendor_pricelist_base_on == "average_purchase":
                            seller.price = get_avg_price_purchase(
                                line.product_id.id, 
                                partner.id, 
                                datetime.today().date().strftime('%Y-%m-%d')
                            )
                    else:
                        first_pricelist = True
                                   
        if vendor_pricelist_base_on in ('', False, "standard") or first_pricelist:
            # STD ODOO with first purchase only
            return super()._add_supplier_to_product()


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
    catalog_price = fields.Float(string='Catalog Price', compute="_get_from_item_catalog")

    @api.onchange('product_id')
    def _set_supplier_item_code(self):
        for rec in self:
            if rec.product_id and rec.order_id.partner_id:
                for i in rec.product_id.seller_ids:
                    if i.name.id == rec.order_id.partner_id.id:
                        rec.supplier_item_code = i.product_code

    @api.depends('item_catalog')
    def _get_from_item_catalog(self):
        for rec in self:
            rec.catalog_price = rec.item_catalog.price if rec.item_catalog else 0

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