from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError
from .employee_custom import _get_domain_user

class PeelDissAssy(models.Model):
    _name = 'peel.diss.assy'
    _description = "Form Kupas Diss Assy"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    sequence = fields.Integer(string='Sequence')
    name = fields.Char(string='Name', readonly=True)
    date = fields.Date(string='Tangal',default=datetime.now().date(), required=True)
    job = fields.Many2one('job', string='Job', required=True)
    state = fields.Selection([
        ("draft","Draft"),
        ("submit","Submited"), 
        ('cancel', "Canceled")], string='State', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True)
    custom_css = fields.Html(string='CSS', sanitize=False, compute='_compute_css', store=False)
    count_mo = fields.Integer(string='Count MO', compute="_count_mo", store=True, readonly=True)
    peel_diss_assy_line = fields.One2many('peel.diss.assy.line', 'peel_diss_assy_id', 'Line')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            seq_date = None
            if 'date_order' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'peel_diss_assy', sequence_date=seq_date) or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('peel_diss_assy', sequence_date=seq_date) or _('New')
        
        vals['company_id'] = self.env.company.id
        vals['state'] = 'draft'

        return super().create(vals)  

    @api.depends('state')
    def _compute_css(self):
        for rec in self:
            if rec.state != 'draft':
                rec.custom_css = '<style>.o_form_button_edit {display: none !important;}</style>'
            else:
                rec.custom_css = False

    def action_submit(self):
        self.state = "submit"
        self.create_mo()

    def write(self, vals):  
        # if self.state in ['submit']:
        #     raise ValidationError(_("You Cannot Edit %s as it is in %s State" % (self.name, self.state)))

        vals = super().write(vals)

        return vals
        
    def action_cancel(self):
        self.state = "cancel"

    def action_draft(self):
        self.state = "draft"

    def unlink(self):
        if self.state == 'submit':
            raise ValidationError(_("You Cannot Delete %s as it is in %s State" % (self.name, self.state)))
        return super().unlink()

    def remove(self):
        if self.state not in ['draft', 'cancel']:
            raise ValidationError(_("You Cannot Delete %s as it is in %s State" % (self.name, (self.state))))
        return super().remove()

    def _count_mo(self):
        for rec in self:
            rec.count_mo = rec.env['mrp.production'].sudo().search_count([('peel_diss_assy_id', '=', rec.id)])

    def action_see_mo(self):
        list_domain = []
        if 'active_id' in self.env.context:
            list_domain.append(('peel_diss_assy_id', '=', self.env.context['active_id']))
        
        return {
            'name':_('Manufacturing Order'),
            'domain':list_domain,
            'res_model':'mrp.production',
            'view_mode':'tree,form',
            'type':'ir.actions.act_window',
        }

    def create_mo(self):
        for rec in self:
            for line in rec.peel_diss_assy_line:
                new_mo = {
                    "product_id": line.product_id.id,
                    "bom_id": line.bom_id.id,
                    "product_qty": line.bom_id.product_qty,
                    "product_uom_id": line.bom_id.product_uom_id.id,
                    "company_id": self.env.company.id,
                    "peel_diss_assy_id": rec.id,
                    "move_raw_ids": []
                }
                for c in line.peel_diss_assy_component_line:
                    new_mo['move_raw_ids'].append([0,0, {
                        "product_id": c.product_id.id,
                        "product_uom": c.product_id.uom_id.id,
                        "product_uom_qty": c.peeled_total,
                        "name": "New",
                        "location_id": self.env['mrp.production'].sudo()._get_default_location_src_id(),
                        "location_dest_id": c.product_id.with_context(force_company=self.company_id.id).property_stock_production.id
                    }])

                if new_mo:
                    self.env['mrp.production'].sudo().create(new_mo)
                    self._count_mo()
                    


class PeelDissAssyLine(models.Model):
    _name = "peel.diss.assy.line"
    _description = "Detail Job of Peel Diss Assy"

    peel_diss_assy_id = fields.Many2one(
        'peel.diss.assy', 
        'Peel Diss Assy Line ID', 
        ondelete='cascade', 
        index=True
    )
    user = fields.Many2one('employee.custom', string='Operator', required=True, domain=_get_domain_user)
    product_id = fields.Many2one('product.product', string='Produk', required=True)
    bom_id = fields.Many2one(
        'mrp.bom', 
        string='BOM', 
        readonly=True, 
        compute='_fetch_component_from_bom', 
        store=True
    )
    description = fields.Text(string="Description")
    peel_diss_assy_component_line = fields.One2many(
        'peel.diss.assy.component.line', 
        'peel_diss_assy_line_id', 
        'Peel Diss Assy Componen Line',
        compute="_fetch_component_from_bom",
        store=True,
        readonly=False
    )

    @api.onchange('product_id')
    def _fetch_component_from_bom(self):
        # reset lines to null
        self.peel_diss_assy_component_line = [(5,0,0)]
        list_component = []

        for rec in self:
            if rec.product_id:
                bom = self.env['mrp.bom'].sudo().search([('product_tmpl_id', '=', rec.product_id.product_tmpl_id.id)])
                if bom:
                    rec.update({'bom_id': bom.id})
                    for component in bom.bom_line_ids:
                        list_component.append([0,0,{
                            'product_id': component.product_id.id,
                            'peel_diss_assy_line_id': rec.id
                        }])
       
        self.peel_diss_assy_component_line =  list_component


class PeelDissAssyComponentLine(models.Model):
    _name = "peel.diss.assy.component.line"
    _description = "Compoent Kupas Diss Assy"
    
    peel_diss_assy_line_id = fields.Many2one(
        'peel.diss.assy.line', 
        string='Peel Diss Assy Line ID', 
        ondelete="cascade", 
        index=True
    )
    product_id = fields.Many2one('product.product', string='Component', required=True, readonly=True, store=True)
    peeled_total = fields.Float(string="Total yang dikupas")
    ok = fields.Float(string='OK', store=True)
    ng = fields.Float(string='NG', store=True)

    def write(self, vals):
        self._validate_ng_ok()
        return super(PeelDissAssyComponentLine, self).write(vals)

    @api.onchange('ok', 'ng')
    def _validate_ng_ok(self):
        """
        validate field ng + ok = peeled_total
        """
        for rec in self:
            if (rec.ok or 0) + (rec.ng or 0) > rec.peeled_total:
                raise ValidationError(_("Total OK + NG maximum must be %s " % (rec.peeled_total)))