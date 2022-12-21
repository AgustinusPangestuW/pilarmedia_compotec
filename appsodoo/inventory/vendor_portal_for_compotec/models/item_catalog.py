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
        default=get_current_supplier, readonly=0)

    _sql_constraints = [
        ('unique_name_catalog_supplier', 'unique(name, supplier_id)', 'Catalog must be unique per Supplier!'),
    ]