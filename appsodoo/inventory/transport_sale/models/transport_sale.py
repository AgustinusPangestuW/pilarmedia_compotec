from odoo import models, fields, api, _
from odoo.osv.osv import except_osv

class sale_order_fleet_vehicle(models.Model):
    _name = 'sale.order.fleet_vehicle'
    _description = 'All sales order and associated vehicles'

    sale_order_id = fields.Many2one('sale.order', string='Sale Order', ondelete='cascade', index=True)
    sales_date = fields.Date(string='Sales Date', compute="fetch_from_sale_order_id")
    partner_departure_id = fields.Many2one('res.partner', string='From', compute="fetch_from_sale_order_id")
    partner_destination_id = fields.Many2one('res.partner', string='To', compute="fetch_from_sale_order_id")
    delivery_date = fields.Date(string='Delivery Date', help="The date that will start to transport", compute="fetch_from_sale_order_id")
    return_date = fields.Date(string='Return Date', help="The expected date to finish all the transport", compute="fetch_from_sale_order_id")
    fleet_vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True, ondelete='restrict')
    license_plate = fields.Char(string='License Plate', size=64, required=False, store=True, compute="fetch_from_fleet_vehicle_id")
    internal_number = fields.Integer(string='Number', compute="fetch_from_fleet_vehicle_id")
    # employee_driver_id = fields.Many2one('hr.employee', string='Driver', required=True, ondelete='restrict', compute="fetch_from_fleet_vehicle_id")
    employee_driver_id = fields.Many2one('hr.employee', string='Driver', required=True, ondelete='restrict')
    employee_helper_id = fields.Many2one('hr.employee', string='Helper', required=True, ondelete='restrict')
    fleet_trailer_id = fields.Many2one('fleet.vehicle', string='Trailer', ondelete='restrict', required=True)
    trailer_license_plate = fields.Char(string='Tailer License Plate', size=64, required=False, store=True, 
        compute="onchange_fleet_trailer_id")
    cargo_ids = fields.One2many('sale.order.cargo', 'sale_order_fleet_id', 'Cargo', required=True, 
        help=_("All sale order transported cargo")) 
    
    @api.depends("fleet_trailer_id")
    def onchange_fleet_trailer_id(self):
        for rec in self:
            rec.trailer_license_plate = rec.fleet_trailer_id.license_plate if rec.fleet_trailer_id else None
    
    @api.depends('fleet_vehicle_id')
    def fetch_from_fleet_vehicle_id(self):                          
        for rec in self:
            rec.license_plate =  rec.fleet_vehicle_id.license_plate if rec.fleet_vehicle_id else None
            rec.internal_number = rec.fleet_vehicle_id.internal_number if rec.fleet_vehicle_id else None
            # di remark karena saat ini field driver_id ter-relasi dengan res.partner
            # rec.employee_driver_id = rec.fleet_vehicle_id.driver_id.id if rec.fleet_vehicle_id else None
        
    @api.depends('sale_order_id')
    def fetch_from_sale_order_id(self):
        for rec in self:
            rec.sales_date = rec.sale_order_id.date_order if rec.sale_order_id else None
            rec.partner_departure_id = rec.sale_order_id.partner_departure_id.id if rec.sale_order_id else None
            rec.partner_destination_id = rec.sale_order_id.partner_shipping_id.id if rec.sale_order_id else None
            rec.delivery_date = rec.sale_order_id.delivery_date if rec.sale_order_id else None
            rec.return_date = rec.sale_order_id.return_date if rec.sale_order_id else None

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        sale_order_id = self.env.context.get('sale_order_id')
        if sale_order_id:
            res['sale_order_id'] = sale_order_id

        return res
    
#     def copy(self, cr, uid, _id, default=None, context=None):
        
#         if not default:
#             default = {}
# #         default.update({            
# #             'state': 'draft',            
# #         })
#         return super(sale_order_fleet_vehicle, self).copy(cr, uid, _id, default, context=context)
        
        
#     _sql_constraints = [('vehicle_uniq', 'unique(fleet_vehicle_id,sale_order_id)',
#                          'Vehicle must be unique per sale order! Remove the duplicate vehicle'),
#                         ('employee_unique','unique(employee_driver_id,sale_order_id)',
#                          'A driver must be unique per sale order! Remove the duplicate driver'),]  
         

class EmployeeTransportCommission(models.Model):
    _name = "employee.transport.commission"

    READONLY_STATES = {
        'submit': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    sale_order_id = fields.Many2one('sale.order', string='Sale Order', ondelete='cascade', index=True, required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, ondelete='restrict', states=READONLY_STATES)
    qty = fields.Float(string='Transport Quantity', compute="get_total_qty_transport", readonly=False, store=True, states=READONLY_STATES)
    value = fields.Float(string='Commission Value', states=READONLY_STATES)
    state = fields.Selection([("draft","Draft"),("confirm","Confirmed")], string='State', default="draft", readonly=True)
    payment_ref = fields.Char(string='Payment Ref', states=READONLY_STATES)
    payment_date = fields.Date(string='Payment Date', states=READONLY_STATES)

    @api.depends('employee_id')
    def get_total_qty_transport(self):
        for rec in self:
            rec.qty = len([i.id for i in rec.sale_order_id.cargo_ids if i.sale_order_fleet_id.employee_driver_id == rec.employee_id])


class sale_order_cargo(models.Model):
    _name = 'sale.order.cargo'
    _description = 'Transport cargo from a sale order transport service'

    sale_order_fleet_id = fields.Many2one('sale.order.fleet_vehicle', string='Sale Order Vehicle', ondelete='cascade', 
        required=True, readonly=True, index=True)
    transport_date = fields.Date(string='Transport Date', required=True, 
        help=_('The day when the product was transported.'))
    cargo_product_id = fields.Many2one('product.product', string='Cargo', required=True)
    cargo_docport = fields.Char(string='Port Document', size=64, required=False, readonly=False, 
        help=_('Associated port document of the transported product if applicable.'))
    brand = fields.Char(string='Brand', size=64, required=False, readonly=False, 
        help=_('Brand of the transported product if applicable.'))
    model = fields.Char(string='Model', size=64, required=False, readonly=False, 
         help=_('Model of the transported product if applicable.'))
    cargo_ident = fields.Char(string='Identification', size=64, required=False, readonly=False, 
        help=_('Identification of the cargo.Ex:Id,License Plate,Chassi'))
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', required=True)
    transport_from_id = fields.Many2one('res.partner', string='From')
    transport_to_id = fields.Many2one('res.partner', string='To')

    @api.onchange('cargo_product_id')             
    def product_change(self):
        for rec in self:
            rec.sale_order_id = rec._context.get('sale_order_id') or rec.sale_order_fleet_id.sale_order_id.id or None
        
#         result={}      
#         if not cargo_product_id:
#             return {'value':result}
                        
#         sale_order = self.pool.get('sale.order').browse(cr,uid,context.get('sale_order_id')) 
        
#         if sale_order:
#             result['sale_order_id'] = context.get('sale_order_id')
            
# #             if [ product sale_order_fleet_idfor product in sale_order.order_line if cargo_product_id == product.product_id]:            
    
#         return {'value':result}
    
#     def copy(self, cr, uid, _id, default=None, context=None): 
        
#         if not default:
#             default = {}
# #         default.update({
# #         })
        
#         res_id = super(sale_order_cargo, self).copy(cr, uid, _id, default, context)
#         return res_id 
             

class sale_order(models.Model):
    _inherit = 'sale.order'

    fleet_vehicles_ids = fields.One2many('sale.order.fleet_vehicle', 'sale_order_id', 'Transport Vehicles', 
        required=True, index=True)
    partner_departure_id = fields.Many2one('res.partner', string='From', required=True)
    delivery_date = fields.Date(string='Transport Date', required=True, help=_('Expected Transport start date.'))
    return_date = fields.Date(string='Transport Finish', required=True, help=_('Expected Transport finish date.'))
    cargo_ids = fields.One2many('sale.order.cargo', 'sale_order_id', 'Cargo Manifest', required=False)
    employee_commission_ids = fields.One2many('employee.transport.commission', 'sale_order_id', 'Employee Transport Commission', required=False)
   
    def action_confirm_emp_commission(self):
        for rec in self:
            for c in rec.employee_commission_ids:
                c.state = "confirm"

    def _validate_data(self, cr, uid, ids):
        for dates in self.browse(cr,uid,ids):
            if dates.return_date < dates.delivery_date:
                return False            
            else:
                return True
    #TODO : check condition and return boolean accordingly
    
    def _validate_cargo_products(self,cr,uid,ids):
        
        result = True
        cargo_products_ids = []
        
        sale_order = self.browse(cr,uid,ids[0])
        
        if sale_order:            
            cargo_products_ids = [cargo.cargo_product_id.id for cargo in sale_order.cargo_ids]
            
            if not cargo_products_ids:
                result = True
            else:                
                line_products_ids = [line.product_id.id for line in sale_order.order_line]
                result = set(cargo_products_ids) == set(line_products_ids)
                            
        return result
    
    def _validate_cargo_products_qty(self,cr,uid,ids):
        
        result = True
        msg_format=""
        line_product_ids = []
        line_product_qts = []
        
        sale_order = self.browse(cr,uid,ids[0])
        
        if sale_order:            
            cargo_product_ids = [cargo.cargo_product_id.id for cargo in sale_order.cargo_ids]
            
            #give all products for order line
            line_product_ids = [line.product_id.id for line in sale_order.order_line]
            line_product_qts = [line.product_uom_qty for line in sale_order.order_line]
            
            line_product_ids_qts = {}
            line_product_dif_ids = {}
            
            for idx,prod_id in enumerate(line_product_ids):                
                if prod_id in line_product_ids_qts.keys():
                    line_product_ids_qts[prod_id]+= line_product_qts[idx]
                else:
                    line_product_ids_qts[prod_id] = line_product_qts[idx]                            
                        
            if not cargo_product_ids:
                result = True
            else:
                for cargo_product_id in set(cargo_product_ids):                                    
                    line_product_ids_dict = { prod_id:qtd  for prod_id,qtd in line_product_ids_qts.iteritems() 
                                         if prod_id == cargo_product_id 
                                         and int(line_product_ids_qts[prod_id]) != cargo_product_ids.count(cargo_product_id)}  
                    
                    line_product_dif_ids.update(line_product_ids_dict)
                                                   
                if len(line_product_dif_ids) > 0:
                    
                    line_product_names = self.pool.get('product.product').name_get(cr,uid,line_product_dif_ids.keys(),context=None)
                    cargo_product_qts = [ cargo_product_ids.count(cargo_product_id) for cargo_product_id in line_product_dif_ids.keys()]
                    for product_name in line_product_names:
                        index= line_product_names.index(product_name)
                        
                        msg_format =  _("""Product:%s\n\tOrder=%s vs Cargo=%s\n""") % (product_name[1],
                                                                                       int(line_product_dif_ids[product_name[0]]),
                                                                                       cargo_product_qts[index])
                                                             
                    message = _("""The following products quantities in cargo don't match\n quantities in sales order line:\n%s
                                    """) % (msg_format)
                        
                    raise except_osv(_('Error'), message)
                    result = False
                else:
                    result = True
        return result
    
    _constraints = [(_validate_data,'Error: Invalid return date', ['delivery_date','return_date']),
                    (_validate_cargo_products,"Error: There is a cargo product that doesn't belongs to the sale order line!",['cargo_ids','order_line']),
                    (_validate_cargo_products_qty,"Error: In products quantities",['cargo_ids','order_line'])]

 
class fleet_vehicle(models.Model):
    _inherit = 'fleet.vehicle' 

    sales_order_ids = fields.One2many('sale.order.fleet_vehicle', 'fleet_vehicle_id', 'Vehicle Sales', 
        index=True, ondelete='cascade')
    internal_number = fields.Integer(string='Internal Number')
    is_trailer = fields.Boolean(string='Is Trailer', required=False)

 
class hr_employee_driver_sales(models.Model):
    _inherit = 'hr.employee' 

    sales_order_ids = fields.One2many('sale.order.fleet_vehicle', 'employee_driver_id', 'Driver Sales', 
        ondelete='cascade', index=True)
    is_driver = fields.Boolean(string='Is Driver', required=False)