# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Approval PR & PO',
    'version': '1.0',
    'author': 'Pilarmedia Indonesia',
    'category': 'Compotec',
    'summary': """ Approval for Purchase Request and Purchase Order """,
    'website': 'https://solog.id/',
    'maintainer': 'Pilarmedia Indonesia',
    'license': 'OPL-1',
    'support':'info@solog.id',
    'depends': ['hr', 'purchase', 'purchase_request'],
    'data': [
        "security/ir.model.access.csv",
        "views/inherit_purchase_order.xml",
        "views/inherit_purchase_request.xml",
        # "views/inherit_res_config_settings.xml"
        "views/approval_setting.xml"
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
