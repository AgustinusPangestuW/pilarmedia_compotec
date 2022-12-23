from odoo import models, fields, api, _

class ItemCatalogCategory(models.Model):
    _name = 'catalog.category'
    _description = "Catalog Category"

    name = fields.Char(string='Name')

    _sql_constraints = [
        ('unique_name_catalog_category', 'unique(name)', 'Catalog category must be unique!'),
    ]


class ItemCatalog(models.Model):
    _name = 'item.catalog'
    _description = "Item Catalog"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', copy=False)
    description = fields.Text(string='Description')
    price = fields.Float(string='Price', readonly=True)
    tender_date = fields.Date(string='Tender Date', readonly=1)
    tender_id = fields.Char(string='Tender ID', readonly=1)
    tender_name = fields.Char(string='Tender', readonly=1)
    category_id = fields.Many2one('catalog.category', string='Category')

    def get_current_supplier(self):
        partner_id = self.env.user.partner_id
        return partner_id.id if partner_id.is_supplier else ""

    supplier_id = fields.Many2one('res.partner', string='Supplier', required=True, 
        default=get_current_supplier, readonly=1)

    _sql_constraints = [
        ('unique_name_catalog_supplier', 'unique(name, supplier_id)', 'Catalog must be unique per Supplier!'),
    ]

    def name_get(self):
        new_res = []
        for rec in self:
            name = ("%s - %s" % (rec.name, rec.description)) if rec.description else ""
            if rec.price:
                name += " [%s] " % ("{:,}".format(rec.price))
            new_res.append((rec.id, name))

        return new_res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if not args:
            args = []
        domain = args + [('description',operator,name)]
        res = super().search(domain, limit=limit).name_get()
        return res

