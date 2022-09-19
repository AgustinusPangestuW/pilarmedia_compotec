from odoo import models, fields, api

class PilarReagen(models.Model):
    _name = 'pilar.reagen'

    name = fields.Char(string='Nomor Reagen',default='New')
    tanggal = fields.Date(string='Tanggal', default=fields.Date.today())
    category_id = fields.Many2one('pilar.categ.reagen', string='Kategori Reagen')
    reagen_lines = fields.One2many(
        comodel_name='pilar.reagen.line',
        inverse_name='reagen_id',
        string='Detail',
        )
    klasifikasi = fields.Selection([("kwitansi","1.Kwitansi"),("catalog","2.e-Catalog"),("langsung","3.Pengadaan Langsung"),("tender","2.Tender")], string='Klasifikasi')
    state = fields.Selection([("draft","Draft"),("rencana","Perencanaan"),
        ("ver","Verifikasi"),("klasifikasi","Klasifikasi"),("setuju","Persetujuan"),("lelang","Pengadaan")], string='Status',default='draft')
    nomor_rka = fields.Char(string='Kode RKA-KL')
    
    @api.model
    def create(self, vals):
        obj = super(PilarReagen, self).create(vals)
        if obj.name == 'New':
            number = self.env['ir.sequence'].get('nomor.pengajuan') or 'New'
            obj.write({'name': number})
        return obj

    def set_validate(self):
        for doc in self:
            doc.state = 'rencana'
    
    def set_draft(self):
        for doc in self:
            doc.state = 'draft'

    def set_ver(self):
        for doc in self:
            doc.state = 'ver'
    
    def set_klas(self):
        for doc in self:
            doc.state = 'klasifikasi'

    def set_setuju(self):
        for doc in self:
            doc.state = 'setuju'

    def set_lelang(self):
        for doc in self:
            doc.state = 'lelang'
            order_lines = []
            for line in doc.reagen_lines:
                order_lines.append((0, 0, {
                    'product_id': line.name.id,
                    'product_qty': line.jumlah,
                    'product_uom_id': line.satuan_id.id,
                    }))

            lines_dict = {
                'type_id': 3,
                'origin': doc.name,
                'line_ids': order_lines,
            }
            self.env['purchase.requisition'].create(lines_dict)

class PilarCategReagen(models.Model):
    _name = 'pilar.categ.reagen'

    name = fields.Char(string='Kategori',required=True)
    deskripsi = fields.Text(string='Deskripsi')

class PilarReagenLine(models.Model):
    _name = 'pilar.reagen.line'

    name = fields.Many2one('product.product', string='Nama')
    merk = fields.Char(string='Merk')
    spesifikasi = fields.Char(string='Spesifikasi')
    no_katalog = fields.Char(string='No. Katalog')
    jumlah = fields.Float(string='Jml Kebutuhan')
    satuan_id = fields.Many2one('uom.uom', string='Satuan')
    keterangan = fields.Char(string='Keterangan')
    reagen_id = fields.Many2one('pilar.reagen', string='Reagen')


