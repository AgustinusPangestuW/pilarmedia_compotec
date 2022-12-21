from odoo import models, fields, api

class SettingApprovalPR(models.Model):
    _name = 'list.approval.pr'

    active = fields.Boolean(string='Active', default=1)
    department = fields.Many2one('hr.department', string='Department', required=True)
    total_action = fields.Integer(string='Total Action', compute="calculate_total_action", store=True)
    approval_ids = fields.One2many('approval.line', 'list_approval_pr_id', string='Approval Line')

    _sql_constraints = [
        ('department', 'unique(department)', 'Department must be unique!'),
    ]

    @api.depends('approval_ids')
    def calculate_total_action(self):
        for rec in self:
            rec.total_action = sum([i.total_action for i in rec.approval_ids])


class SettingApprovalPO(models.Model):
    _name = 'list.approval.po'

    sequence = fields.Integer(string='Sequence')
    active = fields.Boolean(string='Active', default=1)
    department = fields.Many2one('hr.department', string='Department', required=True)
    total_action = fields.Integer(string='Total Action', compute="calculate_total_action", store=True)
    approval_ids = fields.One2many('approval.line', 'list_approval_po_id', string='Approval Line')
    min_amount = fields.Float(string='Min Amount')
    max_amount = fields.Float(string='Max Amount')

    _sql_constraints = [
        ('apprv_department_unique', 'unique(department, min_amount, max_amount)', 'Department, Min Amount and Max Amount must be unique!'),
    ]

    @api.depends('approval_ids')
    def calculate_total_action(self):
        for rec in self:
            rec.total_action = sum([i.total_action for i in rec.approval_ids])
                        

class ApprovalLine(models.Model):
    _name = "approval.line"

    list_approval_pr_id = fields.Many2one('list.approval.pr', string='List Approval PR ID', 
        index=True, ondelete='cascade')
    list_approval_po_id = fields.Many2one('list.approval.po', string='List Approval PO ID', 
        index=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence')
    department = fields.Many2one('hr.department', string='Department', required=True)
    total_action = fields.Integer(string='Total Action', default="1")