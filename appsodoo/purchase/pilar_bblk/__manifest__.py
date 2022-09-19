# -*- coding: utf-8 -*-
{
    'name' : 'Modul BBLK',
    'version' : '1.0',
    'author':'Pilarmedia',
    'category': 'Warehouse',
    'maintainer': 'Pilarmedia',
    'summary': """Modul BBLK""",

    'website': 'https://solog.id/',
    'license': 'OPL-1',
    'support':'info@solog.id',
    'depends' : ['stock'],
    'data': [

        'security/security.xml',
        'security/ir.model.access.csv',
        'views/pilar_reagen.xml',
        'views/pilar_kategori.xml',
        'views/menu.xml',
        'views/sequence.xml',

    ],
    
    'installable': True,
    'application': True,
    'auto_install': False,

    'images': ['static/description/main_screen.png'],

}
