import json, copy
from xml.dom import ValidationErr
from odoo import http, _
from odoo.http import request
from .api import RequestError, ApiController
from odoo.exceptions import ValidationError


class APIStockInventory(http.Controller):
    def mapping_stock_inventory(self, si:object, ret_stock_inventory_lines=False):
        res = []
        model_obj = request.env['stock.inventory']
        # model_loc_obj = request.env['stock.location']
        # model_prod_obj = request.env['product.product']
        for i in si:
            temp_res = i.read(list(set(model_obj._fields)))

            if ret_stock_inventory_lines:
                stock_inventory_lines = self.mapping_stock_inventory_lines(i.line_ids)
                temp_res[0].update({'line_ids': stock_inventory_lines})
            
            # temp_res[0].update({'location_ids': [l.read(list(set(model_loc_obj._fields)))[0] for l in i.location_ids]})
            # temp_res[0].update({'product_ids': [p.read(list(set(model_prod_obj._fields)))[0] for p in i.product_ids]})
            res.append(temp_res[0])
        
        return res

    def mapping_stock_inventory_lines(self, stock_inventory_lines:object):
        res = []
        model_obj = request.env['stock.inventory.line']
        for i in stock_inventory_lines:
            res.append(i.read(list(set(model_obj._fields)))[0])
        
        return res

    @http.route(['/stockopname/create/'], type="json", auth="public", method="POST", csrf=False)
    def create(self, warehouse_ids, **kwargs):
        """
        REST API POST for create table `stock.inventory` 
        """
        request.env.cr.savepoint()
        try:
            required_field = ['name']
            start_inventory = False

            if warehouse_ids:
                location_ids = ApiController().get_location_base_on_warehouses(warehouse_ids)
                kwargs['location_ids'] = location_ids

            if kwargs.get('start_inventory'):
                start_inventory = True
                del kwargs['start_inventory']

            res = ApiController().create_document('stock.inventory', required_field, kwargs)
            if start_inventory: 
                for rec in res:
                    rec.action_start()
            stock_inventory = self.mapping_stock_inventory(res)
            if len(stock_inventory) > 0: stock_inventory = stock_inventory[0]
            request.env.cr.commit()            

            if kwargs.get('location_ids'):
                kwargs['warehouse_ids'] = warehouse_ids
                del kwargs['location_ids']

            return ApiController().response_sucess(stock_inventory, kwargs, "/stockopname/create")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, kwargs, "/stockopname/create")

    @http.route(['/stockopname/startinventory'], type="json", auth="public", method="POST", csrf=False)
    def validate_inventory(self, ids):
        """
        validate `stock.inventory` startinventory
        """
        request.env.cr.savepoint()
        try:
            si_success = []
            model = request.env['stock.inventory']
            for i in ids:
                inv = model.sudo().search([('id', '=', i)])
                inv.action_start()
                si_success.append(self.mapping_stock_inventory(inv))
            request.env.cr.commit()

            return ApiController().response_sucess(si_success, ids, "/stockopname/startinventory")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, ids, "/stockopname/startinventory")

    @http.route(['/stockopname/validate'], type="json", auth="public", method="POST", csrf=False)
    def validate_inventory(self, ids):
        """
        validate `stock.inventory`
        """
        request.env.cr.savepoint()
        try:
            si_success = []
            model = request.env['stock.inventory']
            for i in ids:
                inv = model.sudo().search([('id', '=', i)])
                inv.action_validate()
                si_success.append(self.mapping_stock_inventory(inv))
            request.env.cr.commit()

            return ApiController().response_sucess(si_success, ids, "/stockopname/validate")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, ids, "/stockopname/validate")

    @http.route(['/stockopname/startinventory'], type="json", auth="public", method="POST", csrf=False)
    def validate_inventory(self, ids):
        """
        validate `stock.inventory` start
        """
        request.env.cr.savepoint()
        try:
            si_success = []
            model = request.env['stock.inventory']
            for i in ids:
                inv = model.sudo().search([('id', '=', i)])
                inv.action_start()
                si_success.append(self.mapping_stock_inventory(inv))
            request.env.cr.commit()

            return ApiController().response_sucess(si_success, ids, "/stockopname/startinventory")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, ids, "/stockopname/startinventory")

    @http.route(['/stockopname/delete'], type="json", auth="public", method="POST", csrf=False)
    def delete_stock_inventory(self, ids):
        """
        delete `stock.inventory`
        """
        request.env.cr.savepoint()
        try:
            si_success = []
            model = request.env['stock.inventory']
            for i in ids:
                res = model.sudo().search([('id', '=', i)]).unlink()
                si_success.append({'id': i, 'succes': res})
            request.env.cr.commit()

            return ApiController().response_sucess(si_success, ids, "/stockopname/delete")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, ids, "/stockopname/delete")

    @http.route(['/stockopname/cancel'], type="json", auth="public", method="POST", csrf=False)
    def cancel_stock_inventory(self, ids):
        """
        cancel `stock.inventory`
        """
        request.env.cr.savepoint()
        try:
            si_success = []
            model = request.env['stock.inventory']
            for i in ids:
                res = model.sudo().search([('id', '=', i)]).action_cancel_draft()
                si_success.append({'id': i, 'succes': res})
            request.env.cr.commit()

            return ApiController().response_sucess(si_success, ids, "/stockopname/cancel")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, ids, "/stockopname/cancel")

    @http.route(['/stockopname/'], type="json", auth="public", method="GET", csrf=False)
    def getStockOpname(self, **kwargs):
        """
        REST API GET for table `stock.inventory`

        parameters:
        -----------
        kwargs['search']: list of list
            ex: [['id', '=', '1']]
        """
        try:
            limit = kwargs.get('limit') or None
            offset = kwargs.get('offset') or 0
            ret_lines = kwargs.get('ret_lines') or False
            res = request.env['stock.inventory'].sudo().search(kwargs.get('search') or [], offset=offset, limit=limit)
            stock_inventorys = self.mapping_stock_inventory(res, ret_stock_inventory_lines=ret_lines)
            return ApiController().response_sucess(stock_inventorys, kwargs, "/stockopname/get")
        except Exception as e:
            return ApiController().response_failed(e, kwargs, "/stockopname/get")

    @http.route(['/stockopname/inv'], type="json", auth="public", method="GET", csrf=False)
    def getInventory(self, **kwargs):
        """
        REST API GET for table `stock.inventory.line`

        parameters:
        -----------
        kwargs['search']: list of list
            ex: [['id', '=', '1']]
        """
        try:
            limit = kwargs.get('limit') or None
            offset = kwargs.get('offset') or 0
            # DEFAULT search
            kwargs['search'] += [["location_id.usage", "in", ["internal", "transit"]]]
            res = request.env['stock.inventory.line'].sudo().search(kwargs.get('search') or [], offset=offset, limit=limit)
            stock_inventorys = self.mapping_stock_inventory_lines(res)
            return ApiController().response_sucess(stock_inventorys, kwargs, "/stockopname/inv")
        except Exception as e:
            return str(e)

    @http.route(['/stockopname/inv/create/'], type="json", auth="public", method="POST", csrf=False)
    def create_inventory(self, new_items):
        """
        REST API POST for create table `stock.inventory.line` 
        """
        def validate_location(location_ids:object):
            list_id_location = [str(loc.id) for loc in location_ids]

            # validate location must be in location_ids in table stock_inventory
            if str(d['location_id']) not in list_id_location:
                raise ValidationError(_("location [%s] must be in location_ids in stock inventory [%s].") % (
                    d['location_id'], ", ".join(list_id_location)
                ))

        def check_state(inventory:object):
            if inventory.state != "confirm":
                raise ValidationError(_("change value only can in state confirm (In progress), current document state is %s. " % (
                    inventory.state
                )))

        def validate_require_field(required_field:list, row:object):
            # validation required field 
            for r in required_field:
                if r not in row:
                    raise ValidationError(_("%s need in parameter create") % (", ".join(required_field)))

        request.env.cr.savepoint()
        try:
            inv_success = []
            model = request.env['stock.inventory.line']
            required_field = ['inventory_id', 'product_id', 'location_id']
            for d in new_items:
                validate_require_field(required_field, d)
                inventory = request.env['stock.inventory'].sudo().search([('id', '=', d['inventory_id'])])
                validate_location(inventory.location_ids)
                check_state(inventory)

                if 'prod_lot_id' not in d:
                    d['prod_lot_id'] = request.env['stock.production.lot'].create({
                        'product_id': d['product_id'],
                        'company_id': inventory.company_id.id
                    })['id']

                inv = model.sudo().create(d)
                inv_success.append(self.mapping_stock_inventory_lines(inv))
            request.env.cr.commit()       

            return ApiController().response_sucess(inv_success, new_items, "/stockopname/inv/create")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, new_items, "/stockopname/inv/create")

    @http.route(['/stockopname/inv/update'], type="json", auth="public", method="POST", csrf=False)
    def update_inventory(self, updates):
        """
        REST API POST for update table `stock.inventory.line` 
        """
        request.env.cr.savepoint()
        try:
            inv_success = []
            model = request.env['stock.inventory.line']
            for d in updates:
                if 'new_qty' not in d and 'id' not in d:
                    raise ValidationError(_("new qty and id need in parameter updates"))
                else:
                    inv = model.sudo().search([('id', '=', d['id'])])
                    inv.product_qty = d['new_qty']
                    inv_success.append(self.mapping_stock_inventory_lines(inv))
            request.env.cr.commit()       

            return ApiController().response_sucess(inv_success, updates, "/stockopname/inv/update")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, updates, "/stockopname/inv/update")

    @http.route(["/stockopname/inv/refreshqty/"], type="json", auth="public", method="POST", csrf=False)
    def refreshqty_inventory(self, ids, inventory_ids):
        """
        REST API POST for refresh qty pada table `stock.inventory.line`
        """
        def check_exist_data(inv:object):
            if not inv:
                raise ValidationError(_("stock inventory line with id %s is does not exist. " % (d)))
                
        def check_state(inv:object):
            if inv.state != "confirm":
                raise ValidationError(_("only can delete in state confirm (In Progress)"))

        def get_id_from_stock_inventory(inventory_ids:list):
            """ get ids (stock inventory line) base on stock inventory
            
            parameter:
            ----------
            inventory_ids : list of integer
                ex: [1,4,55]

            return:
            -------
            ids : list
            """
            ids = []
            for i in inventory_ids:
                si = request.env['stock.inventory'].sudo().search([('id', '=', i)])
                ids += [l.id for l in si.line_ids]

            return ids

        request.env.cr.savepoint()
        try:
            inv_success = []
            model = request.env['stock.inventory.line']
            ids += get_id_from_stock_inventory(inventory_ids)
            for d in ids:
                inv = model.sudo().search([('id', '=', d)])
                check_exist_data(inv)            
                check_state(inv)    
                inv.action_refresh_quantity()
                inv_success.append(self.mapping_stock_inventory_lines(inv))
            request.env.cr.commit()

            return ApiController().response_sucess(inv_success, ids, "/stockopname/inv/remove")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, ids, "/stockopname/inv/remove")

    @http.route(["/stockopname/inv/remove/"], type="json", auth="public", method="POST", csrf=False)
    def remove_inventory(self, ids):
        """
        REST API POST for remove qty pada table `stock.inventory.line`
        """
        def check_exist_data(inv:object):
            if not inv:
                raise ValidationError(_("stock inventory line with id %s is does not exist. " % (d)))
                
        def check_state(inv:object):
            if inv.state != "confirm":
                raise ValidationError(_("only can delete in state confirm (In Progress)"))

        request.env.cr.savepoint()
        try:
            inv_success = []
            model = request.env['stock.inventory.line']
            for d in ids:
                inv = model.sudo().search([('id', '=', d)])
                check_exist_data(inv)            
                check_state(inv)    
                res_del = inv.unlink()
                inv_success.append({'id': d, 'success': res_del})
            request.env.cr.commit()       

            return ApiController().response_sucess(inv_success, ids, "/stockopname/inv/remove")
        except Exception as e:
            request.env.cr.rollback()
            return ApiController().response_failed(e, ids, "/stockopname/inv/remove")

    