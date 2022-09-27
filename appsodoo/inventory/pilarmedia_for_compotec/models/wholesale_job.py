from enum import unique
from odoo import models, fields, api, _, exceptions
from datetime import datetime


class Lot(models.Model):
    _name = "lot"
    _sql_constraints = [
        ('check_name_unique', 'UNIQUE(name)', 'The name is not unique')
    ]
    
    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer(string='Sequence')
    description = fields.Text(string='Desciption')


class WholesaleJob(models.Model):
    _name = 'wholesale.job'

    name = fields.Char(string='Wholesale Job Name', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    sequence = fields.Integer(string='Sequence', default=10)
    date = fields.Date(string="Date", required=True, default=datetime.now().date())
    job_ids = fields.Many2one('job', string='Job', required=True, domain=[('active', '=', 1)])
    lot_lines = fields.One2many('wholesale.job.line', 'wholesale_job_ids', 'Lot Line', auto_join=True)
    checked_coordinator = fields.Many2one('employee.custom', string='Checked Coordinator')
    checked_qc = fields.Many2one('employee.custom', string='Checked QC')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            seq_date = None
            if 'date_order' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'wholesale_job', sequence_date=seq_date) or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('wholesale_job', sequence_date=seq_date) or _('New')

        return super().create(vals)  


class WholesaleJobLine(models.Model):
    _name = "wholesale.job.line"
    _description = "Wholesale Job Line"

    sequence = fields.Integer(string='Sequence')
    wholesale_job_ids = fields.Many2one(
        'wholesale.job', 
        'Lot ID', 
        index=1, 
        ondelete="cascade", 
        copy=False
    )
    is_check = fields.Boolean(string='Is Check')
    job_ids = fields.Many2one('job', string='Job', required=True, domain=[('active', '=', 1)])
    product_ids = fields.Many2one('product.product', string='Produk')
    user_ids = fields.Many2one('employee.custom', string='Nama', required=True)
    total_lot = fields.Float(string="Total Lot", readonly=True, compute="_calc_total_lot", store=True)
    total_ng = fields.Float(string="Total NG", readonly=True, compute="_calc_total_ng_ok", store=True)
    total_ok = fields.Float(string="Total OK", readonly=True, compute="_calc_total_ng_ok", store=True)
    total_ok_ng = fields.Float(string='Total OK & NG', readonly=True, compute="_calc_total_ng_ok", store=True)
    factor = fields.Float(string='Factor')
    biggest_lot = fields.Many2one('lot', string='Last Lot ID', readonly=True, compute="_compute_get_biggest_lot", store=True)
    wholesale_job_lot_lines = fields.One2many('wholesale.job.lot.line', 'wholesale_job_line_ids', 'Lot Line', auto_join=True)           

    @api.model
    def default_get(self, fields_list):
        res = super(WholesaleJobLine, self).default_get(fields_list)

        if self.env.context.get('job_id'):
            job_id = self.env.context.get('job_id')
            res.update({'job_ids' : job_id})

        return res

    def add_job_lot_lines(self):
        """
        fucntion for create wholesale_job_lot_lines in different lot ID (unique)
        """
        biggest_lot_id, next_lot_id = "", ""
        list_lots = self.env['lot'].sudo().search([]).sorted('name')

        # get list data `job_lot_line`
        if len(self.wholesale_job_lot_lines) > 0:
            biggest_lot_id = self.wholesale_job_lot_lines[-1].lot_ids.id
        else:
            # isikan lot pertama
            next_lot_id = list_lots[0].id 

        if biggest_lot_id:
            # ambil urutan lot setelahnya untuk set lot id saat ini
            for idx_l, l in enumerate(list_lots):
                if str(l.id) == str(biggest_lot_id) and len(list_lots) > idx_l+1:
                    next_lot_id = list_lots[idx_l+1].id
                    break

        biggest_lot_id = next_lot_id

        if not biggest_lot_id:
            raise exceptions.ValidationError(_("cur lots is out of range, please add new lots in configuration."))
        
        self.update({
            'wholesale_job_lot_lines': [[0,0,{ 'lot_ids': biggest_lot_id, 'wholesale_job_line_ids': self.id }]],
            'biggest_lot': biggest_lot_id
        })

        self._calc_total_lot()
        self._calc_total_ng_ok()

        return self

    def remove_job_lot_lines(self):    
        # validation list job_lot_lines
        if len(self.wholesale_job_lot_lines) > 0:
            new_job_lot_line = self.wholesale_job_lot_lines[:-1]
            biggest_lot = None

            if len(new_job_lot_line) > 0:
                biggest_lot = new_job_lot_line[-1].lot_ids.id
            
            self.write({
                'wholesale_job_lot_lines': new_job_lot_line,
                'biggest_lot': biggest_lot
            })

            self._calc_total_lot()
            self._calc_total_ng_ok()

            return self
        else:
            raise exceptions.ValidationError(_("cur Job Lot Line is null."))

    @api.depends('is_check', 'wholesale_job_lot_lines.ng', 'wholesale_job_lot_lines.ok')
    def _calc_total_ng_ok(self):
        total_ng, total_ok = 0, 0
        for rec in self:
            for line in self.wholesale_job_lot_lines:
                if not rec.is_check:
                    total_ng += line.ng
                    total_ok += line.ok

            rec.update({
                'total_ng': total_ng,
                'total_ok': total_ok,
                'total_ok_ng': total_ok + total_ng
            }) 
            
    @api.depends('factor', 'is_check')
    def _calc_total_lot(self):
        new_total_lot = 0
        for rec in self:
            if rec.is_check:
                last_lot_list = rec.wholesale_job_lot_lines
                last_lot_name = ''
                if len(last_lot_list) > 0:
                    last_lot_name = last_lot_list[-1].lot_ids.name
                    new_total_lot = int(rec.factor) * int(last_lot_name)
            else:
                new_total_lot = 0
        rec.total_lot = new_total_lot
                

class WholesaleJobLotLine(models.Model):
    _name = "wholesale.job.lot.line"
    _description = "Wholesale Job Lot Line"
    _rec_name = "lot_ids"
    
    wholesale_job_line_ids = fields.Many2one('wholesale.job.line','Wholesale Job Line ID', index=1, ondelete="cascade")
    lot_ids = fields.Many2one('lot', string='Lot No', required=True, readonly=True)
    ok = fields.Float(string='OK')
    ng = fields.Float(string='NG')