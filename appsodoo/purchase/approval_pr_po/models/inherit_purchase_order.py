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
    user_approval = fields.Many2many(
        comodel_name='res.users', 
        string='User Approval',
        compute="get_user_approval",
        readonly=1,
        store=True
    )
    total_action_approve = fields.Integer("Total Action", compute="get_total_action")
    need_approval_current_user = fields.Boolean(string='Need Approval User?', compute="_need_approval_current_user")
    receipt_done = fields.Boolean(string='Receipt Done ?', store=True, readonly=True)
    is_editable = fields.Boolean(string='Is Editable?', compute="_compute_is_editable")

    @api.depends('state')
    def _compute_is_editable(self):
        for rec in self:
            if rec.with_approval and self.env.user in rec.user_approval or \
                not rec.with_approval:
                rec.is_editable = True
            else: 
                rec.is_editable = False

    @api.depends('with_approval', 'user_approval')
    def _need_approval_current_user(self):
        for rec in self:
            rec.need_approval_current_user = 1 if self.env.user in rec.user_approval else 0

    @api.depends('with_approval', 'state', 'with_approval')
    def get_total_action(self):
        for rec in self:
            approval_setting = self._get_approval_setting()
            rec.total_action_approve = approval_setting.total_action_po if approval_setting else 0
    
    @api.depends('with_approval', 'state', 'total_value_approve')
    def get_user_approval(self):
        for rec in self:
            rec.user_approval = [(6,0,[])]

            approval_setting = self._get_approval_setting()
            if not approval_setting: return
            
            accumulate_value = 0
            approved_users = [i.user_id.id for i in rec.history_approval_ids if i.value == 1]
            for i in approval_setting.list_approval_po:
                accumulate_value += i.total_action
                if accumulate_value > rec.total_value_approve:
                    rec.user_approval = [(4,u.user_id.id) for u in i.group_user_approval.user_approval_ids \
                        if u.user_id.id not in approved_users]
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
            approval_setting = self._get_approval_setting()
            rec.with_approval = approval_setting[0].po_with_approval if approval_setting else 0

    def action_approve(self):
        for rec in self:
            # validation 
            if rec.env.user not in rec.user_approval:
                raise UserError("""You donot have permission for approve this document. please refresh this page for get current state of the document.""")

            rec.history_approval_ids = [(0,0, {
                'user_id': self.env.user.id,
                'approve': 1,
                'value': 1
            })]

            if rec.total_action_approve == rec.total_value_approve:
                rec.state = "approved"
            else:
                rec.state = "to_approve"

    def action_reject(self):
        for rec in self:
            # validation 
            if rec.env.user not in rec.user_approval:
                raise UserError("""You donot have permission for approve this document. please refresh this page for get current state of the document.""")

            rec.history_approval_ids = [(0,0, {
                'user_id': self.env.user.id,
                'approve': 0,
                'value': 0
            })]

            for i in rec.history_approval_ids:
                i.value = 0

            rec.state = "rejected"

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
        for rec in self: 
            rec.receipt_done = 1
        return res

    def _create_picking(self):
        for rec in self:
            if not rec.with_approval:
                rec.receipt_done = 1
                return super()._create_picking()

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
            if rec.with_approval and rec.env.user.id not in [i.id for i in rec.user_approval]:
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


class InheritPurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    is_editable = fields.Boolean(string='Is Editable?', compute="_compute_is_editable")

    @api.depends('order_id', 'order_id.state', 'order_id.is_editable')
    def _compute_is_editable(self):
        for rec in self:
            if rec.order_id and \
                (
                    rec.order_id.with_approval and 
                    self.env.user in rec.order_id.user_approval 
                    and rec.order_id.state not in ['to_approve', 'approved']
                ) \
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