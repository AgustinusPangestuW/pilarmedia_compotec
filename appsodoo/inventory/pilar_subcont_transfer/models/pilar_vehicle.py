from odoo import models, fields, api

class PilarVehicles(models.Model):
    _name = 'pilar.vehicles'

    name = fields.Char(string='Plat Nomor')
    jenis_kendaraan = fields.Selection([("box","BOX"),("minibus","Minibus"),("pickup","Pick Up")], string='Jenis Kendaraan')
    pemilik_id = fields.Many2one('res.partner', string='Pemilik',domain="[('is_subcon', '=', True)]")

    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id,'%s - %s' % (rec.name,rec.pemilik_id.name)))
        return res

class PilarDriver(models.Model):
    _name = 'pilar.driver'

    name = fields.Char(string='Nama Driver')
    perusahaan_id = fields.Many2one('res.partner', string='Perusahaan',domain="[('is_subcon', '=', True)]")

class InheritResPartner(models.Model):
    _inherit = 'res.partner'

    is_subcon = fields.Boolean(string='Sub Contrator')

    