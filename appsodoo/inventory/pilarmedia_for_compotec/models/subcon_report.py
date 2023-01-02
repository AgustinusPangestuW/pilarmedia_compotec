import logging

from odoo import models, fields, api
from .employee_custom import _get_domain_user

_logger = logging.getLogger(__name__)


class SubconReport(models.Model):
    _name = 'subcon.report'
    _description = 'Subcon Report'
    _rec_name = 'date'

    pricelist_subcon_id = fields.Many2one('pricelist.subcon.baseon.stockmove', string='Pricelist Subcon ID')
    pricelist_subcon_line_id = fields.Many2one('pricelist.subcon.baseon.stockmove.line', string='Pricelist Subcon Line ID')
    move_id = fields.Many2one('stock.move', string='Stock Move ID')
    picking_id = fields.Many2one('stock.picking', string='Stock Picking ID')
    date = fields.Date(string='Date')
    product_id = fields.Many2one('product.product', string='Product')
    service_id = fields.Many2one('product.product', string='Service')
    date_transfer = fields.Date(string='Date Transfer')
    name_service = fields.Char(string='Service name')
    customer = fields.Char(string='Customer')
    subcon = fields.Char(string='Subcon')
    subcon_dest = fields.Char(string='Subcon Destination')
    no_sj = fields.Char(string='No. Surat Jalan')
    qty = fields.Float(string='Qty')
    qty_component = fields.Float(string='Qty Component')
    price_service = fields.Float(string='Price Service')
    tot_price_service = fields.Float(string='Total Price Service')
    price_transport = fields.Float(string='Price Transport')
    tot_price_transport = fields.Float(string='Total Price Transport')
    total_price = fields.Float(string='Total Price')


    def init(self):
        self.env.cr.execute("""
        DROP FUNCTION IF EXISTS subcon_report(DATE, DATE, CHAR);
        CREATE OR REPLACE FUNCTION subcon_report(date_start DATE, date_end DATE, input_vendor CHAR)
        RETURNS VOID AS $BODY$ 
        DECLARE
            
            csr cursor for
            SELECT 
                ps.id as pricelist_subcon_id, 
                psl.id as pricelist_subcon_line_id,
                sm.id as move_id,
                sp.id as picking_id,
                sp.scheduled_date as date,
                sm.product_id as product_id,
                p_service.id as service_id,
                p_service_tmpl.name as name_service,
                sp.date_done as date_transfer,
                prod_tmpl.nama_alias as customer,
                src.name as subcon,
                dest.name as subcon_dest,
                sj.name as no_sj,
                ps.qty_component as qty_component,
                ps.qty_in_stock_move_line as qty,
                psl.price as price_service,
                psl.price_total as tot_price_service,
                0 as price_transport,
                0 as tot_price_transport,
                psl.price_total as total_price
            FROM pricelist_subcon_baseon_stockmove ps
            LEFT JOIN pricelist_subcon_baseon_stockmove_line psl ON psl.pricelist_subcon_id = ps.id
            LEFT JOIN stock_move sm ON sm.id = ps.move_id
            LEFT JOIN pilar_pricelist pp ON pp.id = psl.pricelist_id
            LEFT JOIN product_product prod ON prod.id = sm.product_id
            LEFT JOIN product_template prod_tmpl ON prod_tmpl.id = prod.product_tmpl_id
            LEFT JOIN product_product p_service ON p_service.id = pp.product_id
            LEFT JOIN product_template p_service_tmpl ON p_service_tmpl.id = p_service.product_tmpl_id
            LEFT JOIN stock_picking sp ON sp.id = sm.picking_id
            LEFT JOIN stock_picking sj ON sp.surat_jalan_id = sj.id
            LEFT JOIN res_partner src ON src.id = sp.vendor
            LEFT JOIN res_partner dest ON dest.id = sp.vendor_dest_loc_subcon or dest.id = sp.vendor_dest_loc
            WHERE 
                (ps.invoice_created = false or ps.invoice_created is null) AND 
                sp.scheduled_date BETWEEN date_start AND date_end AND
                input_vendor in ('', CAST(src.name AS CHAR), CAST(dest.name AS CHAR))
                
            UNION

            SELECT 
                ps.id as pricelist_subcon_id, 
                null as pricelist_subcon_line_id,
                sm.id as move_id,
                sp.id as picking_id,
                sp.scheduled_date as date,
                sm.product_id as product_id,
                p_service.id as service_id,
                p_service_tmpl.name as name_service,
                sp.date_done as date_transfer,
                prod_tmpl.nama_alias as customer,
                src.name as subcon,
                dest.name as subcon_dest,
                sj.name as no_sj,
                ps.qty_component as qty_component,
                ps.qty_in_stock_move_line as qty,
                0 as price_service,
                0 as tot_price_service,
                pt.price as price_transport,
                (pt.price * NULLIF((ps.qty_in_stock_move_line * ps.qty_component), 1)) as tot_price_transport,
                (pt.price * NULLIF((ps.qty_in_stock_move_line * ps.qty_component), 1)) as total_price
            FROM pricelist_subcon_baseon_stockmove ps
            LEFT JOIN stock_move sm ON sm.id = ps.move_id
            LEFT JOIN stock_picking sp ON sp.id = sm.picking_id
            LEFT JOIN pilar_pricelist pt ON pt.id = sp.pricelist_id
            LEFT JOIN pilar_pricelist pp ON pp.id = sp.pricelist_id
            LEFT JOIN product_product prod ON prod.id = sm.product_id
            LEFT JOIN product_template prod_tmpl ON prod_tmpl.id = prod.product_tmpl_id
            LEFT JOIN product_product p_service ON p_service.id = pp.product_id
            LEFT JOIN product_template p_service_tmpl ON p_service_tmpl.id = p_service.product_tmpl_id
            LEFT JOIN stock_picking sj ON sp.surat_jalan_id = sj.id
            LEFT JOIN res_partner src ON src.id = sp.vendor
            LEFT JOIN res_partner dest ON dest.id = sp.vendor_dest_loc_subcon or dest.id = sp.vendor_dest_loc
            WHERE 
                (ps.invoice_created = false or ps.invoice_created is null) AND 
                sp.scheduled_date BETWEEN date_start AND date_end AND
                input_vendor in ('', CAST(src.name AS CHAR), CAST(dest.name AS CHAR)); 
        BEGIN
            delete from subcon_report;
            
            for rec in csr loop
                insert into subcon_report (pricelist_subcon_id, pricelist_subcon_line_id, move_id, picking_id,
                    date, product_id, service_id, date_transfer, name_service, customer, subcon, subcon_dest, no_sj,
                    qty, qty_component, price_service, tot_price_service, price_transport, tot_price_transport, 
                    total_price) 
                    values (rec.pricelist_subcon_id, rec.pricelist_subcon_line_id, rec.move_id, rec.picking_id, 
                    rec.date, rec.product_id, rec.service_id, rec.date_transfer, rec.name_service, rec.customer, rec.subcon, rec.subcon_dest, rec.no_sj,
                    rec.qty, rec.qty_component, rec.price_service, rec.tot_price_service, rec.price_transport, rec.tot_price_transport,
                    rec.total_price);
	        end loop;
        END;

        $BODY$
        LANGUAGE plpgsql;
        """)
