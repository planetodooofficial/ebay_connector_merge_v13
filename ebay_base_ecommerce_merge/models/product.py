from odoo import api, fields, models, _
from odoo.exceptions import UserError
import base64
import datetime
import math
import os
import time
import urllib


def get_allocation():
    return True


class ebay_product_listing(models.Model):
    _name = 'ebay.product.listing'

    # @api.model
    # def write(self, vals):
    #     '''
    #     Inherit write
    #     parameters:
    #         vals :- Dictionary of Listing Data
    #     '''
    #     # context = self._context.copy()
    #     if vals.get('price'):
    #         vals.update({'price_change': True})
    #     if vals.get('int_qnt'):
    #         vals.update({'stock_change': True})
    #     return super(ebay_product_listing, self).write(vals)

    def relist_item(self):
        """
        This function is used to Relist Item
        parameters:
            No Parameter
        """
        context = self._context.copy()
        shop_obj = self.env['sale.shop']
        (data,) = self
        if not data.shop_id:
            #            raise osv.except_osv(_('Warning'), _('Please Select Shop'))
            raise UserError(_('Please Select Shop'))

        if data.active_ebay:
            #            raise osv.except_osv(_('Warning'),_('Item is Active in odoo'))
            raise UserError(_('Item is Active in odoo'))

        shop_obj.verify_relist_item(data.shop_id.id, data.name)
        itemID = shop_obj.relist_item(data.shop_id.id, data.name)

        ebay_vals = {
            'name': itemID,
            'shop_id': data.shop_id.id,
            'type': data.type,
            'listing_duration': data.listing_duration,
            'ebay_start_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'ebay_end_time': False,
            'product_id': data.product_id.id,
            'active_ebay': True,
        }

        self.with_context(context).create(ebay_vals)
        data.write({'active_ebay': False})
        data.product_id.write({'ebay_inactive': False})
        return True

    name = fields.Char(string='Item ID', size=64)
    price_change = fields.Boolean('Price changed')
    stock_change = fields.Boolean('Stock changed')
    shop_id = fields.Many2one('sale.shop', string='eBay Shop', domain=[('ebay_shop', '=', True)])
    type = fields.Selection([('Chinese', 'Auction'),
                             ('PersonalOffer', 'PersonalOffer'),
                             ('FixedPriceItem', 'Fixed Price'),
                             ('StoresFixedPrice', 'Stores Fixed Price')], string='Type')
    listing_duration = fields.Selection([
        ('Days_1', '1 Days'),
        ('Days_3', '3 Days'),
        ('Days_5', '5 Days'),
        ('Days_7', '7 Days'),
        ('Days_10', '10 Days'),
        ('Days_30', '30 Days'),
        ('GTC', 'GTC'),
    ], string='Listing Duration')
    ebay_start_time = fields.Datetime(string='Start Time')
    ebay_end_time = fields.Datetime(string='End Time')
    last_sync_date = fields.Datetime(string='Last Sync Date')
    last_sync_stock = fields.Integer(string='Stock')
    price = fields.Float(string='Price')
    buy_it_now_price = fields.Float(string='BuyItNow Price')
    reverse_met = fields.Boolean(string='Reverse Met')
    active_ebay = fields.Boolean(string='Active', default=True)
    is_variant = fields.Boolean(string='Variant')
    ebay_title = fields.Char(string='eBay Title', size=264)
    sub_title = fields.Char(string='eBay Sub Title', size=264)
    ebay_sku = fields.Char(string='eBay SKU', size=264)
    condition = fields.Selection([
        ('1000', 'New'),
        ('1500', 'New other'),
        ('1750', 'New with defects'),
        ('2000', 'Manufacturer refurbished'),
        ('2500', 'Seller refurbished'),
        ('2750', 'Like New'),
        ('3000', 'Used'),
        ('4000', 'Very Good'),
        ('5000', 'Good'),
        ('6000', 'Acceptable'),
        ('7000', 'For parts or not working'),
    ], string='Condition')
    product_id = fields.Many2one('product.product', string='Product Name')

    _order = 'last_sync_date desc'

    def end_ebay_item(self):
        '''
        This function is used to create orders
        parameters:
            No Parameter
        '''
        context = self._context.copy()
        ebay_list_data = self
        connection_obj = self.env['ebayerp.osv']
        ebay_prod_list_obj = self.env['ebay.product.listing']
        sale_shop_obj = self.env['sale.shop']
        value = ''
        sku = ''
        var_dic = {}
        var_list = []
        if ebay_list_data.name.strip():
            ebay_data = sale_shop_obj.browse(ebay_list_data.shop_id.id)
            inst_lnk = ebay_data.instance_id

            siteid = ebay_data.instance_id.site_id.site
            if not ebay_list_data.is_variant:
                result = connection_obj.call(inst_lnk, 'EndItem', ebay_list_data.name.strip(), siteid)

                if result.get('long_message', False):
                    if result.get('long_message',
                                  False) == 'This item cannot be accessed because the listing has been deleted, is a Half.com listing, or you are not the seller.':
                        del_inactive_record = ebay_list_data.write({'active_ebay': False})

                if result.get('EndTime', False):
                    del_inactive_record = ebay_list_data.write({'active_ebay': False})

            else:
                result = connection_obj.call(inst_lnk, 'DeleteVariationItem', ebay_list_data.name.strip(),
                                             ebay_list_data.product_id.default_code)
                if result:
                    del_inactive_record = ebay_list_data.write({'active_ebay': False})
                else:
                    #                    raise osv.except_osv(_('Warning'),_('Failure For Ending Product'))
                    raise UserError(_('Failure For Ending Product'))

        return True

    @api.model
    def update_listing_cron(self):
        listing_data = self.search([])
        if listing_data:
            for ls in listing_data:
                ls.update_listing()

    def update_listing(self):
        if self.name and self.product_id.default_code:
            results = self.shop_id.import_ebay_product(self.name, self.product_id.default_code)

            result = results[0]
            if result:
                listing_vals = {
                    'last_sync_stock': int(result['Quantity']) - int(result.get('QuantitySold', 0)),
                    'price': result['ItemPrice'],
                }
                result_id = self.write(listing_vals)

                return result_id


class product_product(models.Model):
    _inherit = 'product.product'

    @api.model
    def copy(self, id, default=None):
        if not default:
            default = {}
        default.update({
            'default_code': False,
            'images_ids': False,
        })
        return super(product_product, self).copy(id, default)

    def get_main_image(self, id):
        if isinstance(id, list):
            id = id[0]
        images_ids = self.read(id, ['image_ids'])['image_ids']
        if images_ids:
            return images_ids[0]
        return False

    #    def _get_main_image(self, cr, uid, ids, field_name, arg, context=None):
    #        res = {}
    #        img_obj = self.pool.get('product.images')
    #        for id in ids:
    #            image_id = self.get_main_image(cr, uid, id, context=context)
    #            if image_id:
    #                image = img_obj.browse(cr, uid, image_id, context=context)
    #                res[id] = image.file
    #            else:
    #                res[id] = False
    #        return res

    def _get_main_image(self):
        img_obj = self.env['product.images']
        for id in self:
            image_id = self.get_main_image(id)
            if image_id:
                #                image = img_obj.browse(cr, uid, image_id, context=context)
                # image = image_id
                id.product_image = image_id.file
            else:
                id.product_image = False

    def get_allocation(self):
        context = self._context.copy()
        shop_obj = self.env['sale.shop']
        history_obj = self.env['product.allocation.history']
        prod_obj = self
        if prod_obj.qty_available > 0:
            s = {}
            for rec in prod_obj.prodlisting_ids:
                # if not s.has_key(rec.shop_id.id):
                if not rec.shop_id.id in s:
                    s.update({rec.shop_id.id: 1})
                else:
                    s.update({rec.shop_id.id: s[rec.shop_id.id] + 1})
            shop_ids = s.keys()
            for record in shop_obj.browse(shop_ids):
                if record.alloc_type == 'fixed':
                    value = math.floor(record.alloc_values[record.id])
                else:
                    value = math.floor(math.floor(prod_obj.qty_available * record.alloc_value / 100) / s[record.id])
                self._cr.execute(
                    'UPDATE ebay_product_listing set last_sync_stock = %s where product_id = %s and shop_id = %s'
                    , (value, self.ids[0], record.id))
                vals = {
                    'name': record.id,
                    'qty_allocate': value,
                    'date': datetime.datetime.now(),
                    'alloc_history_id': self[0].id,
                }
                history_obj.create(vals)

        res = super(product_product, self).get_allocation()
        return True

    def is_ebay_listing_availabe(self, id):
        if not self.browse(id).prodlisting_ids:
            return True
        active_ids = self.env['ebay.product.listing'].search([('product_id', '=', id), ('active_ebay', '=', True)])
        if active_ids:
            return True
        else:
            return False

    prodlisting_ids = fields.One2many('ebay.product.listing', 'product_id', string='Product Listing')
    ebay_category1 = fields.Many2one('product.attribute.set', string='Category')
    ebay_attribute_ids1 = fields.One2many('product.attribute.info', 'ebay_product_id1', string='Attributes')
    ebay_category2 = fields.Many2one('product.attribute.set', string='Category')
    ebay_attribute_ids2 = fields.One2many('product.attribute.info', 'ebay_product_id2', string='Attributes')
    ebay_exported = fields.Boolean(string='eBay Exported')
    ebay_category1 = fields.Many2one('product.attribute.set', string='Category')
    plcs_holds = fields.One2many('place.holder', 'plc_hld', string='Place Holder')
    ebay_prod_condition = fields.Char('Product Condition', size=64)
    store_cat_id1 = fields.Many2one('ebay.store.category', string='Product Category Store ID')
    store_cat_id2 = fields.Many2one('ebay.store.category', string='Product Category Store ID')
    image_ids = fields.One2many('product.images', 'product_id', string='Product Images')
    default_code = fields.Char(string='SKU', size=64, require='True')

    #    product_image = fields.Binary(compute='_get_main_image',  method=True)
    allocation_history_id = fields.One2many('product.allocation.history', 'alloc_history_id',
                                            string='Allocation History', readonly=True)


class product_allocation_history(models.Model):
    _name = 'product.allocation.history'

    date = fields.Datetime(string='Date of Allocation', readonly=True)
    name = fields.Many2one('sale.shop', string='Shop', readonly=True)
    alloc_history_id = fields.Many2one('product.product', string='Product')
    qty_allocate = fields.Float(string='Allocated Quantity', readonly=True)


class place_holder(models.Model):
    _name = 'place.holder'

    name = fields.Char(string='Name', size=50)
    value = fields.Text(string='Value')
    tmplate_field_id1 = fields.Many2one('ir.model.fields', 'Template Field', index=True,
                                        domain=[('model', '=', 'ebayerp.template')])
    product_field_id = fields.Many2one('ir.model.fields', 'Product Field', index=True,
                                       domain=['|', ('model', '=', 'product.product'),
                                               ('model', '=', 'product.template')])
    tmplate_field_id = fields.Many2one('ir.model.fields', 'Product Field', index=True,
                                       domain=['|', ('model', '=', 'product.product'),
                                               ('model', '=', 'product.template')])
    plc_hld = fields.Many2one('product.product', string='Place holder')
    plc_hld_temp = fields.Many2one('ebayerp.template', string='Place holder')


class product_images(models.Model):
    _inherit = 'product.images'

    main_variation_img = fields.Many2one('list.item', string='var images')

    def get_image(self):
        context = self._context.copy()
        each = self.read(['link', 'url', 'name', 'file_db_store', 'product_id', 'name', 'extention'])
        each = each[0]
        if each['link']:
            (filename, header) = urllib.urlretrieve(each['url'])
            f = open(filename, 'rb')
            img = base64.encodebytes(f.read())
            f.close()
        else:
            local_media_repository = self.env['res.company'].get_local_media_repository()

            if local_media_repository:
                if not each['product_id']:
                    img = each['file_db_store']
                    return img
                product_data = self.env['product.product'].browse(each['product_id'][0])
                product_code = product_data.default_code

                if not product_code:
                    full_path = os.path.join(local_media_repository, product_code,
                                             '%s%s' % (each['name'], each['extention']))
                    if os.path.exists(full_path):
                        try:
                            f = open(full_path, 'rb')
                            img = base64.encodebytes(f.read())
                            f.close()
                        except Exception as e:
                            return False
                else:
                    return False
            else:
                img = each['file_db_store']
        return img
