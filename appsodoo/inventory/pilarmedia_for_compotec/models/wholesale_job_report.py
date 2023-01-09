import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from .employee_custom import _get_domain_user

_logger = logging.getLogger(__name__)


class WholesaleJobReport(models.Model):
    _name = 'wholesale.job.report'
    _description = 'Wholesale Job Report'
    _rec_name = 'date'

    id_wj = fields.Many2one('wholesale.job', string='ID Wholesale Job')
    id_wjl = fields.Many2one('wholesale.job.line', string='ID Wholesale Job Line')
    id_wjpl = fields.Many2one('wholesale.job.pricelist', string='ID Pricelist')
    id_wjb = fields.Many2one('wholesale.job.billed', string='ID Billed')
    
    date = fields.Date(string='Date')
    job = fields.Many2one('job', string='Job')
    product_id = fields.Many2one('product.product', string='Product')
    operator = fields.Many2one('employee.custom', string='User', domain=_get_domain_user)
    factor = fields.Float(string='Factor')
    total_ng = fields.Float(string='Total NG')
    total_ok = fields.Float(string='Total OK')
    biggest_lot = fields.Many2one('lot', string="Last Lot")
    total_set = fields.Float(string='Total Set')
    total_pcs= fields.Float(string='Total Pcs')
    checked_coordinator = fields.Many2one('employee.custom', string='Checked Coordinator', domain=_get_domain_user)
    checked_qc = fields.Many2one('employee.custom', string='Checked QC', domain=_get_domain_user)
    pricelist_id = fields.Many2one('pilar.pricelist', string='Pricelist ID')
    price = fields.Float(string='Price')
    price_total = fields.Float(string='Price Total')
    created_bill = fields.Boolean(string='Created Bill ?', compute="get_from_wholesale_job_line", store=True)
    
    @api.depends('id_wjb')
    def get_from_wholesale_job_line(self):
        for rec in self:
            bill = rec.id_wjb
            rec.created_bill = bill.created_bill if bill else 0

    def create_bill_base_wjob(self,ret_raise=False):
        invoice_line_ids, wholesale_job_ids = [], []
        for rec in self:
            bill = rec.id_wjb
            if bill and not bill.created_bill:
                invoice_line_ids.append((0,0,{
                    'product_id': rec.pricelist_id.product_id.id,
                    'quantity': rec.total_pcs or rec.total_set or 0,
                    'price_unit': rec.price,
                    'wholesale_job_line_id': rec.id_wjl.id,
                    'tax_ids': []
                }))
                bill[0].created_bill = 1
                rec.created_bill = 1

            if rec.id_wj.id not in [i.id for i in wholesale_job_ids]:
                wholesale_job_ids.append(rec.id_wj)
        
        bill = None
        if invoice_line_ids:
            bill = self.env['account.move'].sudo().create({
                'name': '/',
                'invoice_payment_state': 'not_paid',
                'type': 'in_invoice',
                'invoice_line_ids': invoice_line_ids
            })
            # count billed
            for i in wholesale_job_ids:
                i._count_bill()

        if ret_raise:
            view = self.env.ref('account.view_move_form')

            if not bill:
                raise UserError('Checksheet with ID [%s] is already created bill.' % (rec.id_wj.name))

            return {
                'name': _('Bill'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'account.move',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': bill.id,
                'context': dict(
                    self.env.context
                ),
            }

    def init(self):
        self.env.cr.execute("""
        DROP FUNCTION IF EXISTS wholesale_job_report(DATE, DATE, CHAR, CHAR, CHAR);
        CREATE OR REPLACE FUNCTION wholesale_job_report(date_start DATE, date_end DATE, input_company CHAR, input_job CHAR, input_shift CHAR)
        RETURNS VOID AS $BODY$ 
        DECLARE
            csr cursor for
            SELECT 
                wj.id as wj_id, wjl.id as wjl_id, wj.date, j.id as job, wjl.product_id as product_id, u.id as user_id, wjl.total_set, wjl.total_ng, 
                wjl.total_ok, wjl.factor, wj.checked_coordinator, wj.checked_qc, wjl.factor, wjl.total_pcs, wjl.biggest_lot,
                pl.pricelist_id, pl.price, wjb.created_bill, pl.id as pl_id, wjb.id as wjb_id,
                CASE
                    WHEN wjl.total_pcs > 0 THEN (pl.price * wjl.total_pcs)
                    WHEN wjl.total_set > 0 THEN (pl.price * wjl.total_set)
                END as price_total
            FROM wholesale_job wj
            LEFT JOIN wholesale_job_line wjl ON wjl.wholesale_job_id = wj.id
            LEFT JOIN job j ON j.id = wj.job
            LEFT JOIN wjob_pricelist_line pl ON pl.wholesale_job_id = wj.id 
            -- LEFT JOIN product_product p ON p.id = wjl.product_id
            -- LEFT JOIN product_template pt ON pt.id = p.product_tmpl_id
            LEFT JOIN res_partner u ON u.id = wjl.operator
            LEFT JOIN wholesale_job_billed wjb ON wjb.wjl_id = wjl.id AND wjb.wjpl_id = pl.id
            WHERE 
                wj.state='submit' AND NOT EXISTS (
                    SELECT 1 FROM  wholesale_job_report wjr WHERE wjr.id_wjl = wjl.id
                ) 
                AND wj.date BETWEEN date_start AND date_end 
                AND input_job in ('', CAST(j.id AS CHAR))
                AND input_shift in ('', CAST(wj.shift AS CHAR))
                AND input_company in ('', CAST(wj.company_id AS CHAR))
            ORDER BY wj.date;

        BEGIN            
            for rec in csr loop
                insert into wholesale_job_report (id_wj, id_wjl, date, job, product_id, operator, total_set, 
                    total_ng, total_ok, checked_coordinator, checked_qc, factor, total_pcs, biggest_lot, 
                    pricelist_id, price, price_total, created_bill, id_wjpl, id_wjb) 
                    values (rec.wj_id, rec.wjl_id, rec.date, rec.job, rec.product_id, rec.user_id, 
                        rec.total_set, rec.total_ng, rec.total_ok, rec.checked_coordinator, 
                        rec.checked_qc, rec.factor, rec.total_pcs, rec.biggest_lot, rec.pricelist_id, 
                        rec.price, rec.price_total, rec.created_bill, rec.pl_id, rec.wjb_id);
	        end loop;
        END;

        $BODY$
        LANGUAGE plpgsql;
        """)
