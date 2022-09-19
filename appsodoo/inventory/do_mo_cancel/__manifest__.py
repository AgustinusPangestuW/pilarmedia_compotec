# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Cancel Manufacturing & Picking',
    'version' : '1.0',
    'author':'Craftsync Technologies',
    'category': 'Sales',
    'maintainer': 'Craftsync Technologies',
    'summary': """Enable Auto cancel like Manufacturing & Picking and work order, Inventory . This module it will allow you cancel sale,purchase,accounting,Inventory even if it already done. """,

    'website': 'https://www.craftsync.com/',
    'license': 'OPL-1',
    'support':'info@craftsync.com',
    'depends' : ['stock','mrp','account'],
    'data': [

        'security/security.xml',
        'views/view_manufacturing_order.xml',
        'views/stock_picking.xml',

    ],
    
    'installable': True,
    'application': True,
    'auto_install': False,
    'price': 14.99,
    'currency': 'EUR',

    'images': ['static/description/main_screen.png'],

}
