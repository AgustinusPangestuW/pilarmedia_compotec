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
    job_ids_active = fields.Boolean(string='Job ID Active', compute="_set_job_id_active", store=False)
    job_ids = fields.Many2one(
        'job', 
        string='Job', 
        domain=[('active', '=', 1)], 
        required=True
    )
    lot_lines = fields.One2many('wholesale.job.line', 'wholesale_job_ids', 'Lot Line', auto_join=True)
    checked_coordinator = fields.Many2one('employee.custom', string='Checked Coordinator')
    checked_qc = fields.Many2one('employee.custom', string='Checked QC')
    shift = fields.Many2one('shift', string='Shift')

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

    @api.depends('lot_lines')
    def _set_job_id_active(self):
        for rec in self:
            if len(rec.lot_lines) > 0: rec.job_ids_active = 1
            else: rec.job_ids_active = 0


class WholesaleJobLine(models.Model):
    _name = "wholesale.job.line"
    _description = "Wholesale Job Line"

    sequence = fields.Integer(string='Sequence')
    wholesale_job_ids = fields.Many2one(
        'wholesale.job', 
        'wholesale job ids', 
        index=1, 
        ondelete="cascade", 
        copy=False
    )
    is_set = fields.Boolean(
        string='Is Set', 
        readonly=True, 
        compute="_get_detail_product", 
        store=True,
        help="This field will be True when product UOM = `set`"
    )
    job_ids = fields.Many2one(
        'job', string='Job', 
        required=True, 
        readonly=True, 
        domain=[('active', '=', 1)]
    )
    product_ids = fields.Many2one('product.product', string='Produk', required=True)
    user_ids = fields.Many2one('employee.custom', string='Nama', required=True)
    total_set = fields.Float(string="Total SET", readonly=True, compute="_calc_total_set", store=True)
    total_ng = fields.Float(string="Total NG", compute="_calc_total_ng_ok", store=True)
    total_ok = fields.Float(string="Total OK", readonly=True, compute="_calc_total_ng_ok", store=True)
    total_pcs = fields.Float(string='Total PCS', readonly=True, compute="_calc_total_ng_ok", store=True)
    factor = fields.Float(string='Factor')
    biggest_lot = fields.Many2one(
        'lot', 
        string='Last Lot', 
        readonly=True, 
        compute="_compute_get_biggest_lot", 
        store=True, 
        help="this field for track last Lot ID"
    )
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
        list_lots = self.env['lot'].sudo().search([]).sorted(key=lambda r: int(r.name))

        # get list data `job_lot_line`
        if len(self.wholesale_job_lot_lines) > 0:
            biggest_lot_id = self.wholesale_job_lot_lines[-1].lot_ids.id
        elif len(list_lots) > 0:
            # isikan lot pertama
            next_lot_id = list_lots[0].id 
        else:
            raise exceptions.ValidationError(_("System don't have master Lot, please insert master Lot."))

        if biggest_lot_id:
            # ambil urutan lot setelahnya untuk set lot id saat ini
            for idx_l, l in enumerate(list_lots):
                if int(l.id) == int(biggest_lot_id) and len(list_lots) > idx_l+1:
                    next_lot_id = list_lots[idx_l+1].id
                    break

        biggest_lot_id = next_lot_id

        if not biggest_lot_id:
            raise exceptions.ValidationError(_("cur lots is out of range, please add new lots in configuration."))
        
        self.update({
            'wholesale_job_lot_lines': [[0,0,{ 'lot_ids': biggest_lot_id, 'wholesale_job_line_ids': self.id }]],
            'biggest_lot': biggest_lot_id
        })

        self._calc_total_set()
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

            self._calc_total_set()
            self._calc_total_ng_ok()

            return self
        else:
            raise exceptions.ValidationError(_("cur Job Lot Line is null."))

    @api.depends('is_set', 'wholesale_job_lot_lines.ng', 'wholesale_job_lot_lines.ok', \
        'total_set', 'total_ng')
    def _calc_total_ng_ok(self):
        for rec in self:
            # calculation NG & OK when is_set = FALSE (NON set)
            if not rec.is_set:
                self._calculate_ok_ng_pcs()

            # calculation NG & OK when is_set = TRUE
            else:
                self._calc_ok()


    def _calculate_ok_ng_pcs(self):
        total_ng, total_ok, total_pcs = 0, 0, 0
        for rec in self:
            if not rec.is_set:
                for line in self.wholesale_job_lot_lines:
                    total_ng += line.ng
                    total_ok += line.ok
                    total_pcs = total_ng + total_ok

                rec.update({
                    'total_ng': total_ng,
                    'total_ok': total_ok,
                    'total_pcs': total_pcs
                }) 

    @api.onchange('total_ng', 'total_set')
    def _calc_ok(self):
        for rec in self:
            # calculation NG & OK when is_set = TRUE
            if rec.is_set:
                rec.update({
                    'total_ok': rec.total_set - rec.total_ng
                })
            
    @api.depends('factor', 'is_set')
    def _calc_total_set(self):
        new_total_lot = 0
        for rec in self:
            if rec.is_set:
                last_lot_list = rec.wholesale_job_lot_lines
                last_lot_name = ''
                if len(last_lot_list) > 0:
                    last_lot_name = last_lot_list[-1].lot_ids.name
                    new_total_lot = int(rec.factor) * int(last_lot_name)
            else:
                new_total_lot = 0
        rec.total_set = new_total_lot

    @api.depends('product_ids')
    def _get_detail_product(self):
        new_is_set = 0
        for rec in self:
            if rec.product_ids: 
                uom = rec.product_ids.product_tmpl_id.uom_id.name
                if uom.lower() == "set":
                    new_is_set = 1
            
            rec.is_set = new_is_set

class WholesaleJobLotLine(models.Model):
    _name = "wholesale.job.lot.line"
    _description = "Wholesale Job Lot Line"
    _rec_name = "lot_ids"
    
    wholesale_job_line_ids = fields.Many2one('wholesale.job.line','Wholesale Job Line ID', index=1, ondelete="cascade")
    lot_ids = fields.Many2one('lot', string='Lot No', required=True, readonly=True)
    ok = fields.Float(string='OK')
    ng = fields.Float(string='NG')