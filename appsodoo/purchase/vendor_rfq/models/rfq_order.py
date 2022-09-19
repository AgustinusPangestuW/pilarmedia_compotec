from odoo import api, fields, tools, models, _
from odoo.exceptions import UserError, ValidationError


class RfqOrder(models.Model):
	
	_name = 'rfq.order'
	
	_description = 'Vendor RFQs'

	def show_rfq_purchase_orders(self):
		ids = self.env['purchase.order'].sudo().search([('partner_ref', '=', self.name)]).ids
		return {
			'type': 'ir.actions.act_window',
			'name': 'Purchase Order',
			'view_mode': 'tree,form',
			'res_model': 'purchase.order',
			'domain': [('id', 'in', ids)],
		}

	def _compute_rfq_purchase_count(self):
		for record in self:
			count = self.env['purchase.order'].sudo().search([('partner_ref', '=', record.name)]).ids
			record.rfq_purchase_count = len(count)




	def check_applied(self):
		partner = self.env['res.users'].browse(self._context['uid']).partner_id
		for item in self:
			item.partner_status = 'Not Applied'
			for quote in item.quote_ids:
				if partner.id == quote.partner_id.id:
					item.partner_status = 'Applied'
					if quote.state == 'accept':
						item.partner_status = 'Accepted'
					break
		
		
		
		
	name = fields.Char("Name")
	date = fields.Datetime(related="create_date", string="RFQ Date", readonly=True)
	estimated_delivery = fields.Date("Expected Estimated Date", required=True)
	desc = fields.Text("Short Description")
	partner_ids = fields.Many2many("res.partner", string="Vendors", required=True)
	product_ids = fields.One2many('rfq.order.product', 'order_id', "Products",)
	quote_ids = fields.One2many('rfq.order.line', 'order_id', "Received Quotations")
	rfq_purchase_count = fields.Integer(compute='_compute_rfq_purchase_count')

	state = fields.Selection([('draft', 'Draft'), ('publish', 'Open'), ('done', 'Closed'), ('purchase', 'Done'), ('cancel', 'Canceled')], default="draft")
	
	partner_status = fields.Char(compute='check_applied')
	

	@api.model
	def create(self, vals):
		vals['name'] = self.env['ir.sequence'].next_by_code('rfq.order') or 'New'
		return super(RfqOrder, self).create(vals)



	def action_publish(self):
		return {	 
				 'type': 'ir.actions.act_window',
				 'name': 'Publish RFQ and Notify',
				 'res_model': 'publish.email',
				 'view_type': 'form', 	
				 'view_mode': 'form',
				 'target': 'new',
				}
			
		
	def action_cancel(self):
		for item in self:
			item.state = 'cancel'
			


	def action_create_quote(self):
		
		partner = False
		quote = False
		product_uom = {}
		
		
		for item in self.quote_ids:
			if item.state == 'accept':
				partner = item.partner_id
				quote = item
				
				
		for product in self.product_ids:
			for item in quote.sub_ids:
				if product.product_id.id == item.product_id.id:
					product_uom[product.product_id.id] = product.uom.id
					
					
		
		purchase_vals = {
			'partner_id': partner.id,
			'partner_ref': self.name,
			}
		
		purchase_id = self.env['purchase.order'].create(purchase_vals)
		
		for item in quote.sub_ids:
			purchase_line_vals = {
			'product_id': item.product_id.id,
			'product_qty': item.vendor_qty,
			'price_unit': item.vendor_price,
			'order_id': purchase_id.id,
			#'partner_ref': self.name,
			'name': self.name,
			'date_planned': quote.vendor_estimated_date,
			'product_uom': product_uom[item.product_id.id],
			}
		
			purchase_line_id = self.env['purchase.order.line'].create(purchase_line_vals)
		
		
		
		
		self.state = 'purchase'
		
		return True
		
		
		
		

class RfqOrderProduct(models.Model):
	
	_name = 'rfq.order.product'
	
	_description = 'Vendor RFQs Products'
	
	
	product_id = fields.Many2one('product.product', "Product", required=True)
	qty = fields.Float("Quantity", required=True)
	uom = fields.Many2one('uom.uom', "Unit of Measure", required=True)
	
	order_id = fields.Many2one('rfq.order', 'Order')
	
	
	
	
class RfqOrderLine(models.Model):
	
	_name = 'rfq.order.line'
	
	_description = 'Vendor RFQs Lines'
	
	
	partner_id = fields.Many2one('res.partner', 'Vendor')
	vendor_estimated_date = fields.Date("Vendor Estimated Date")
	note = fields.Text("Note")
	state = fields.Selection([('draft', "Draft"), ('accept', 'Accepted and Mail Sent')], default="draft")
	order_id = fields.Many2one('rfq.order', 'Order')
	
	sub_ids = fields.One2many('rfq.order.line.sub', 'request_id', "Quotation Lines")
	
	
	def action_accept_quotation(self):
		return {	 
				 'type': 'ir.actions.act_window',
				 'name': 'Send Quotation Acceptance Email',
				 'res_model': 'accept.email',
				 'view_type': 'form', 	
				 'view_mode': 'form',
				 'target': 'new',
				}
		


	
class RfqOrderSubLine(models.Model):
	
	_name = 'rfq.order.line.sub'
	
	_description = 'Vendor RFQs Sub Lines'
	
	
	product_id = fields.Many2one('product.product', "Product", required=True)
	vendor_qty = fields.Float("Vendor Qty")
	vendor_price = fields.Float("Vendor Price")
	
	request_id = fields.Many2one('rfq.order.line', 'Order')
	
	
	
class accept_email(models.TransientModel):
	
	_name = 'accept.email'
	
	partner_id = fields.Many2one('res.partner', "Vendor", readonly=True)
	subject = fields.Char("Subject")
	body = fields.Html("Email body")
	
	
	@api.model
	def default_get(self, default_fields):
		request = self.env['rfq.order.line'].browse(self._context['active_id'])
		res = super(accept_email, self).default_get(default_fields)
		res['partner_id'] = request.partner_id.id
		
		return res
	
	
	
	def send(self):
		
		template = self.env.ref('vendor_rfq.accept_email', raise_if_not_found=False)
		template_values = {
            'email_to': self.partner_id.email,
            'email_cc': False,
            'auto_delete': False,
            'partner_to': False,
            'scheduled_date': False,
            'subject': self.subject,
            'body_html': self.body,
        }
		template.write(template_values)
		template.send_mail(self._uid, force_send=True, raise_exception=False)
		
		
		request = self.env['rfq.order.line'].browse(self._context['active_id'])
		request.state = 'accept'
		request.order_id.state = 'done'
		
		return {'type': 'ir.actions.act_window_close'}
		
	
	
	
class publish_email(models.TransientModel):
	
	_name = 'publish.email'
	
	subject = fields.Char("Subject")
	body = fields.Html("Email body")
	
	
	
	def send(self):
		
		template = self.env.ref('vendor_rfq.publish_email', raise_if_not_found=False)
		order = self.env['rfq.order'].browse(self._context['active_id'])
		emails = ''
		for item in order.partner_ids:
			if item.email:
				emails = item.email + ","
			
			 
		template_values = {
            'email_to': emails,
            'email_cc': False,
            'auto_delete': False,
            'partner_to': False,
            'scheduled_date': False,
            'subject': self.subject,
            'body_html': self.body,
        }
		template.write(template_values)
		template.send_mail(self._uid, force_send=True, raise_exception=False)
		
		
		order.state = 'publish'
		
		return {'type': 'ir.actions.act_window_close'}
		
	
	
	
	
	
	
	
	
	
