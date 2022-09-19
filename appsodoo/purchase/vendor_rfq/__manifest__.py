{
  "name": "Vendor Portal",
  "summary": "Vendor Portal, request for quotation, vendor quotation, purchase order, rfq, rfq portal, rfq order, ",
  "category": "Website",
  "version": "12.0",
  "author": "Simple Apps",
  "website": "",
  "description": "Vendor Portal, request for quotation, vendor quotation",
  "depends": ['purchase', 'website_sale'],
  "data":  [
			'views/rfq_views.xml',
			'security/ir.model.access.csv',
			'views/rfq_templates.xml',
            ],
  "images": [
	'static/description/screen.png',
	],
  "application": True,
  "installable": True,
  "auto_install": False,
  "price":  39,
  "currency": "USD",
}
