from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
import json
import datetime

class Portal(CustomerPortal):

	
	def _prepare_portal_layout_values(self):
		values = super(Portal, self)._prepare_portal_layout_values()
		partner = request.env.user.partner_id

		rfqs = request.env['rfq.order'].sudo().search([('state', 'in', ['publish', 'done', 'cancel'])])
		order_sum = 0
		for rfq in rfqs:
			if partner.id in rfq.partner_ids.ids:
				order_sum += 1

		values.update({
			'order_count1': order_sum,
		})
		return values

	
	
	@http.route('/my/submit_rfq', type='http', auth="user", website=True)
	def submit_rfq(self, **kw):
		

		
		partner = request.env.user.partner_id
		request_id = request.env['rfq.order.line'].sudo().create({
			'partner_id': partner.id,
			'vendor_estimated_date': datetime.datetime.strptime(kw['date'], "%Y-%m-%d").date(),
			'note': kw['note'],
			'order_id': int(kw['id']),
			'state': 'draft',
			})
		
		price_units = kw['price_units'].split(',')
		for item in price_units:
			if item:
				item = item.split(":")
				request.env['rfq.order.line.sub'].sudo().create({
				'product_id': int(item[0]),
				'vendor_qty': float(item[1]),
				'vendor_price': int(item[2]),
				'request_id': request_id.id,
				})
		
		
		
		return json.dumps({})


	@http.route(['/my/rfqlist'], type='http', auth="user", website=True)
	def rfqlist(self, **kw):
		partner = request.env.user.partner_id
		
		vendor_state = 'all' ##FILTER
		if 'vendor_state' in kw:
			vendor_state = kw['vendor_state']
			
		rfqs = request.env['rfq.order'].sudo().search([('state', 'in', ['publish', 'done', 'cancel'])])
		rfq_to_show = []
		if vendor_state == 'all':
			for rfq in rfqs:
				if partner.id in rfq.partner_ids.ids:
					rfq_to_show.append(rfq)
					
		if vendor_state == 'apply':
			for rfq in rfqs:
				for recieved in rfq.quote_ids: 
					if partner.id == recieved.partner_id.id:
						rfq_to_show.append(rfq)
						
		if vendor_state == 'open':
			for rfq in rfqs:
				if partner.id in rfq.partner_ids.ids:
					applied = False
					for recieved in rfq.quote_ids: 
						if partner.id == recieved.partner_id.id:
							applied = True
					if not applied and rfq.state == 'publish':
						rfq_to_show.append(rfq)
						
		if vendor_state == 'accept':
			for rfq in rfqs:
				for recieved in rfq.quote_ids:
					if recieved.state == 'accept': 
						if partner.id == recieved.partner_id.id:
							rfq_to_show.append(rfq)
						
						
		if vendor_state == 'complete':
			for rfq in rfqs:
				if partner.id in rfq.partner_ids.ids:
					if rfq.state == 'done':
						rfq_to_show.append(rfq)
						
			
				
		values = self._prepare_portal_layout_values()
		values.update({
			'rfqdata': rfq_to_show,
			'rfq_available': True if rfq_to_show else False,
			'select_key': vendor_state,
		})
		return request.render("vendor_rfq.rfq_list", values)



	
	@http.route('/my/rfqform/<int:rfqid>', type='http', auth="user", website=True)
	def rfqform(self, rfqid, **kw):
		partner = request.env.user.partner_id
		rfq = request.env['rfq.order'].sudo().browse(rfqid)
		rfq_lines = request.env['rfq.order.line'].sudo().search([('order_id', '=', rfq.id)])
		submitted = 0
		accepted = 0
		applied_details = False
		for item in rfq_lines:
			if item.partner_id.id == partner.id:
				submitted = 1
				applied_details = item
			if item.partner_id.id == partner.id and item.state == 'accept':
				accepted = 1
				applied_details = item
			
		uoms = request.env['uom.uom'].sudo().search([])
				
		values = self._prepare_portal_layout_values()
		values.update({
			'rfq': rfq,
			'products': rfq.product_ids,
			'uoms': uoms,
			'submitted': submitted,
			'accepted': accepted,
			'applied_details': applied_details,
		})
		return request.render("vendor_rfq.rfq_form", values)
	
	
	
	
	