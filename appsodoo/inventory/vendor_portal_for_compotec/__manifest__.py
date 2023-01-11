# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Vendor Channel',
    'version': '1.0',
    'author': 'Pilarmedia Indonesia',
    'category': 'Compotec',
    'summary': """ Adjustment for Compotec """,
    'website': 'https://solog.id/',
    'description': """
    this module for customize vendor channel base on bussiness on Compotec International.
    """,
    'maintainer': 'Pilarmedia',
    'license': 'OPL-1',
    'support':'info@solog.id',
    'depends': [
        'base', 
        'stock', 
        'account',
        'purchase', 
        'crm', 
        'sale',
        'product',  
        'purchase_request', 
        'purchase_requisition',
        'stock_picking_auto_create_lot'
    ],
    'data': [
        "security/ir.model.access.csv",
        "views/inherit_template_css.xml",
        "views/inherit_res_partner.xml",
        "views/inherit_account_move.xml",
        "views/inherit_product.xml",
        "views/inherit_perm_purchase.xml",
        "views/inherit_purchase_request.xml",
        "views/inherit_purchase_request_line.xml",
        "views/inherit_purchase_order.xml",
        "views/inherit_purchase_requisition.xml",
        "views/item_catalog.xml",
        "views/tender.xml",
        "views/inherited_res_config_setting.xml",
        "views/inherit_stock_picking_type.xml",
        "views/report_vendor_pricelist_view.xml",
        "data/ir_sequence.xml"
    ],
    # 'demo': ['data/sale_order_demo.xml'],
    # report
    # 'qweb': ['static/src/xml/qty_at_date.xml'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
