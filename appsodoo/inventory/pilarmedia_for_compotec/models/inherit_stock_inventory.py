from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.misc import OrderedSet

class InheritStockInventory(models.Model):
    _inherit = 'stock.inventory'

    group_by = fields.Selection([
        ("product","Product"),
        ("product_category","Product Category")], string='Group by')
    show_product_with_non_stock = fields.Boolean(string='Show product with non-stock ?')
    product_category_ids = fields.Many2many(
        comodel_name='product.category', 
        string='Product Categories'
    )
    adj_with_value = fields.Boolean(string='Adjust with value ?')

    def fetch_all_location(self):
        for rec in self:
            locations = self.env['stock.location'].sudo().search([
                    ('company_id', '=', rec.company_id.id), 
                    ('usage', 'in', ['internal', 'transit']
                )])
            rec.location_ids = [(4, l.id) for l in locations]
        return self

    def remove_all_location(self):
        for rec in self:
            rec.location_ids = [(6,0,[])]
        return self

    def fetch_all_product(self):
        for rec in self:
            products = self.env['product.product'].sudo().search([
                    ('active', '=', 1),
                    ('type', '=', 'product'), 
                    '|',
                    ('company_id', '=', False), 
                    ('company_id', '=', rec.company_id.id)
                ])
            rec.product_ids = [(4, p.id) for p in products]

        return self

    def remove_all_product(self):
        for rec in self:
            rec.product_ids = [(6,0,[])]
        return self

    def _action_start(self):
        res = super()._action_start()
        
        for rec in self:
            products = rec.product_ids if rec.product_ids else \
                self.env['product.product'].sudo().search([
                    ('active', '=', 1),
                    ('type', '=', 'product'), 
                    ('company_id', '=', rec.company_id.id)
                ])
            locations = rec.location_ids if rec.location_ids else\
                self.env['stock.location'].sudo().search([
                    ('company_id', '=', rec.company_id.id), 
                    ('usage', 'in', ['internal', 'transit']
                )])

            if rec.show_product_with_non_stock:
                for p in products:
                    for l in locations:
                        stock_inventory_line = self.env['stock.inventory.line'].sudo().search([
                            ('inventory_id', '=', rec.id),
                            ('product_id', '=', p.id), 
                            ('location_id', '=', l.id), 
                            ('company_id', '=', rec.company_id.id)])
                        
                        if not stock_inventory_line:
                            lot_id = None 
                            if p.auto_create_lot:
                                lot_id = self.env['stock.production.lot'].create({
                                    'product_id': p.id,
                                    'company_id': rec.company_id.id
                                })
                            self.env['stock.inventory.line'].sudo().create({
                                'inventory_id': rec.id,
                                'product_id': p.id,
                                'location_id': l.id,
                                'company_id': rec.company_id.id,
                                'product_qty': 0,
                                'theoretical_qty': 0, 
                                'product_uom_id': p.uom_id.id,
                                'prod_lot_id': lot_id.id
                            })

        return res

    def _get_inventory_lines_values(self):
        # TDE CLEANME: is sql really necessary ? I don't think so
        locations = self.env['stock.location']
        if self.location_ids:
            locations = self.env['stock.location'].search([('id', 'child_of', self.location_ids.ids)])
        else:
            locations = self.env['stock.location'].search([('company_id', '=', self.company_id.id), ('usage', 'in', ['internal', 'transit'])])
        domain = ' sq.location_id in %s AND sq.quantity != 0 AND pp.active'
        args = (tuple(locations.ids),)

        vals = []
        Product = self.env['product.product']

        # If inventory by company
        if self.company_id:
            domain += ' AND sq.company_id = %s'
            args += (self.company_id.id,)

        ### CUSTOM ###
        if self.group_by == "product" and self.product_ids:
            domain += ' AND sq.product_id in %s'
            args += (tuple(self.product_ids.ids),)

        if self.group_by == "product_category" and self.product_category_ids:
            domain += ' AND pp.categ_id in %s'
            args += (tuple(self.product_category_ids.ids),)
        ##############

        self.env['stock.quant'].flush(['company_id', 'product_id', 'quantity', 'location_id', 'lot_id', 'package_id', 'owner_id'])
        self.env['product.product'].flush(['active'])
        self.env.cr.execute("""SELECT sq.product_id, sum(sq.quantity) as product_qty, sq.location_id, sq.lot_id as prod_lot_id, sq.package_id, sq.owner_id as partner_id
            FROM stock_quant sq
            LEFT JOIN product_product pp
            ON pp.id = sq.product_id
            WHERE %s
            GROUP BY sq.product_id, sq.location_id, sq.lot_id, sq.package_id, sq.owner_id """ % domain, args)

        product_ids = OrderedSet()

        for product_data in self.env.cr.dictfetchall():
            product_data['company_id'] = self.company_id.id
            product_data['inventory_id'] = self.id
            # replace the None the dictionary by False, because falsy values are tested later on
            for void_field in [item[0] for item in product_data.items() if item[1] is None]:
                product_data[void_field] = False
            product_data['theoretical_qty'] = product_data['product_qty']
            if self.prefill_counted_quantity == 'zero':
                product_data['product_qty'] = 0
            if product_data['product_id']:
                product_ids.add(product_data['product_id'])
            vals.append(product_data)
        product_id_to_product = dict(zip(product_ids, self.env['product.product'].browse(product_ids)))
        for val in vals:
            if val.get('product_id'):
                val['product_uom_id'] = product_id_to_product[val['product_id']].product_tmpl_id.uom_id.id
        return vals
    