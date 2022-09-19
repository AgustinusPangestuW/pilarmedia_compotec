# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Wrapping and Sorting',
    'version': '1.0',
    'author': 'Pilarmedia Indonesia',
    'category': 'Compotec',
    'summary': """ new Form Wrapping and Sorting """,
    'website': 'https://solog.id/',
    'description': "Custom Form Wrapping and Sorting for Compotec",
    'maintainer': 'Pilarmedia',
    'license': 'OPL-1',
    'support':'info@solog.id',
    'depends': ['base', 'stock'],
    'data': [
        "security/ir.model.access.csv",
        "views/wrapping.xml",
        "views/shift_view.xml",
        "views/shift_deadline_view.xml",
        "views/working_time_view.xml",
        "views/shift_view.xml",
        "views/wrapping_line.xml",
        "views/wrapping_working_time_line.xml",
        "views/sorting.xml",
        "views/sorting_line_view.xml",
        "data/ir_sequence_wrapping.xml",
        "data/ir_sequence_sorting.xml"
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
