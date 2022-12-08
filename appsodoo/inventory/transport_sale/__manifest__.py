# Copyright 2022 Pilarmedia Indonesia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Transport Sale",
    "version": "13.0.1.0.0",
    "category": "Stock",
    "website": "www.solog.co.id",
    "author": "Pilarmedia Indonesia (SOLOG)",
    "license": "AGPL-3",
    "depends": ["stock", "hr", "fleet", "sale"],
    "installable": True,
    "data": [
        "security/ir.model.access.csv",
        "views/transport_sale.xml"],
    "maintainers": ["victoralmau"],
}
