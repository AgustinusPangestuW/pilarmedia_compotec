from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.http import request

class approval_setting(models.Model):
    _name = "approval.setting"
    _description = "Approval Setting"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    pr_with_approval = fields.Boolean(string='PR with Approval ?', tracking=True)
    po_with_approval = fields.Boolean(string='PO with Approval ?', tracking=True)


class InheritResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    def fetch_pr(self):
        approval_setting = self.env['approval.setting'].sudo().search([])
        pr_approval = 0
        for i in approval_setting:
            if i.pr_with_approval: pr_approval = 1
        return pr_approval

    def fetch_po(self):
        approval_setting = self.env['approval.setting'].sudo().search([])
        po_approval = 0
        for i in approval_setting:
            if i.po_with_approval: po_approval = 1
        return po_approval

    pr_with_approval = fields.Boolean(string='PR with Approval ?', default=fetch_pr, readonly=False)
    po_with_approval = fields.Boolean(string='PO with Approval ?', default=fetch_po, readonly=False)

    def write(self, vals):
        if 'pr_with_approval' in self or 'po_with_approval' in self:
            approval_setting = self.env['approval.setting'].sudo().search([])
            if approval_setting:
                approval_setting.pr_with_approval = self.pr_with_approval or 0
                approval_setting.po_with_approval = self.po_with_approval or 0
            else:
                self.env['approval.setting'].sudo().create({
                    'pr_with_approval': self.pr_with_approval or 0,
                    'po_with_approval': self.po_with_approval or 0
                })

        res = super().write(vals)
        return res