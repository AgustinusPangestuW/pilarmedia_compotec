# Copyright 2019 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class InventoryLine(models.Model):
    _inherit = "stock.inventory.line"

    currency_id = fields.Many2one(
        string="Currency", related="inventory_id.company_id.currency_id", readonly=True
    )

    def _compute_cost(self):
        for record in self:
            record.cost = (record.product_id.standard_price)

    cost = fields.Monetary(
        string="Cost", default=_compute_cost, store=True, readonly=False
    )
    adjustment_cost = fields.Monetary(
        string="Adjustment cost", compute="_compute_adjustment_cost", store=True
    )

    @api.depends("difference_qty", "inventory_id.state", "cost")
    def _compute_adjustment_cost(self):
        for record in self:
            record.adjustment_cost = (
                record.difference_qty * record.cost
            )


    def _get_move_values(self, qty, location_id, location_dest_id, out):
        self.ensure_one()

        res = super()._get_move_values(qty, location_id, location_dest_id, out)
        res['price_unit'] = self.cost or 0
        return res 