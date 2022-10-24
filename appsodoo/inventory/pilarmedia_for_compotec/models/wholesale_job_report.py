import logging

from odoo import models, fields, api
from .employee_custom import _get_domain_user

_logger = logging.getLogger(__name__)


class WholesaleJobReport(models.Model):
    _name = 'wholesale.job.report'
    _description = 'Wholesale Job Report'
    _rec_name = 'date'

    id_wj = fields.Many2one('wholesale.job', string='ID')
    date = fields.Date(string='Date')
    job_id = fields.Many2one('job', string='Job')
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

    def init(self):
        self.env.cr.execute("""
        DROP FUNCTION IF EXISTS wholesale_job_report(DATE, DATE, CHAR, CHAR, CHAR);
        CREATE OR REPLACE FUNCTION wholesale_job_report(date_start DATE, date_end DATE, input_company CHAR, input_job CHAR, input_shift CHAR)
        RETURNS VOID AS $BODY$ 
        DECLARE
            
            csr cursor for
            SELECT 
                wj.id as wj_id, wj.date, j.id as job_id, wjl.product_id as product_id, u.id as user_id, wjl.total_set, wjl.total_ng, 
                wjl.total_ok, wjl.factor, wj.checked_coordinator, wj.checked_qc, wjl.factor, wjl.total_pcs, wjl.biggest_lot
            FROM wholesale_job wj
            LEFT JOIN wholesale_job_line wjl ON wjl.wholesale_job_id = wj.id
            LEFT JOIN job j ON j.id = wj.job_id
            -- LEFT JOIN product_product p ON p.id = wjl.product_id
            -- LEFT JOIN product_template pt ON pt.id = p.product_tmpl_id
            LEFT JOIN res_partner u ON u.id = wjl.operator
            WHERE 
                wj.date BETWEEN date_start AND date_end 
                    AND input_job in ('', CAST(j.id AS CHAR))
                    AND input_shift in ('', CAST(wj.shift AS CHAR))
                    AND input_company in ('', CAST(wj.company_id AS CHAR))
            ORDER BY wj.date;

        BEGIN
            delete from wholesale_job_report;
            
            for rec in csr loop
                insert into wholesale_job_report (id_wj, date, job_id, product_id, operator, total_set, 
                    total_ng, total_ok, checked_coordinator, checked_qc, factor, total_pcs, biggest_lot) 
                    values (rec.wj_id, rec.date, rec.job_id, rec.product_id, rec.user_id, 
                        rec.total_set, rec.total_ng, rec.total_ok, rec.checked_coordinator, 
                        rec.checked_qc, rec.factor, rec.total_pcs, rec.biggest_lot);
	        end loop;
        END;

        $BODY$
        LANGUAGE plpgsql;
        """)
