from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
from lxml import etree
import json
# import simplejson

class InheritPurchaseOrder(models.Model):
    _inherit = "purchase.order"

    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to_approve', 'To be Approve'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ])
    
    with_approval = fields.Boolean("With Approval", compute="get_approval_setting")
    history_approval_ids = fields.One2many('history.approval', 'po_id', 'History Approvals')
    total_value_approve = fields.Integer(string='Value Approve', compute="calculate_total_val_approve", store=True)
    department_approvals = fields.Many2many(
        comodel_name='hr.department', 
        string='Department Approval',
        compute="get_user_approval",
        readonly=1,
        store=True,
        copy=False
    )
    job_approvals = fields.Many2many(
        comodel_name='hr.job', 
        string='Job Approval',
        compute="get_user_approval",
        readonly=1,
        store=True,
        copy=False
    )
    total_action_approve = fields.Integer("Total Action", compute="get_total_action", store=1)
    need_approval_current_user = fields.Boolean(string='Need Approval User?', compute="_need_approval_current_user")
    receipt_done = fields.Boolean(string='Receipt Done ?', compute="set_receipt_done", store=True, readonly=True, default=0, copy=False)
    is_editable = fields.Boolean(string='Is Editable?', compute="_compute_is_editable")
    cannot_to_draft = fields.Boolean(string="Can't set to Draft?", readonly=True, store=True, copy=False)
    
    def get_department_base_on_user_login(self):
        user = self.env.user
        return user.employee_id.department_id.id or None

    department = fields.Many2one('hr.department', string='Department', required=True, default=get_department_base_on_user_login)

    @api.depends('picking_count')
    def set_receipt_done(self):
        for rec in self:
            rec.receipt_done = 1 if rec.picking_count else 0

    @api.depends('state', 'cannot_to_draft')
    def _compute_is_editable(self):
        for rec in self:
            if rec.with_approval and (
                (
                    rec.need_approval_current_user or 
                    rec.state not in ['to_approve', 'approved'] 
                ) and not rec.cannot_to_draft  
            ) or not rec.with_approval:
                rec.is_editable = True
            else: 
                rec.is_editable = False

    @api.depends('with_approval', 'department_approvals', 'job_approvals')
    def _need_approval_current_user(self):
        for rec in self:
            approved_users = [i.user_id.id for i in rec.history_approval_ids if i.value == 1]
            rec.need_approval_current_user = 1 if self.env.user not in approved_users and \
                (
                    self.env.user.employee_id.department_id in rec.department_approvals or
                    self.env.user.employee_id.job_id in rec.job_approvals
                ) else 0

    @api.depends('with_approval', 'state', 'department')
    def get_total_action(self):
        for rec in self:
            # approval_setting = self._get_approval_setting()
            list_approval_po = self._get_approval_base_on_department(based_nominal=True)
            rec.total_action_approve = sum([l.total_action for l in list_approval_po])
    
    def _get_approval_base_on_department(self, based_nominal=False):
        for rec in self:
            list_approval = self.env['list.approval.po'].sudo().search([
                ('active', '=', 1), 
                ('department', '=', rec.department.id)
            ])

            if based_nominal:
                new_list_approval = []
                # check berdsasarkan nominal
                list_approval = self._get_approval_base_on_department()
                for aprv in list_approval:
                    min_amount = self.env.company.currency_id._convert(aprv.min_amount, rec.currency_id, rec.company_id, rec.date_order or fields.Date.today())
                    max_amount = self.env.company.currency_id._convert(aprv.max_amount, rec.currency_id, rec.company_id, rec.date_order or fields.Date.today())
                    if rec.amount_total >= min_amount and rec.amount_total <= max_amount:
                        new_list_approval.append(aprv)
                list_approval = new_list_approval

            return list_approval

    @api.depends('with_approval', 'state', 'total_value_approve')
    def get_user_approval(self):
        for rec in self:
            rec.department_approvals = rec.job_approvals = [(6,0,[])]

            list_approval_po = self._get_approval_base_on_department()
            approval_setting = self._get_approval_setting()
            if not approval_setting: return

            # check berdsasarkan nominal
            list_approval = self._get_approval_base_on_department(based_nominal=True)
            accumulate_value = 0
            for aprv in list_approval:            
                for l in aprv.approval_ids:
                    accumulate_value += l.total_action
                    if accumulate_value > rec.total_value_approve:
                        if l.department: rec.department_approvals = [(4,l.department.id)]
                        if l.job: rec.job_approvals = [(4,l.job.id)]    
                        break
                    
    @api.depends('history_approval_ids.value')
    def calculate_total_val_approve(self):
        for rec in self:
            rec.total_value_approve = sum([i.value for i in rec.history_approval_ids])

    def _get_approval_setting(self):
        approval_setting = self.env['approval.setting'].sudo().search([('id', '=', 1)])
        return approval_setting or None

    @api.depends('state')
    def get_approval_setting(self):
        for rec in self:
            with_approval = 0
            approval_setting = self._get_approval_setting()
            if (approval_setting and not approval_setting[0].po_with_approval) or\
                not approval_setting: 
                rec.with_approval = 0
                return 
                
            # check berdsasarkan nominal
            list_approval = self._get_approval_base_on_department()
            for aprv in list_approval:
                min_amount = self.env.company.currency_id._convert(aprv.min_amount, rec.currency_id, rec.company_id, rec.date_order or fields.Date.today())
                max_amount = self.env.company.currency_id._convert(aprv.max_amount, rec.currency_id, rec.company_id, rec.date_order or fields.Date.today())
                if rec.amount_total >= min_amount and rec.amount_total <= max_amount:
                    with_approval = 1

            rec.with_approval = with_approval

    def action_req_approval(self):
        for rec in self:
            rec.action_approve(first=True)
        
    def action_approve(self, first=False):
        def get_value_action_base_on_user_login():
            value_approve = 0
            list_approval_pr = self._get_approval_base_on_department()
            for line in list_approval_pr.approval_ids:
                user_login = self.env.user
                if (user_login.employee_id.department_id.id == line.department.id and line.department.id) or \
                (user_login.employee_id.job_id.id == line.job.id and line.job.id):
                    value_approve = line.value_first_action if first else 1

            return value_approve

        for rec in self:
            # validation 
            if not first and not rec.need_approval_current_user:
                raise UserError("""You donot have permission for approve this document. please refresh this page for get current state of the document.""")

            value_approve = get_value_action_base_on_user_login()

            if value_approve:
                rec.history_approval_ids = [(0,0, {
                    'user_id': self.env.user.id,
                    'approve': value_approve,
                    'value': value_approve
                })]

            if rec.total_action_approve == rec.total_value_approve:
                rec.state = "approved"
            else:
                rec.state = "to_approve"

    def button_draft(self):
        # validate
        for rec in self:
            if rec.cannot_to_draft:
                raise UserError('Document cannot set to draft from approval User.')

        return super().button_draft()

    def action_reject(self):
        for rec in self:
            # validation 
            if not rec.need_approval_current_user:
                raise UserError("""You donot have permission for approve this document. please refresh this page for get current state of the document.""")

            rec.history_approval_ids = [(0,0, {
                'user_id': self.env.user.id,
                'approve': 0,
                'value': 0
            })]

            for i in rec.history_approval_ids:
                i.value = 0

            rec.state = "rejected"

    def action_reject_without_set_to_draft(self):
        self.action_reject()
        for rec in self:
            rec.cannot_to_draft = 1

    def button_confirm(self):
        for order in self:
            if order.state not in ['draft', 'sent', 'approved']:
                continue
            order._add_supplier_to_product()
            # Deal with double validation process
            if order.company_id.po_double_validation == 'one_step'\
                    or (order.company_id.po_double_validation == 'two_step'\
                        and order.amount_total < self.env.company.currency_id._convert(
                            order.company_id.po_double_validation_amount, order.currency_id, order.company_id, order.date_order or fields.Date.today()))\
                    or order.user_has_groups('purchase.group_purchase_manager'):
                order.button_approve()
            else:
                order.write({'state': 'to approve'})
        return True

    def make_receipt(self):
        res = super()._create_picking()
        return res

    def _create_picking(self):
        for rec in self:
            if not rec.with_approval:
                return super()._create_picking()
        return True

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super().fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)        
        readonly = False
        
        obj = None
        if not self:
            id = dict(self._context).get('params', {}).get('id', None) or None
            model = dict(self._context).get('params', {}).get('model', None) or None
            if id and model:
                obj = self.env[model].sudo().search([('id', '=', id)])
        else: obj = self

        if model and model != "purchase.order":
            return res

        for rec in obj or []:
            if rec.with_approval and not rec.need_approval_current_user:
                readonly = True
        
        if readonly:
            doc = etree.XML(res['arch'])
            if view_type == "form":
                for node in doc.xpath('//field'):
                    node.set('readonly', '1')
                    node_values = node.get('modifiers')
                    modifiers = json.loads(node_values)
                    modifiers['readonly'] = True
                    node.set('modifier', json.dumps(modifiers))
                res['arch'] = etree.tostring(doc)

        return res

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        res = super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

        show_by_department = 0
        for d in domain:
            if 'need_approval_current_user' in d: 
                show_by_department = 1 
                break

        if show_by_department:
            new_res = []
            for r in res:
                if self.env['purchase.order'].sudo().search([('id', '=', r['id'])]).need_approval_current_user:
                    new_res.append(r)
            res = new_res
        return res


class InheritPurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    cannot_to_draft = fields.Boolean(string="Can't set to Draft?", compute="set_cannot_to_draft", store=True, copy=False)
    is_editable = fields.Boolean(string='Is Editable?', compute="_compute_is_editable")

    @api.depends('order_id', 'order_id.cannot_to_draft')
    def set_cannot_to_draft(self):
        for rec in self:
            rec.cannot_to_draft = 1 if rec.order_id and rec.order_id.cannot_to_draft else 0

    @api.depends('order_id', 'order_id.state', 'order_id.is_editable')
    def _compute_is_editable(self):
        for rec in self:
            if rec.order_id and \
                (
                    rec.order_id.with_approval and 
                    rec.order_id.need_approval_current_user 
                    and rec.order_id.state in ['to_approve', 'approved']
                ) or (
                    rec.order_id.state not in ['to_approve', 'approved']
                )\
                or not rec.order_id.with_approval:
                rec.is_editable = True                
            else:
                rec.is_editable = False

class HistoryApproval(models.Model):
    _name = "history.approval"

    po_id = fields.Many2one('purchase.order', string='PO ID', ondelete='cascade', index=True)
    pr_id = fields.Many2one('purchase.request', string='PR ID')
    user_id = fields.Many2one('res.users', string='User', readonly="1")
    approve = fields.Integer(string='Approve', readonly="1")
    value = fields.Integer(string='Value', readonly="1")
    datetime = fields.Datetime(string='Datetime', default=datetime.now(), readonly="1")
