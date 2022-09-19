# -*- coding: utf-8 -*-
{
    'name' : 'Transfer for Sub Contracting Compotec',
    'version' : '1.0',
    'author':'Pilarmedia',
    'category': 'Warehouse',
    'maintainer': 'Pilarmedia',
    'summary': """Two step transfer for sub contracting. """,

    'website': 'https://solog.id/',
    'license': 'OPL-1',
    'support':'info@solog.id',
    'depends' : ['stock'],
    'data': [

        'security/ir.model.access.csv',
        'views/inherit_stock_picking_type.xml',
        'views/pilar_pricelist.xml',
        'views/pilar_vehicle.xml',
        'views/inherit_mrp_production.xml',

    ],
    
    'installable': True,
    'application': True,
    'auto_install': False,

    'images': ['static/description/main_screen.png'],

}
