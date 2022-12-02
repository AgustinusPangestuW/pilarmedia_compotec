# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Pilarmedia for Compotec',
    'version': '1.0',
    'author': 'Pilarmedia Indonesia',
    'category': 'Compotec',
    'summary': """ new Form Cleaning, Wrapping, Peel Diss Assy and Wholesale Job (Checksheet Borongan). """,
    'website': 'https://solog.id/',
    'description': """
    New Form : \n
    1. Cleaning. \n
    2. Wrapping. \n
    3. Peel Diss assy. \n
    4. Wholesale Job (Checksheet Borongan). \n
    """,
    'maintainer': 'Pilarmedia',
    'license': 'OPL-1',
    'support':'info@solog.id',
    'depends': ['base', 'stock', 'pilar_subcont_transfer'],
    'data': [
        "security/ir.model.access.csv",
        "views/cleaning_view.xml",
        "views/wrapping.xml",
        "views/shift_view.xml",
        "views/shift_deadline_view.xml",
        "views/working_time_view.xml",
        "views/shift_view.xml",
        "views/wrapping_line.xml",
        "views/wrapping_working_time_line.xml",
        "views/sorting.xml",
        "views/sorting_line_view.xml",
        "views/master_ng_view.xml",
        "views/peel_diss_assy_view.xml",
        "views/peel_diss_assy_line_view.xml",
        "views/peel_diss_assy_component_line_view.xml",
        "views/peel_diss_assy_fg_line_view.xml",
        "views/wholesale_job_view.xml",
        "views/wholesale_job_line_view.xml",
        "views/daily_wholesale_job_view.xml",
        "views/lot_view.xml",
        "views/employee_custom_view.xml",
        "views/wholesale_job_view_report.xml",
        "views/inherit_stock_picking_view.xml",
        "views/inherit_stock_warehouse_view.xml",
        "views/inherit_res_users_view.xml",
        "views/job_view.xml",
        "views/pricelist_subcon_base_on_stock_move.xml",
        "views/inherit_product_template_view.xml",
        "views/generator_mo_or_sp_view.xml",
        "views/generator_mosp_line_view.xml",
        "views/required_items.xml",
        "views/generate_mo_or_sp_bomlines.xml",
        "views/inherit_stock_inventory_view.xml",
        "wizard/wholesale_job_report_wizz.xml",
        "data/ir_sequence_wrapping.xml",
        "data/ir_sequence_sorting.xml",
        "data/ir_sequence_wholesale_job.xml",
        "data/ir_sequence_peel_diss_assy.xml",
        "data/ir_sequence_cleaning.xml",
        "data/ir_sequence_generator_mo_or_sp.xml",
        "report/surat_jalan.xml"
    ],
    # 'demo': ['data/sale_order_demo.xml'],
    # report
    # 'qweb': ['static/src/xml/qty_at_date.xml'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
