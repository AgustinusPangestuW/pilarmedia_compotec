from odoo import models, fields, api, _
from odoo.exceptions import UserError

class InheritStockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    # code = fields.Selection(selection_add=[("subcon","Subcon Transfer")])
    is_subcon = fields.Boolean(string='Is Subcontracting Transfer')
    transit_location_id = fields.Many2one(
        comodel_name='stock.location',
        string='Transit Location'
        )
    operation_type_id = fields.Many2one('stock.picking.type', string='Next Operation Type')
    pricelist_id = fields.Many2one(
        comodel_name='pilar.pricelist',
        string='Pricelist'
        )
    master_sj = fields.Boolean(string='Master Surat Jalan')

class InheritStockPicking(models.Model):
    _inherit = 'stock.picking'

    master_sj = fields.Boolean(string='Master Surat Jalan')
    surat_jalan_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Surat Jalan',
        domain="[('master_sj', '=', True)]"
        )
    po_id = fields.Many2one(
        comodel_name='purchase.order',
        string='Purchase Order',
        domain="[('partner_id.name', 'ilike', 'acp')]"
        )
    vehicle_id = fields.Many2one('pilar.vehicles', string='Kendaraan')
    driver_id = fields.Many2one('pilar.driver', string='Driver')
    

    cek_master = fields.Boolean(compute='_compute_master', string='Master DO', store=False)
    cek_subcon = fields.Boolean(compute='_compute_master', string='Subcon', store=False)
    subkon_id = fields.Many2one(comodel_name='res.partner',compute='_compute_company', string='Company Id', store=False)
    
    @api.depends('picking_type_id')
    def _compute_master(self):
        for doc in self:
            mas = doc.picking_type_id.master_sj 
            sub = doc.picking_type_id.is_subcon
            doc.cek_master = mas
            doc.cek_subcon = sub
    
    @api.depends('vehicle_id')
    def _compute_company(self):
        for doc in self:
            com = doc.vehicle_id.pemilik_id
            doc.subkon_id = com
    
    
class InheritMrpProduction(models.Model):
    _inherit = 'mrp.production'

    surat_jalan_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Surat Jalan',
        domain="[('picking_type_id.master_sj', '=', True)]"
        )

class NamaModel(models.Model):
    _inherit = 'stock.location'

    nama_warehouse = fields.Char(string='Nama Warehouse',compute='_compute_warehouse')
    
    def _compute_warehouse(self):
        def get_warehouse(location:object):
            parent_loc = location.location_id

            wrh_in_currenct_loc = self.env['stock.warehouse'].sudo().search([('view_location_id', '=', location.id)])
            if wrh_in_currenct_loc:
                return wrh_in_currenct_loc
            
            if parent_loc:
                wrh_in_parent_loc = self.env['stock.warehouse'].sudo().search([('view_location_id', '=', parent_loc.id)])
                if wrh_in_parent_loc:
                    return wrh_in_parent_loc
                else:
                    self.get_warehouse(parent_loc)

            return ""
        
        for rec in self:
            rec.nama_warehouse = get_warehouse(rec)


    @api.depends('location_id')
    def _compute_company(self):
        for doc in self:
            com = doc.location_id.pemilik_id
            doc.subkon_id = com

class InheritProductTemplate(models.Model):
    _inherit = 'product.template'

    nama_alias = fields.Char(string='Nama Alias')


class InheritProductProduct(models.Model):
    _inherit = 'product.product'

    def name_get(self):
        res = []
        for rec in self:
            kedua = ''
            if rec.product_tmpl_id.nama_alias :
                kedua = ' - ' + rec.product_tmpl_id.nama_alias
            res.append((rec.id,'[%s] %s %s' % (rec.default_code,rec.product_tmpl_id.name, kedua )))
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if not args:
            args = []
        domain = args + ['|','|',('default_code',operator,name),('product_tmpl_id.name',operator,name),('nama_alias',operator,name)]
        res = super(InheritProductProduct, self).search(domain, limit=limit).name_get()
        return res
