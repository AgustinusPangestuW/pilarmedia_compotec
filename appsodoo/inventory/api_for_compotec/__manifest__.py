# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'API for Compotec',
    'version': '1.0',
    'author': 'Pilarmedia Indonesia',
    'category': 'Compotec',
    'summary': """ 
        1. Change status picking to (in Transit / Delivered)
        2. Add data to form `Transit Log` base on Stock Picking.
        3. CRUD cleaning, Wrapping, Checkseet Borongan, Peel Diss Assy
    """,
    'website': 'https://solog.id/',
    'maintainer': 'Pilarmedia',
    'license': 'OPL-1',
    'support':'info@solog.id',
    'depends': ['base', 'stock', 'pilarmedia_for_compotec'],
    'data': [
        "security/ir.model.access.csv",
        "views/inherit_inventory_overview.xml",
        "views/inherit_res_users_view.xml",
        "views/transit_log_view.xml",
        "views/stock_picking_type_for_transit_view.xml",
        "views/api_log_view.xml",
        "data/ir_sequence_api_log.xml"
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
