from odoo import models, fields, api, _
from odoo.exceptions import UserError

class approval_setting(models.Model):
    _name = "approval.setting"
    _description = "Approval Setting"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    pr_with_approval = fields.Boolean(string='PR with Approval ?', tracking=True)
    list_approval_pr = fields.One2many('list.approval', 'approval_line_id', 'Line')
    total_action_pr = fields.Integer(string='Total Action', compute="calculate_total_action", 
        store=True)
    po_with_approval = fields.Boolean(string='PO with Approval ?', tracking=True)
    list_approval_po = fields.One2many('list.approval', 'approval_line_id', 'Line')
    total_action_po = fields.Integer(string='Total Action', compute="calculate_total_action", 
        store=True)

    @api.depends('list_approval_po.total_action', 'list_approval_pr.total_action')
    def calculate_total_action(self):
        for rec in self:
            rec.total_action_po = sum([i.total_action for i in rec.list_approval_po])
            rec.total_action_pr = sum([i.total_action for i in rec.list_approval_pr])


class ApprovalList(models.Model):
    _name = "list.approval"
    _description = "List Approval"

    approval_line_id = fields.Many2one('approval.setting', 'Approval ID', 
        ondelete='cascade', index=True)
    sequence = fields.Integer(string='Sequence')
    group_user_approval = fields.Many2one('group.user.approval', 
        string='Group User Approval', required=True)
    total_action = fields.Integer(string='Total Action', default="1", required=True)


class GroupUserApproval(models.Model):
    _name = "group.user.approval"

    name = fields.Char("Name")
    user_approval_ids = fields.One2many('user.approval.line', 'user_approval_id', 'Line')
   
   
class UserApprovalLine(models.Model):
    _name = "user.approval.line"

    user_approval_id = fields.Many2one('group.user.approval', 'User Approval ID', ondelete='cascade', index=True)
    user_id = fields.Many2one('res.users', string='User', required=True,domain=lambda self: [
            (
                "groups_id",
                "in",
                [self.env.ref("purchase_request.group_purchase_request_manager").id, 
                self.env.ref("purchase.group_purchase_user").id],
            )
        ])