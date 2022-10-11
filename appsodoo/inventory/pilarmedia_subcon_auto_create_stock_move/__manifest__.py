# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Pilarmedia',
    'version': '1.0',
    'author': 'Pilarmedia Indonesia',
    'category': 'Subcon',
    'summary': """ auto create Stock Picking when operation type is subcon """,
    'website': 'https://solog.id/',
    'description': """ auto create Stock Picking when operation type is subcon """,
    'maintainer': 'Pilarmedia',
    'license': 'OPL-1',
    'support':'info@solog.id',
    'depends': ['base', 'stock', 'pilar_subcont_transfer'],
    'data': [
        "views/inherit_stock_picking_view.xml",
        "views/inherit_stock_picking_type_view.xml"
    ],
    # 'demo': ['data/sale_order_demo.xml'],
    # report
    # 'qweb': ['static/src/xml/qty_at_date.xml'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
