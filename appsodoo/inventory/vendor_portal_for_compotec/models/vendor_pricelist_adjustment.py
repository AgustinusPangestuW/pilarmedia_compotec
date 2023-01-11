from odoo import models, fields, api
from datetime import datetime

class VendorPricelistAdjustment(models.Model):
    _name = 'vendor.pricelist.adjustment'
    _description = "Vendor Pricelist Adjustment"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    READONLY_STATES = {
        'post': [('readonly', True)],
        'approve': [('readonly', True)],
        'reject': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    # name = fields.Char(string='Name', readoly=1)
    partner_id = fields.Many2one('res.partner', string='Vendor', required=True, states=READONLY_STATES)
    posting_date = fields.Date(string='Posting Date', readonly=1)
    confirm_date = fields.Date(string='Confirm Date', readonly=1, help="confirmation date base on (approve / reject) action")
    pricelist_id = fields.Many2one('product.supplierinfo', string='Vendor Pricelist', readonly=1)
    product_id = fields.Many2one('product.product', string='Product', states=READONLY_STATES)
    price = fields.Float(string='Price', states=READONLY_STATES)
    currency_id = fields.Many2one('res.currency', string='Currency', required=1, states=READONLY_STATES,default=lambda self:self.env.company.currency_id)
    qty = fields.Float(string='Qty', states=READONLY_STATES)
    uom = fields.Many2one('uom.uom', string='UOM', required=1, readonly=1)
    product_name = fields.Char(string='Product name', states=READONLY_STATES)
    product_code = fields.Char(string='Product code', states=READONLY_STATES)
    state = fields.Selection([
        ("draft","Draft"),
        ("post","Post"),
        ("approve","Approve"),
        ("reject","Reject"),
        ("cancel","Cancel")
    ], string='State', default="draft", tracking=1)

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'
            
    def action_post(self):
        for rec in self:
            rec.state = 'post'
            rec.posting_date = fields.Date.today()

    def action_approve(self):
        for rec in self:
            rec.state = 'approve'
            rec.confirm_date = fields.Date.today()
            self.process_vendor_pricelist()

    def action_reject(self):
        for rec in self:
            rec.state = 'reject'
            rec.confirm_date = fields.Date.today()

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'

    @api.onchange('product_id')
    def fetch_from_vendor_pricelist(self):
        for rec in self:
            seller = None
            if rec.partner_id and rec.product_id:
                seller = rec.product_id._select_seller(
                    partner_id=rec.partner_id,
                    quantity=rec.qty,
                    date=datetime.today().date(),
                    uom_id=rec.uom
                )

            rec.update({'uom': rec.product_id.product_tmpl_id.uom_po_id})

            if seller:
                rec.update({
                    'qty': seller.min_qty,
                    'product_name': seller.product_name,
                    'product_code': seller.product_code,
                    'price': seller.price,
                    'pricelist_id': seller.id
                })

    def process_vendor_pricelist(self):
        for rec in self:
            partner = rec.partner_id if not rec.partner_id.parent_id else rec.partner_id.parent_id
            seller = None
            if rec.partner_id and rec.product_id:
                seller = rec.product_id._select_seller(
                    partner_id=rec.partner_id,
                    quantity=rec.qty,
                    date=datetime.today().date(),
                    uom_id=rec.uom
                )

            # Convert the price in the right currency.
            company_id = self.env.user.company_id
            currency = partner.property_purchase_currency_id or self.env.company.currency_id
            price = self.currency_id._convert(rec.price, currency, company_id, fields.Date.today(), round=False)
            # Compute the price for the template's UoM, because the supplier's UoM is related to that UoM.
            if rec.product_id.product_tmpl_id.uom_po_id != rec.uom:
                default_uom = rec.product_id.product_tmpl_id.uom_po_id
                price = rec.uom._compute_price(price, default_uom)

            # Update
            if seller:
                seller.update({'price': price})
                if rec.product_name: seller.update({'product_name': rec.product_name})
                if rec.product_code: seller.update({'product_code': rec.product_code})
                
            # insert new vendor pricelist
            else:
                supplierinfo = {
                    'name': partner.id,
                    'sequence': max(rec.product_id.seller_ids.mapped('sequence')) + 1 if rec.product_id.seller_ids else 1,
                    'min_qty': rec.qty,
                    'price': price,
                    'currency_id': currency.id,
                    'delay': 0,
                    'product_name': rec.product_name or "",
                    'product_code': rec.product_code or ""
                }
                rec.product_id.write({
                    'seller_ids': [(0, 0, supplierinfo)],
                })