# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Change Status Picking',
    'version': '1.0',
    'author': 'Pilarmedia Indonesia',
    'category': 'Compotec',
    'summary': """ Change status picking to (in Transit / Delivered)""",
    'website': 'https://solog.id/',
    'description': """
    Change status picking (in Transit / Delivered) based on method API 
    """,
    'maintainer': 'Pilarmedia',
    'license': 'OPL-1',
    'support':'info@solog.id',
    'depends': ['base', 'stock'],
    'data': [
        "security/ir.model.access.csv",
        "views/inherit_inventory_overview.xml",
        "views/inherit_res_users_view.xml",
        "views/transit_log_view.xml",
        "views/stock_picking_type_for_transit_view.xml"
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
