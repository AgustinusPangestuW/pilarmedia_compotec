from odoo import models, fields, api

class ReportVendorPricelist(models.Model):
    _name = 'report.vendor.pricelist'
    _description = "Report vendor Pricelist"

    name = fields.Many2one("purchase.order.line",string="Purchase Order Line")  
    partner_id = fields.Many2one("res.partner",string="Vendor")
    user_id = fields.Many2one("res.users",string="Sales Person")
    product_tmpl_id = fields.Many2one("product.template",string="Template Id")
    variant_id = fields.Many2one("product.product",string="Product")
    purchase_order_id = fields.Many2one("purchase.order",string="Purchase Order")
    confirm_date = fields.Datetime(string="Confirm Date")
    vendor_pricelist_adjustment_id = fields.Many2one('vendor.pricelist.adjustment', string='Vendor Pricelist Adjustment')
    product_uom_qty = fields.Float(string="Quantity")
    unit_price = fields.Float(string="Price")
    currency_id = fields.Many2one("res.currency",string="Currency Id")
    total_price = fields.Monetary(string="Total")

    def init(self):
        self.env.cr.execute("SELECT report_vendor_pricelist()")
        self.env.cr.execute("""
            DROP FUNCTION IF EXISTS report_vendor_pricelist();
            CREATE OR REPLACE FUNCTION report_vendor_pricelist()
            RETURNS VOID AS $BODY$ 
            DECLARE
                csr cursor for
                SELECT 
                    pol.id as name,
                    po.create_uid as user_id, 
                    u.id as partner_id, 
                    pt.id as product_tmpl_id,
                    p.id as variant_id,
                    po.id as purchase_order_id,
                    Null as vendor_pricelist_adjustment_id,
                    po.date_order as confirm_date,
                    pol.product_qty as product_uom_qty,
                    pol.price_unit as unit_price,
                    pol.currency_id as currency_id,
                    pol.price_total as total_price
                FROM purchase_order_line pol
                LEFT JOIN purchase_order po ON po.id = pol.order_id
                LEFT JOIN res_users u ON u.id = pol.partner_id
                LEFT JOIN product_product p ON p.id = pol.product_id
                LEFT JOIN product_template pt ON pt.id = p.product_tmpl_id
                WHERE po.state in ('purchase', 'done') AND NOT EXISTS(
                    SELECT 1 FROM report_vendor_pricelist WHERE name = pol.id
                )
                
                UNION

                SELECT 
                    Null as name,
                    vpa.create_uid as user_id, 
                    u.id as partner_id, 
                    pt.id as product_tmpl_id,
                    p.id as variant_id,
                    Null as purchase_order_id,
                    vpa.id as vendor_pricelist_adjustment_id,
                    vpa.confirm_date as confirm_date,
                    vpa.qty as product_uom_qty,
                    vpa.price as unit_price,
                    vpa.currency_id as currency_id,
                    vpa.price as total_price
                FROM vendor_pricelist_adjustment vpa
                LEFT JOIN res_users u ON u.id = vpa.partner_id
                LEFT JOIN product_product p ON p.id = vpa.product_id
                LEFT JOIN product_template pt ON pt.id = p.product_tmpl_id
                WHERE vpa.state in ('approve') AND NOT EXISTS(
                    SELECT 1 FROM report_vendor_pricelist WHERE 
                        vendor_pricelist_adjustment_id = vpa.id
                );
            BEGIN            
                for rec in csr loop
                    insert into report_vendor_pricelist (name, user_id, partner_id, product_tmpl_id, variant_id, purchase_order_id,
                        confirm_date, product_uom_qty, unit_price, currency_id, total_price, vendor_pricelist_adjustment_id) 
                        values (rec.name, rec.user_id, rec.partner_id, rec.product_tmpl_id, rec.variant_id, rec.purchase_order_id, 
                            rec.confirm_date, rec.product_uom_qty, rec.unit_price, rec.currency_id, rec.total_price, 
                            rec.vendor_pricelist_adjustment_id);
                end loop;
            END;

            $BODY$
            LANGUAGE plpgsql;
            """)