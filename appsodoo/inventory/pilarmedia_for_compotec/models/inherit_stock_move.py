from odoo import models, fields, api, _
from odoo.exceptions import UserError

class inheritStockMove(models.Model):
    _inherit = 'stock.move'
    
    pricelist_subcons = fields.One2many(
        'pricelist.subcon.baseon.stockmove', 
        'move_id', 
        string='Pricelist subcon',
        store=True,
        copy=False
    )
    created_bill = fields.Boolean(string='Created Bill ?', copy=False)

    def write(self, vals):
        res = super().write(vals)
        self.create_pricelist_subcon()
        return res

    def create_pricelist_subcon(self):
        for rec in self:
            ps = self.env['pricelist.subcon.baseon.stockmove'].sudo().search([('move_id', '=', rec.id)])
            if not ps:
                ps = self.env['pricelist.subcon.baseon.stockmove'].sudo().create({
                    "product_id": rec.product_id.id,
                    "move_id": rec.id,
                    "price_total": 0, 
                    "qty_in_stock_move_line": rec.product_uom_qty,
                    "uom_in_stock_move_line": rec.product_uom.name,
                    "vendor": rec.picking_id.vendor.id or None,
                    "lines": []
                })  
                ps.get_qty_component_base_on_bom()
                ps.calculate_qty_total()

            if not rec.picking_id.surat_jalan_id:
                ps.lines = [(5,0,0)]

    def action_show_pricelist_subcon(self):
        self.ensure_one()
        view = self.env.ref('pilarmedia_for_compotec.pricelist_subcons_form')

        for rec in self:
            self.create_pricelist_subcon()
            ps = self.env['pricelist.subcon.baseon.stockmove'].sudo().search([('move_id', '=', rec.id)])
            ps = ps[0]

        return {
            'name': _('Pricelist Subcon'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'pricelist.subcon.baseon.stockmove',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': ps.id,
            'context': dict(
                self.env.context
            ),
        }