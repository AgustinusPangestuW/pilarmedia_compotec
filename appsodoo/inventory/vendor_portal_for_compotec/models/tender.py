from odoo import models, fields, api, _

class Tender(models.Model):
    _name = 'tender'
    _description = "Tender"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    READONLY_STATES = {
        'post': [('readonly', True)]
    }

    def get_current_supplier(self):
        partner_id = self.env.user.partner_id
        return partner_id.id if partner_id.is_supplier else ""

    name = fields.Char(string='Name', states=READONLY_STATES, copy=False)
    supplier_id = fields.Many2one('res.partner', string='Supplier', default=get_current_supplier, 
        states=READONLY_STATES)
    posting_date = fields.Date(string='Posting Date', readonly=1, states=READONLY_STATES)
    item_ids = fields.One2many('tender.line', 'tender_id', 'Line', required=True, copy=1,
        states=READONLY_STATES)
    state = fields.Selection([
            ('draft', 'Draft'),
            ('post', 'Post'),
        ], string='Status', default='draft', copy=0)

    def action_post(self):
        for rec in self:
            rec.state = "post"
            rec.posting_date = fields.Date.today()
            for line in rec.item_ids:
                line.item_catalog_id.update({
                    'tender_id': rec.id,
                    'tender_name': rec.name,
                    'tender_date': rec.posting_date,
                    'price': line.price
                })

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            seq_date = None
            vals['name'] = self.env['ir.sequence'].next_by_code('item_catalog', sequence_date=seq_date) or _('New')

        return super().create(vals) 
   

class TenderLine(models.Model):
    _name = "tender.line"

    tender_id = fields.Many2one('tender', 'Tender ID', index=1, ondelete='cascade')
    item_catalog_id = fields.Many2one('item.catalog', string='Item Catalog', required=True, 
        ondelete='restrict')
    price = fields.Float(string='Price', required=True)