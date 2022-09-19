# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Pilarmedia for Compotec',
    'version': '1.0',
    'author': 'Pilarmedia Indonesia',
    'category': 'compotec',
    'summary': 'Custom for Compotec',
    'description': "Custom for Compotec",
    'depends': ['base'],
    'data': [
        # "views/test_crud_menu.xml",
        # "views/test_crud_views.xml"
        "security/ir.model.access.csv",
        "views/shift_view.xml",
        "views/shift_deadline_view.xml",
        "views/working_time_view.xml",
        "views/shift_view.xml",
        "views/wrapping.xml",
        "views/wrapping_line.xml",
        "views/wrapping_working_time_line.xml",
        "views/sorting.xml",
        "views/sorting_line_view.xml",
        "data/ir_sequence_wrapping.xml",
        "data/ir_sequence_sorting.xml"
        # 'security/sale_stock_security.xml'
    ],
    # 'demo': ['data/sale_order_demo.xml'],
    # report
    # 'qweb': ['static/src/xml/qty_at_date.xml'],
    'installable': True,
    'auto_install': False,
    # flag sebagai applikasi
    # 'application': True,
    'license': 'LGPL-3',
}
