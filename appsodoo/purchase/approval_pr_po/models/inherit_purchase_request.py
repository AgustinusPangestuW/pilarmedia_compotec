from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
from lxml import etree
import json

class InheritPurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    states = fields.Selection([
        ("draft", "Draft"),
        ("to_approve", "To be approved"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("done", "Done"),
    ])

    def _domain_base_approval_pr(self):
        """ this code is to validate department must be in `list.approval.pr` """
        list_approval_pr = self.env['list.approval.pr'].sudo().search([('active', '=', 1)])
        list_department_ids = [i.department.id for i in list_approval_pr]
        return [('id', 'in', list_department_ids)]

    with_approval = fields.Boolean("With Approval", compute="get_approval_setting")
    history_approval_ids = fields.One2many('history.approval', 'pr_id', 'History Approvals')
    total_value_approve = fields.Integer(string='Value Approve', compute="calculate_total_val_approve", store=True)
    department_approvals = fields.Many2many(
        comodel_name='hr.department', 
        string='Department Approval',
        compute="get_user_approval",
        readonly=1,
        store=True
    )
    job_approvals = fields.Many2many(
        comodel_name='hr.job', 
        string='Job Approval',
        compute="get_user_approval",
        readonly=1,
        store=True
    )
    total_action_approve = fields.Integer("Total Action", compute="get_total_action")
    need_approval_current_user = fields.Boolean(string='Need Approval User?', compute="_need_approval_current_user")
    cannot_to_draft = fields.Boolean(string="Can't set to Draft?", readonly=True, store=True, copy=False)
    
    def get_department_base_on_user_login(self):
        user = self.env.user
        return user.employee_id.department_id.id or None

    department = fields.Many2one('hr.department', string='Department', required=True, 
        default=get_department_base_on_user_login, domain=_domain_base_approval_pr)

    @api.depends('with_approval', 'department_approvals', 'job_approvals')
    def _need_approval_current_user(self):
        for rec in self:
            approved_users = [i.user_id.id for i in rec.history_approval_ids if i.value == 1]
            rec.need_approval_current_user = 1 if self.env.user not in approved_users and \
                (
                    self.env.user.employee_id.department_id in rec.department_approvals or
                    self.env.user.employee_id.job_id in rec.job_approvals
                ) else 0

    @api.depends('with_approval', 'state')
    def get_total_action(self):
        for rec in self:
            approval_setting = self._get_approval_setting()
            list_approval_pr = self._get_approval_base_on_department()
            rec.total_action_approve = sum(i.total_action for i in list_approval_pr)

    def _get_approval_base_on_department(self):
        for rec in self:
            list_approval = self.env['list.approval.pr'].sudo().search([
                ('active', '=', 1), 
                ('department', '=', rec.department.id)
            ])
            return list_approval
    
    @api.depends('with_approval', 'state', 'total_value_approve')
    def get_user_approval(self):
        for rec in self:
            rec.department_approvals = rec.job_approvals = [(6,0,[])]

            list_approval_pr = self._get_approval_base_on_department()
            approval_setting = self._get_approval_setting()
            if not approval_setting: return
            
            accumulate_value = 0
            for i in list_approval_pr:
                for l in i.approval_ids:
                    accumulate_value += l.total_action
                    if accumulate_value > rec.total_value_approve:
                        if l.department: rec.department_approvals = [(4,l.department.id)]
                        if l.job: rec.job_approvals = [(4,l.job.id)]
                        break

    def button_to_approve(self):
        res = super().button_to_approve()
        self.button_approved(first=True)
        return res
                    
    @api.depends('history_approval_ids.value')
    def calculate_total_val_approve(self):
        for rec in self:
            rec.total_value_approve = sum([i.value for i in rec.history_approval_ids])

    def _get_approval_setting(self):
        approval_setting = self.env['approval.setting'].sudo().search([('id', '=', 1)])
        return approval_setting or None

    # @api.depends('state')
    def get_approval_setting(self):
        for rec in self:
            approval_setting = self._get_approval_setting()
            list_approval_pr = self._get_approval_base_on_department()
            
            if approval_setting and approval_setting[0].pr_with_approval \
                and list_approval_pr:
                rec.with_approval = 1
            else:
                rec.with_approval = 0

    def button_approved(self, first=False):
        def get_value_action_base_on_user_login():
            value_approve = 0
            list_approval_pr = self._get_approval_base_on_department()
            for line in list_approval_pr.approval_ids:
                user_login = self.env.user
                if (user_login.employee_id.department_id.id == line.department.id and line.department.id) or \
                (user_login.employee_id.job_id.id == line.job.id and line.job.id):
                    value_approve = line.value_first_action if first else 1

            return value_approve
            
        def get_list_user_for_approve(departement_approvals, job_approvals):
            approved_users = [str(i.user_id.id) for i in rec.history_approval_ids if i.value == 1]
            approved_users.append(str(self.env.user.id))
            departement_ids = [str(i.id) for i in departement_approvals]
            job_ids = [str(i.id) for i in job_approvals]

            conditions = " and u.id not in (%s) and " % (",".join(approved_users)) if approved_users else ""
            conditions_department = " e.department_id IN (%s) " % (",".join(departement_ids)) if departement_ids else ""
            condition_job = "e.job_id IN (%s) " % (".".join(job_ids)) if job_ids else "" 
            if conditions_department: condition_job = " or "+condition_job

            res = self.env.cr.execute("""
                SELECT u.id as id
                FROM hr_employee e, res_users u
                WHERE u.id = e.user_id  %s %s %s
            """ % (conditions, conditions_department, condition_job))
            res = self.env.cr.dictfetchall()
            user_ids = [i['id'] for i in res]
            return user_ids

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
                # internal notification (ToDo)
                user_ids = get_list_user_for_approve(rec.department_approvals, rec.job_approvals)
                for i in user_ids:
                    ir_models = self.env['ir.model'].sudo().search([('model', '=', 'purchase.request')])
                    model_id = ir_models[0].id if ir_models else None
                    mail = self.env['mail.activity'].sudo().create({
                        'activity_type_id': 4,
                        'date_deadline': datetime.today().strftime("%Y-%m-%d"),
                        'note': "<p>tolong segera konfirmasi</p>",
                        'res_id': rec.id,
                        'user_id': i,
                        'res_model_id': model_id
                    })

    def button_rejected(self):
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

            res = super().button_rejected()
            return res

    def action_reject_without_set_to_draft(self):
        self.button_rejected()
        for rec in self:
            rec.cannot_to_draft = 1

    def button_confirm(self):
        for order in self:
            if order.state not in ['draft', 'sent', 'approved']:
                continue
            order._add_supplier_to_product()
            # Deal with double validation process
            if order.company_id.pr_double_validation == 'one_step'\
                    or (order.company_id.pr_double_validation == 'two_step'\
                        and order.amount_total < self.env.company.currency_id._convert(
                            order.company_id.pr_double_validation_amount, order.currency_id, order.company_id, order.date_order or fields.Date.today()))\
                    or order.user_has_groups('purchase.group_purchase_manager'):
                order.button_approve()
            else:
                order.write({'state': 'to approve'})
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

    @api.depends("state", 'cannot_to_draft')
    def _compute_is_editable(self):
        for rec in self:
            if rec.with_approval:
                if (
                        rec.need_approval_current_user or \
                        rec.state not in ("to_approve", "approved", "rejected", "done")
                    ) and not rec.cannot_to_draft:
                    rec.is_editable = True
                else: rec.is_editable = False
            else:
                if rec.state in ("to_approve", "approved", "rejected", "done"):
                    rec.is_editable = False
                else:
                    rec.is_editable = True

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
                if self.env['purchase.request'].sudo().search([('id', '=', r['id'])]).need_approval_current_user:
                    new_res.append(r)
            res = new_res
        return res


class InheritPurchaseRequestLines(models.Model):
    _inherit = "purchase.request.line"

    is_editable = fields.Boolean(default=1)
    cannot_to_draft = fields.Boolean(string="Can't set to Draft?", compute="set_cannot_to_draft", store=True, copy=False)

    @api.depends('request_id', 'request_id.cannot_to_draft')
    def set_cannot_to_draft(self):
        for rec in self:
            rec.cannot_to_draft = 1 if rec.request_id and rec.request_id.cannot_to_draft else 0

    @api.depends(
        "product_id",
        "name",
        "product_uom_id",
        "product_qty",
        "analytic_account_id",
        "date_required",
        "specifications",
        "purchase_lines",
        "cannot_to_draft"
    )
    def _compute_is_editable(self):
        for rec in self:
            if rec.request_id.with_approval:
                if (
                        rec.request_id.need_approval_current_user or \
                        rec.request_id.state not in ("to_approve", "approved", "rejected", "done")
                    ) and not rec.request_id.cannot_to_draft:
                    rec.is_editable = True
                else: rec.is_editable = False
            else:
                if rec.request_id.state in ("to_approve", "approved", "rejected", "done"):
                    rec.is_editable = False
                else:
                    rec.is_editable = True
        for rec in self.filtered(lambda p: p.purchase_lines):
            if rec.request_id.with_approval:
                if rec.request_id.need_approval_current_user:
                    rec.is_editable = True
                else: rec.is_editable = False
            else:
                rec.is_editable = False