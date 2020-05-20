import re
import base64
import csv
import datetime
import json
import logging
import os
import random
import time
import urllib.request
from datetime import timedelta
import requests
from odoo import models, fields, api, _, osv
from odoo.exceptions import UserError, Warning

logger = logging.getLogger(__name__)


class ebay_store_category(models.Model):
    _name = "ebay.store.category"

    name = fields.Char(string='Name', size=256)
    category_id = fields.Char(string='Category ID', size=256)
    shop_id = fields.Many2one('sale.shop', string='Shop')


class sale_order_line(models.Model):
    _inherit = "sale.order.line"

    unique_sales_line_rec_no = fields.Char(string="Sales Line Record Number", size=256)
    return_id = fields.Char('Return ID')
    return_status = fields.Char('Return Status')
    returned = fields.Boolean(string='Returned')
    refunded = fields.Boolean(string='Refunded')
    return_qty = fields.Integer(string='Return Qty')
    rma = fields.Char(string='RMA')
    refund_jrnl_entry = fields.Many2one('account.move', 'Refund Journal Entry')

    # ebay_order = fields.Boolean(related='shop_id.ebay_shop',string='Ebay Order',store=True)
    # return_requested = fields.Boolean(string='Return Requested')
    # return_line = fields.One2many('return.order.line', 'order_id', string='Return Item Line')
    # return_id = fields.Char('Return ID')
    # return_status = fields.Char('Return Status')
    #
    # def get_user_returns(self):
    #     context = self._context.copy()
    #     connection_obj = self.env['ebayerp.osv']
    #     shop_obj = self.shop_id
    #     results = connection_obj.call(shop_obj.instance_id, 'getUserReturns', shop_obj.instance_id.site_id.site)
    #     if not results:
    #         raise UserError(_("Return Request not found"))
    #     return_id = results[0].get('ns1:ReturnId','')
    #     status = results[0].get('ns1:status','')
    #     item_list = results[0].get('ns1:returnRequest',[])
    #     return_line_data = []
    #     for item_details in item_list:
    #         item_dict = {}
    #         item_dict['item_id'] = item_details.get('ns1:itemId','')
    #         item_dict['transaction_id'] = item_details.get('ns1:transactionId','')
    #         item_dict['return_qty'] = item_details.get('ns1:returnQuantity','')
    #         return_line_data.append(item_dict)
    #     refund_vals = {
    #         'name':return_id,
    #         # 'return_line': [(1,0,return_line_data)],
    #         'return_status':status
    #     }
    #     refund_id = self.env['refund.order'].create(refund_vals)
    #     for line in return_line_data:
    #         vals =  {
    #             'item_id': line.get('item_id'),
    #             'transaction_id': line.get('transaction_id'),
    #             'return_qty': line.get('return_qty'),
    #             'refund_id': refund_id.id,
    #         }
    #         refund_line_id = self.env['refund.order.line'].create(vals)
    #     view = self.env.ref('ebay_base_ecommerce_merge.view_refund_order')
    #     action = {'name': _('User Returns'),
    #               'type': 'ir.actions.act_window',
    #               'view_type': 'form',
    #               'view_mode': 'form',
    #               'res_model': 'refund.order',
    #               'res_id':refund_id.id,
    #               'view_id': view.id,
    #               'target': 'new',
    #                }
    #     return action
    #


class sale_shop(models.Model):
    _name = "sale.shop"

    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")
    name = fields.Char(string="Channel Name", size=64, required=True)
    payment_default_id = fields.Many2one('account.payment.term', string="Default Payment Term")

    pricelist_id = fields.Many2one('product.pricelist', string="Pricelist")
    project_id = fields.Many2one('account.analytic.account', string="Analytic Account",
                                 domain=[('parent_id', '!=', False)])
    company_id = fields.Many2one('res.company', string="Company", required=False)

    store_id_ship_station = fields.Integer(string="Store ID Ship Station")
    currency = fields.Many2one('res.currency', string="Currency")
    instance_id = fields.Many2one('sales.channel.instance', string="Instance", readonly=True)
    last_update_order_date = fields.Date(string="Last Update order Date")
    #    prefix = fields.Char(string="Prefix", size=64),
    #    suffix = fields.Char(string="suffix", size=64),
    last_update_order_status_date = fields.Datetime(string="Start Update Status Date")
    last_export_stock_date = fields.Datetime(string="Last Exported Stock Date")
    last_export_price_date = fields.Datetime(string="Last Exported Price Date")
    last_import_order_date = fields.Datetime(string="Last Imported Order Date")
    sale_channel_shop = fields.Boolean(string="Sales channel shop")
    tax_include = fields.Boolean(string="Cost Price Include Taxes")
    picking_policy = fields.Selection(
        [('direct', 'Deliver each product when available'), ('one', 'Deliver all products at once')],
        string="Shipping Policy",
        help="""Pick 'Deliver each product when available' if you allow partial delivery.""")
    order_policy = fields.Selection([
        ('manual', 'On Demand'),
        ('picking', 'On Delivery Order'),
        ('prepaid', 'Before Delivery'),
    ], string="Create Invoice")
    shop_address = fields.Many2one('res.partner', string="Shop Address")
    alloc_type = fields.Selection([('fixed', 'Fixed'),
                                   ('per', 'Percentage')], string="Type")
    alloc_value = fields.Float(string="Value")
    is_shipped = fields.Boolean(string="Import shipped")
    #    sent_thankyou_email = fields.Boolean(string="Sent Thankyou Email")
    use_debug = fields.Boolean(string="Set Debug log")
    exclude_product = fields.Boolean(string="Import Order Only")
    template_id = fields.Many2one('mail.template', string="Email Template")
    marketplace_image = fields.Binary()
    ebay_shop = fields.Boolean(string='Ebay Shop', readonly=True)
    stock_update_on_time = fields.Boolean(string='Real Time Stock Update')
    last_ebay_listing_import = fields.Datetime(string='Last Ebay Listing Import')
    last_ebay_messages_import = fields.Datetime(string='Last Ebay Messages Import')
    postal_code = fields.Char(string='Postal Code', size=256)
    country_code = fields.Many2one('res.partner', string='Country Code')
    site_code = fields.Many2one('res.partner', string='Country Code')
    paypal_email = fields.Char(string='Paypal Email', size=64)
    payment_method = fields.Many2one('payment.method.ecommerce', string='Payment Method')
    store_name = fields.Char(string='Name', size=256)
    store_subscriplevel = fields.Char(string='Subscription Level', size=256)
    store_desc = fields.Char('Description', size=256)
    store_category_ids = fields.One2many('ebay.store.category', 'shop_id', string='Store Category')
    ebay_paid = fields.Boolean(string='Ebay Paid')

    def createProduct(self, shop_id, product_details):
        res = super(sale_shop, self).createProduct(shop_id, product_details)
        context = self._context.copy()
        if shop_id.ebay_shop:
            product_id = res
            product_sku = product_details.get('SellerSKU', '').strip() or product_id.default_code
            itemID = product_details.get('ItemID', '').strip()
            if product_id and itemID:
                self.createListing(shop_id, product_id.id, product_sku, itemID)
        return res

    def relist_item(self, shop_id, sku, itemId, qty, price=0.0):
        """
        This function is used to Relist item on Ebay
        parameters:
            shop_id :- integer
            sku :- integer
            itemId :- integer
            qty :- integer
            price :- integer
        """
        context = self._context.copy()

        if context is None:
            context = {}

        ebayerp_osv_obj = self.env['ebayerp.osv']
        shop_data = self.browse(shop_id)
        inst_lnk = shop_data.instance_id
        currency = shop_data.currency.name
        if not currency:
            #            raise osv.except_osv(_('Warning !'), _("Please Select Currency For Shop - %s")%(shop_data.name))
            raise UserError(_("Please Select Currency For Shop - %s") % shop_data.name)
        try:
            result = ebayerp_osv_obj.call(inst_lnk, 'RelistFixedPriceItem', itemId, qty, price, currency)
        except Exception as e:

            if context.get('raise_exception', False):
                #                raise osv.except_osv(_('Error!'),_('%s' % (str(e),)))
                raise UserError(_('%s' % (str(e))))

            return False

        if context.get('activity_log', False):
            activity_log = context['activity_log']
            activity_log.write({'note': activity_log.note + "Successfully updated"})

        gitem_results = shop_data.with_context(context).import_ebay_product(itemId, sku)
        if not gitem_results:
            logger.info('import_ebay_product result False')
            return False

        gitem_result = gitem_results[0]
        is_variation = gitem_result.get('variations') and True or False

        if not is_variation:
            return result

        for result_variation in gitem_result['variations']:
            if sku == result_variation['SKU']:
                revise_qty = qty
            else:
                revise_qty = 0

            try:
                results = ebayerp_osv_obj.call(inst_lnk, 'ReviseInventoryStatus', itemId, False, revise_qty,
                                               result_variation['SKU'])
            except Exception as e:
                continue
        return result

    def verify_relist_item(self, shop_id, itemId):
        """
        This function is used to verify the item relisted
        parameters:
            shop_id :- integer
            itemId :- integer
        """
        context = self._context.copy()
        ebayerp_osv_obj = self.env['ebayerp.osv']
        inst_lnk = self.browse(shop_id).instance_id
        try:
            result = ebayerp_osv_obj.call(inst_lnk, 'VerifyRelistItem', itemId)
        except Exception as e:
            if context.get('raise_exception', False):
                #                raise osv.except_osv(_('Error!'),_('%s' % (str(e),)))
                raise UserError(_('%s' % (str(e))))
            return False
        return result

    def get_ebay_store_category(self):
        """
        This function is used to get ebay store categories
        parameters:
            No Parameters
        """
        context = self._context.copy()
        shop_obj = self
        connection_obj = self.env['ebayerp.osv']
        categ_obj = self.env['ebay.store.category']

        if context is None:
            context = {}
        inst_lnk = shop_obj.instance_id
        site_id = inst_lnk.site_id.site
        user_id = inst_lnk.ebayuser_id
        shop_name = shop_obj.name
        store_name = shop_obj.store_name
        inst_name = inst_lnk.name
        if not user_id:
            #            raise osv.except_osv(_('Warning !'), _("Please Enter User ID For Instance %s")%(inst_name))
            raise UserError(_("Please Enter User ID For Instance %s") % inst_name)
        if not store_name:
            store_datas = connection_obj.call(inst_lnk, 'GetStore', user_id, site_id)

            if not store_datas:
                #                raise osv.except_osv(_('Warning !'), _("No Store For Shop %s")%(shop_name))
                raise UserError(_("No Store For Shop %s") % (shop_name))
            for store_dic in store_datas:
                for store_info in store_dic['StoreInfo']:
                    store_desc = False
                    if store_info.get('Description', False):
                        store_desc = store_info['Description']

                    SubscriptionLevel = False
                    if store_info.get('SubscriptionLevel', False):
                        SubscriptionLevel = store_info['SubscriptionLevel']

                    store_info_data = {'store_name': store_info['Name'],
                                       'store_desc': store_desc,
                                       'store_subscriplevel': SubscriptionLevel, }
                    shop_obj.write(store_info_data)

                for customcateg_info in store_dic['CustomCategoryInfo']:
                    categ_info_data = {
                        'name': customcateg_info['Name'],
                        'category_id': customcateg_info['CategoryID'],
                        'shop_id': shop_obj.id,
                    }
                    categ_obj.create(categ_info_data)

        return True

    def import_ebay_orders(self):
        """
        This function is used to Import Ebay orders
        parameters:
            No Parameter
        """
        context = self._context.copy()
        log_vals = {}
        connection_obj = self.env['ebayerp.osv']
        saleorder_obj = self.env['sale.order']
        stock_obj = self.env['stock.picking']
        prod_obj = self.env['product.product']
        list_obj = self.env['ebay.product.listing']
        shop_obj = self
        if context is None:
            context = {}
        context.update({'from_date': datetime.datetime.now()})
        inst_lnk = shop_obj.instance_id
        site_id = inst_lnk.site_id.site
        shop_name = shop_obj.name
        if site_id:
            siteid = site_id
        else:
            #            raise osv.except_osv(_('Warning !'), _("Please Select Site ID in %s shop")%(shop_name))
            raise UserError(_("Please Select Site ID in %s shop") % shop_name)
        currentTimeTo = datetime.datetime.utcnow()
        currentTimeTo = time.strptime(str(currentTimeTo), "%Y-%m-%d %H:%M:%S.%f")
        currentTimeTo = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", currentTimeTo)
        currentTimeFrom = shop_obj.last_import_order_date
        if not currentTimeFrom:
            currentTime = datetime.datetime.strptime(currentTimeTo, "%Y-%m-%dT%H:%M:%S.000Z")
            now = currentTime - datetime.timedelta(days=29)
            currentTimeFrom = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        else:
            currentTimeFrom = time.strptime(currentTimeFrom[:19], "%Y-%m-%d %H:%M:%S")
            currentTimeFrom = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", currentTimeFrom)
        diff = timedelta(minutes=10);
        currentTimeFrom = datetime.datetime.strptime(currentTimeFrom, "%Y-%m-%dT%H:%M:%S.000Z")
        currentTimeFrom = currentTimeFrom - diff
        currentTimeFrom = currentTimeFrom.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        pageNumber = 1
        resultFinal = []
        resultFinal_final = []

        while True:
            results = connection_obj.call(inst_lnk, 'GetOrders', currentTimeFrom, currentTimeTo, pageNumber)

            has_more_trans = results[len(results) - 1]
            del results[len(results) - 1]
            resultFinal = resultFinal + results
            if has_more_trans['HasMoreTransactions'] == 'false':
                break
            pageNumber = pageNumber + 1
        if resultFinal:
            context['date_format'] = "%Y-%m-%dT%H:%M:%S.000Z"
            context['create_tax_product_line'] = False
            context['shipping_code_key'] = 'ebay_code'
            context['shipping_product_default_code'] = 'SHIP EBAY'
            context['default_product_category'] = 1
            context['shipping_code_key'] = 'carrier_code'

            for resultfinal in resultFinal:
                prod_ids = False
                if resultfinal.get('listing_id'):
                    list_ids = list_obj.search([('name', '=', resultfinal.get('listing_id'))])
                    if list_ids:
                        prod_ids = list_ids[0].product_id.id
                        resultfinal.update({'product_id': prod_ids})
            #                    else:
            #                        if shop_obj.exclude_product:
            #                            continue
            #                        prod_ids = prod_obj.search([('default_code','=',resultfinal.get('SellerSKU'))])
            #                        if prod_ids:
            #                            resultfinal.update({'product_id': prod_ids[0].id})

            for results in resultFinal:
                if results.get('ShippedTime', False):
                    continue
                else:
                    resultFinal_final.append(results)

            orderid = self.with_context(context).createOrder(shop_obj, resultFinal_final)
            for order_id in orderid:
                browse_ids = order_id
                wh_id = stock_obj.search([('origin', '=', browse_ids.name)])
                if wh_id:
                    wh_id.write({'shop_id': shop_obj.id})
        else:
            message = _('No more orders to import')
        return True

    #
    #     def import_ebay_customer_messages(self):
    #         '''
    #         This function is used to Import Ebay customer messages
    #         parameters:
    #            No Parameter
    #         '''
    #         context = self._context.copy()
    #         connection_obj = self.env['ebayerp.osv']
    #         mail_obj = self.env['mail.thread']
    #         mail_msg_obj = self.env['mail.message']
    #         partner_obj = self.env['res.partner']
    #         sale_shop_obj = self.env['sale.shop']
    #         shop_obj = self
    #         inst_lnk = shop_obj.instance_id
    # #
    #         for id in self:
    #             shop_data = self.browse(id)
    #             inst_lnk = shop_data.instance_id
    #
    #             currentTimeTo = datetime.datetime.utcnow()
    #             currentTimeTo = time.strptime(str(currentTimeTo), "%Y-%m-%d %H:%M:%S.%f")
    #             currentTimeTo = time.strftime("%Y-%m-%dT%H:%M:%S.000Z",currentTimeTo)
    #             currentTimeFrom = shop_data.last_ebay_messages_import
    #             currentTime = datetime.datetime.strptime(currentTimeTo, "%Y-%m-%dT%H:%M:%S.000Z")
    #             if not currentTimeFrom:
    #                 now = currentTime - datetime.timedelta(days=100)
    #                 currentTimeFrom = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    #             else:
    #                 currentTimeFrom = time.strptime(currentTimeFrom, "%Y-%m-%d %H:%M:%S")
    #                 now = currentTime - datetime.timedelta(days=5)
    #                 currentTimeFrom = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    #         pageNo = 1
    #         while True:
    #             results = connection_obj.call(inst_lnk, 'GetMemberMessages',currentTimeFrom,currentTimeTo,pageNo)
    #             pageNo = pageNo + 1
    #             if results:
    #                 for result in results:
    #                     if not result:
    #                         continue
    #                     if result:
    #                         partner_ids = partner_obj.search([('ebay_user_id', '=', result.get('SenderID'))])
    #                         if len(partner_ids):
    #                             msg_vals = {
    #                             'res_id' : partner_ids[0].id,
    #                             'model' : 'res.partner',
    #                             'record_name' : partner_ids[0].name,
    #                              'body' : result.get('Body')
    #                             }
    #                             mail_ids = mail_msg_obj.search([('res_id', '=', partner_ids[0])])
    #                             if len(mail_ids):
    #                                 mail_id = mail_ids[0].id
    #                             else:
    #                                 mail_id = mail_msg_obj.create(msg_vals)
    #                             self._cr.commit()
    #             sale_shop_obj.write({'last_ebay_messages_import' : currentTimeTo})
    #         return True
    #

    def import_listing_csv_ebay(self):
        """
        This function is used to import ebay orders through CSV
        parameters:
            No Parameter
        """
        context = self._context.copy()
        li = []
        list_obj = self.env['ebay.product.listing']
        prod_obj = self.env['product.product']
        shop_name = self
        path = os.path.dirname(os.path.abspath(__file__))
        path_csv = path + '/channel2.csv'

        if path_csv:
            with open(path_csv) as f_obj:
                reader = csv.DictReader(f_obj, delimiter=',')

                for line in reader:

                    if line['StockSKU'] != "UNASSIGNED":

                        li.append(line['StockSKU'])
                        product_ids = prod_obj.search([('default_code', '=', line['StockSKU'])])
                        if product_ids:
                            li.remove(line['StockSKU'])
                            if shop_name.name.lower().find(line['Source'].lower()) != -1 and \
                                    line['Sub Source'].lower() == "ebay0":
                                vals = {
                                    'name': line['ChannelId'],
                                    'ebay_title': line['ChannelItemName'],
                                    'product_id': product_ids[0].id,
                                    'shop_id': shop_name.id,
                                    'active_ebay': True
                                }
                                list_id = list_obj.create(vals)

                                self._cr.commit()
        return True

    def import_ebay_product(self, itemId, sku):
        """
        This function is used to Import Ebay Products
        parameters:
            itemId :- integer
            sku :- char (unique product code)
        """
        context = self._context.copy()
        ebayerp_osv_obj = self.env['ebayerp.osv']
        inst_lnk = self.instance_id
        result = ebayerp_osv_obj.call(inst_lnk, 'GetItem', itemId, sku)
        return result

    def createListing(self, shop_id, product_id, product_sku, itemID):

        """
        This function is used to Listing Product on Ebay
        parameters:
            itemId :- integer
            itemId :- integer
            itemId :- integer
            itemId :- integer
            sku :- integer (product sku)
        """
        context = self._context.copy()
        shop_obj = self.env['sale.shop']
        product_listing_obj = self.env['ebay.product.listing']
        product_obj = self.env['product.product']
        prod_attr_set_obj = self.env['product.attribute.set']
        ebay_store_cat_obj = self.env['ebay.store.category']
        product_img_obj = self.env['product.images']
        shop_ids = shop_obj.search([('ebay_shop', '=', True)])
        shop_obj = self.env['sale.shop']
        product_data = product_obj.browse(product_id)
        shop_data = shop_obj.browse(shop_id.id)

        if product_id and itemID and shop_data.ebay_shop:
            listing_ids = product_listing_obj.search([('product_id', '=', product_id), ('name', '=', itemID)])
            if not len(listing_ids):
                results = shop_data.import_ebay_product(itemID, product_sku)
                if not results:
                    return True
                result = results[0]
                active = True
                if result:
                    if result['ListingDuration'] == 'GTC':
                        active = True
                    else:
                        endtime = datetime.datetime.strptime(result['EndTime'][:19], '%Y-%m-%dT%H:%M:%S')
                        today_time = datetime.datetime.strptime(time.strftime("%Y-%m-%d %H:%M:%S"), '%Y-%m-%d %H:%M:%S')
                        if endtime < today_time:
                            active = False

                    listing_vals = {
                        'name': itemID,
                        'shop_id': shop_id.id,
                        'type': result['ListingType'],
                        'listing_duration': result['ListingDuration'],
                        'ebay_start_time': result['StartTime'],
                        'ebay_end_time': result['EndTime'],
                        'last_sync_stock': int(result['Quantity']) - int(result.get('QuantitySold', 0)),
                        # 'last_sync_stock': result['Quantity'],
                        'condition': result.get('ConditionID', False),
                        'product_id': product_id,
                        'last_sync_date': time.strftime("%Y-%m-%d %H:%M:%S"),
                        'active_ebay': active,
                        'price': result['ItemPrice'],
                    }
                    product_listing_obj.create(listing_vals)

                """ to import ebay product image  image """
                if result:
                    image_gallery_url = result['picture']
                    img = image_gallery_url[0].get('gallery_img')
                    if img:
                        try:
                            file_contain = urllib.request.urlopen(img).read()
                            image_path = base64.encodebytes(file_contain)
                            imag_id = product_data.write({'image_medium': image_path})
                            name_id = product_obj.browse(product_id)
                            image_ids_avail = product_img_obj.search([('name', '=', name_id.name),('product_id', '=', product_id)])
                            if not image_ids_avail:
                                line_image_data = image_gallery_url[0].get('picture_url')
                                for data_img in line_image_data:
                                    random_num = random.randrange(100, 1000, 2)
                                    image_vals = {
                                        'name': name_id.name,
                                        'link': True,
                                        'is_ebay': True,
                                        'url': data_img,
                                        'product_id': product_id
                                    }
                                    image_ids_new = product_img_obj.create(image_vals)
                            else:
                                image_ids_new = image_ids_avail[0]
                        except Exception as e:
                            pass
                    condition_data = result.get('condition', False)
                    ebay_pro_condtn = condition_data[0].get('item_condition')
                    time.sleep(4)
                    condition_prod = product_data.write({'ebay_prod_condition': ebay_pro_condtn})
                    categ_data = result['categ_data']
                    categ_name = categ_data[0].get('categ_name')
                    categ_code = categ_data[0].get('categ_code')
                    categ_ids = prod_attr_set_obj.search([('code', '=', categ_code)])
                    if not categ_ids:
                        vals_category = {
                            'name': categ_name,
                            'code': categ_code,
                        }
                        categ_id = prod_attr_set_obj.create(vals_category)
                    else:
                        categ_id = categ_ids[0]
                    categ = product_data.write({'ebay_category1': categ_id.id})
                    self._cr.commit()
                if shop_data.ebay_shop:
                    ''' to import store category  from ebay '''
                    store_data = result.get('store_data', False)
                    if len(store_data):
                        store_cat_ebay1 = store_data[0].get('store_categ1')
                        store_cat_ebay2 = store_data[0].get('store_categ2')
                        categ_id_store1 = ebay_store_cat_obj.search([('category_id', '=', store_cat_ebay1)])
                        categ_id_store2 = ebay_store_cat_obj.search([('category_id', '=', store_cat_ebay2)])

                        if len(categ_id_store1):
                            categ_id_store1 = product_id.write({'store_cat_id1': categ_id_store1[0]})
                        if len(categ_id_store2):
                            categ_id_store1 = product_id.write({'store_cat_id2': categ_id_store2[0]})
                        self._cr.commit()
        return True

    def import_listing(self, shop_id, product_id, resultvals):
        """
        This function is used to Import Listing from ebay
        parameters:
            shop_id :- integer
            product_id :- integer
            resultvals :- dictionary of the product data
        """
        context = self._context.copy()
        if isinstance(shop_id, int):
            shop_obj = self.env['sale.shop'].browse(shop_id)
        else:
            shop_obj = shop_id
        if shop_obj.ebay_shop:
            itemID = resultvals.get('ItemID', False)
            product_sku = resultvals.get('SellerSKU', False)
            if not product_sku:
                product_sku = self.env['product.product'].browse(product_id).default_code
            if product_sku and itemID:
                self.with_context(context).createListing(shop_id, product_id, product_sku, itemID)
        return super(sale_shop, self).import_listing(shop_id, product_id, resultvals)

    def update_ebay_order_status(self):
        """
        This function is used to update order status on Ebay
        parameters:
            No Parameter
        """
        logger.info("test--------self---tax---- %s", self)
        logger.info("test--------context---tax---- %s", self._context.copy())
        context = self._context.copy()
        if context is None:
            context = {}
        offset = 0
        inst_lnk = self.instance_id
        shop_obj = self.browse(self[0].id)
        productlisting_obj = self.env['ebay.product.listing']
        stock_obj = self.env['stock.picking']
        sale_obj = self.env['sale.order']
        ebayerp_obj = self.env['ebayerp.osv']
        sale_ids = sale_obj.search([('track_exported', '=', False), ('state', 'not in', ['draft', 'cancel']),
                                    ('carrier_tracking_ref', '!=', False), ('shop_id', '=', shop_obj.id)], offset, 100)

        shop_data = self
        logger.info("test--------sale_ids---tax---- %s", sale_ids)
        for sale_data in sale_ids:
            logger.info("test--------sale_data.carrier_tracking_ref---tax---- %s", sale_data.carrier_tracking_ref)
            if not sale_data.carrier_tracking_ref:
                continue
            if not sale_data.carrier_id:
                continue
            for line in sale_data.order_line:
                if line.product_id.product_tmpl_id.type == 'service':
                    continue

                order_data = {}
                trans_split = line.unique_sales_line_rec_no.split("-")
                print(trans_split)
                if not trans_split:
                    continue
                order_data['ItemID'] = trans_split[0]
                order_data['TransactionID'] = trans_split[1]

                listing_ids = productlisting_obj.search([('name', '=', order_data['ItemID'])])
                order_data['ListingType'] = listing_ids and listing_ids[0].type or 'FixedPriceItem'
                order_data['Paid'] = False
                if shop_data.ebay_paid:
                    order_data['Paid'] = True
                logger.info("test----1----order_data---tax---- %s", order_data)

                order_data['shipped'] = True
                order_data['ShipmentTrackingNumber'] = sale_data.carrier_tracking_ref
                logger.info("test---2-----order_data---tax---- %s", order_data)
                if sale_data.carrier_id.carrier_code:
                    logger.info("test--------picking_data.carrier_id.carrier_code---tax---- %s",
                                sale_data.carrier_id.carrier_code)
                    if '_' in sale_data.carrier_id.carrier_code:
                        carrier_code = sale_data.carrier_id.carrier_code.split('_')
                        logger.info("test----splited----carrier_code---tax---- %s", carrier_code)
                        order_data['ShippingCarrierUsed'] = carrier_code[1]
                    else:
                        order_data['ShippingCarrierUsed'] = sale_data.carrier_id.carrier_code
                else:
                    if sale_data.carrier_id.name:
                        carrier_code = sale_data.carrier_id.name.strip(' ')
                        order_data['ShippingCarrierUsed'] = carrier_code
                    else:
                        continue

            logger.info("test----3----order_data---tax---- %s", order_data)
            results = []

            results = ebayerp_obj.call(inst_lnk, 'CompleteSale', order_data)
            # logger.info("test--------results---tax---- %s",results)
            # results='Success'
            if results == 'Success':
                sale_data.write({'track_exported': True})
                picking_data = sale_data.picking_ids[0]
                picking_data.write({'track_exported': True})

                # If still in draft => confirm and assign
                if picking_data.state == 'draft':
                    picking_data.action_confirm()
                    if picking_data.state != 'assigned':
                        picking_data.action_assign()
                # for pack in picking_data.pack_operation_ids:
                #     if pack.product_qty > 0:
                #         pack.write({'qty_done': pack.product_qty})
                #     else:
                #         pack.unlink()
                picking_data.do_transfer()

                invoice_ids = sale_data.mapped('invoice_ids')

                if len(invoice_ids):
                    invoice_id = invoice_ids[0]
                    if invoice_id.state == 'paid':
                        sale_data.action_done()

            self._cr.commit()
        return True

    def handleMissingItems(self, id, missed_resultvals):
        """
        This function is used to Handle missing items during ebay order import
        parameters:
            missed_resultvals :- dictionary of all the missing order data
        """
        context = self._context.copy()
        count = 0
        product_obj = self.env['product.product']
        product_listing_obj = self.env['ebay.product.listing']

        while missed_resultvals:
            '''  count is to make sure loop doesn't go into endless iteraiton '''
            count = count + 1
            if count > 3:
                break

            resultvals = missed_resultvals

            for results in resultvals:
                try:
                    if results.get('SellerSKU', False):
                        product_ids = product_obj.search([('product_sku', '=', results['SellerSKU'])])
                        today_time = datetime.datetime.strptime(time.strftime("%Y-%m-%d %H:%M:%S"), '%Y-%m-%d %H:%M:%S')
                        if len(product_ids):
                            listing_ids = product_listing_obj.search(
                                [('product_id', '=', product_ids[0].id), ('name', '=', results['ItemID'])])
                            if results['ListingDuration'] == 'GTC':
                                active = True
                            else:
                                endtime = datetime.datetime.strptime(results['EndTime'][:19], '%Y-%m-%dT%H:%M:%S')
                                active = True

                                if endtime < today_time:
                                    active = False

                            listing_vals = {
                                'name': results['ItemID'],
                                'shop_id': id[0],
                                'listing_duration': results['ListingDuration'],
                                'ebay_start_time': results['StartTime'],
                                'ebay_end_time': results['EndTime'],
                                'last_sync_stock': int(results['Quantity']) - int(results.get('QuantitySold', 0)),
                                'product_id': product_ids[0].id,
                                'last_sync_date': time.strftime("%Y-%m-%d %H:%M:%S"),
                                'active_ebay': active,
                                'is_variant': results.get('variant', False),
                            }
                            if not listing_ids:
                                product_listing_obj.create(listing_vals)
                                self._cr.commit()

                            else:
                                listing_ids.write(listing_vals)
                                self._cr.commit()

                    missed_resultvals.remove(results)

                except Exception as e:
                    if str(e).lower().find('connection reset by peer') != -1:
                        time.sleep(10)
                        continue
                    elif str(e).find('concurrent update') != -1:
                        self._cr.rollback()
                        time.sleep(20)
                        continue
        return True

    def import_ebay_listing(self):
        """
        This function is used to Import ebay Listings
        parameters:
            No Parameter
        """
        context = self._context.copy()
        product_obj = self.env['product.product']

        product_listing_obj = self.env['ebay.product.listing']
        for id in self:
            shop_data = self
            shop_id = shop_data.id
            inst_lnk = shop_data.instance_id
            subject = shop_data.name + ': Ebay New Listing Import Exception'

            ebayerp_osv_obj = self.env['ebayerp.osv']

            currentTimeTo = datetime.datetime.utcnow()
            currentTimeTo = time.strptime(str(currentTimeTo), "%Y-%m-%d %H:%M:%S.%f")
            currentTimeTo = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", currentTimeTo)
            missed_item_ids = []
            currentTimeFrom = shop_data.last_ebay_listing_import
            currentTime = datetime.datetime.strptime(currentTimeTo, "%Y-%m-%dT%H:%M:%S.000Z")
            if not currentTimeFrom:
                now = currentTime - datetime.timedelta(days=120)
                currentTimeFrom = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            else:
                now = currentTime - datetime.timedelta(days=5)
                currentTimeFrom = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            titles = []
            missing_skus = []

            pageNo = 1
            while True:
                results_total = ebayerp_osv_obj.call(inst_lnk, 'GetSellerList', currentTimeFrom, currentTimeTo, pageNo)
                pageNo = pageNo + 1
                if not results_total:
                    break
                """for variation """

                for results in results_total:
                    result_list = []
                    if results.get('variations', False):
                        for each_sku in results['variations']:
                            result_info = {}
                            result_info = results.copy()
                            result_info['SellerSKU'] = each_sku.get('SKU', False)
                            result_info['QuantitySold'] = each_sku.get('QuantitySold', False)
                            result_info['Quantity'] = each_sku.get('Quantity', False)
                            result_info['variant'] = True
                            result_list.append(result_info)
                    else:
                        result_list.append(results)

                    for each_result in result_list:

                        product_ids = []
                        listing_ids = []
                        if each_result.get('SellerSKU', False):
                            missing_skus.append(each_result)

                            product_ids = product_obj.search([('default_code', '=', each_result['SellerSKU'])])

                        today_time = datetime.datetime.strptime(time.strftime("%Y-%m-%d %H:%M:%S"), '%Y-%m-%d %H:%M:%S')
                        if len(product_ids):
                            listing_ids = product_listing_obj.search(
                                [('product_id', '=', product_ids[0].id), ('name', '=', each_result['ItemID'])])

                            if each_result['ListingDuration'] == 'GTC':
                                active = True
                            else:
                                endtime = datetime.datetime.strptime(each_result['EndTime'][:19], '%Y-%m-%dT%H:%M:%S')
                                active = True

                                if endtime < today_time:
                                    active = False

                            listing_vals = {
                                'name': each_result['ItemID'],
                                'shop_id': shop_id,
                                'type': each_result['ListingType'],
                                'listing_duration': each_result['ListingDuration'],
                                'ebay_start_time': each_result['StartTime'],
                                'ebay_end_time': each_result['EndTime'],
                                'condition': each_result.get('ConditionID', False),
                                'last_sync_stock': int(each_result['Quantity']) - int(
                                    each_result.get('QuantitySold', 0)),
                                'product_id': product_ids[0].id,
                                'last_sync_date': time.strftime("%Y-%m-%d %H:%M:%S"),
                                'active_ebay': active,
                                'is_variant': each_result.get('variant', False),
                                'ebay_title': each_result.get('Title'),
                                'ebay_sku': each_result.get('SellerSKU'),
                            }
                        else:
                            if each_result['ListingDuration'] == 'GTC':
                                active = True
                            else:
                                endtime = datetime.datetime.strptime(each_result['EndTime'][:19], '%Y-%m-%dT%H:%M:%S')
                                active = True

                                if endtime < today_time:
                                    active = False

                            listing_vals = {
                                'name': each_result['ItemID'],
                                'shop_id': shop_id,
                                'type': each_result['ListingType'],
                                'listing_duration': each_result['ListingDuration'],
                                'ebay_start_time': each_result['StartTime'],
                                'ebay_end_time': each_result['EndTime'],
                                'condition': each_result.get('ConditionID', False),
                                'last_sync_stock': int(each_result['Quantity']) - int(
                                    each_result.get('QuantitySold', 0)),
                                # 'product_id': product_ids[0].id,
                                'last_sync_date': time.strftime("%Y-%m-%d %H:%M:%S"),
                                'active_ebay': active,
                                'is_variant': each_result.get('variant', False),
                                'ebay_title': each_result.get('Title'),
                                'ebay_sku': each_result.get('SellerSKU'),
                            }

                        if not listing_ids:
                            product_listing_obj.create(listing_vals)
                            self._cr.commit()

                        else:
                            listing_ids.write(listing_vals)
                            self._cr.commit()

            self.with_context(context).handleMissingItems(id, missed_item_ids)
            shop_data.write({'last_ebay_listing_import': time.strftime("%Y-%m-%d %H:%M:%S")})
            if missing_skus:
                raise Warning("""Your eBay listings have been successfully imported, however some listings are missing Product SKU's. \nPlease Update products SKU's in eBay to avoid further conflicts.
                    \n\n To correct this error and avoid duplicate listings in Zest ERP please do the following:\n
                    - Update product SKU's in your eBay protal.
                    """)
        return True

    def import_ebay_price(self, product_sku, item_id, start_price, qty, shop_id):
        """
        This function is used to Import ebay product price
        parameters:
            product_sku :- char (product unique code)
            item_id :- integer (product listing code)
            start_price :- integer
            qty :- integer
            shop_id :- integer
        """
        context = self._context.copy()
        shop = self.browse(shop_id)
        product_obj = self.env['product.product']
        product_listing_obj = self.env['ebay.product.listing']
        sale_obj = self.env['sale.shop']
        qty_on_ebay = 0
        product_data = product_obj.search([('product_sku', '=', product_sku)])
        if product_data:
            ebayerp_obj = self.env['ebayerp.osv']
            if qty:
                results = shop.import_ebay_product(item_id, product_sku)
                cont_fwd = True
                if not results:
                    cont_fwd = False
                if cont_fwd:
                    result = results[0]
                    if result.get('Quantity', False):
                        initial_qty = result['Quantity']
                        qty_sold = result['QuantitySold']
                        '''if result.get('variations',False):
                            for each_sku in results['variations']:
                                if each_sku['SKU'] == product_sku:
                                    initial_qty = each_sku['Quantity']
                                    qty_sold = each_sku['QuantitySold']
                                    break'''

                        qty_on_ebay = int(initial_qty) - int(qty_sold)

                        """ For automation, we dont check Ebay just update initial Quantity """
                        if not context.get('is_automation', False):
                            qty = int(initial_qty) - int(qty_sold) + int(qty)

                """ If qty on Ebay and Qty Sent is equal , do not update on Ebay """
                if qty_on_ebay == qty:
                    return True

            end_listing = False
            log = ''
            """Handle End Listing: Start """
            if not qty and context.get('is_automation', False):
                self.with_context(context).endEbayListing(shop_id, product_sku, item_id)
                end_listing = True
                listing_ids = product_listing_obj.search(
                    [('product_id', '=', self.product_ids[0]), ('name', '=', item_id)])
                if listing_ids:
                    listing_ids.write({'active_ebay': False})
                log = 'Listing Ended'

            results = False
            if not end_listing:
                try:
                    results = ebayerp_obj.call(shop.instance_id, 'ReviseInventoryStatus', item_id, start_price, qty,
                                               product_sku)
                except Exception as e:
                    if not context.get('is_automation', False):
                        #                        raise osv.except_osv(_('Error !'),e)
                        raise UserError(_('Error !'), e)
                    else:
                        context['subject'] = str(e)
                        sale_obj.with_context(context)._do_send_auto_stock_email([shop_id], product_data, item_id)

                if start_price:
                    log += 'Price:' + str(start_price)
                if qty:
                    log += ' Stock:' + str(qty)

            vals_log = {
                'name': 'Export Price / Stock',
                'shop_id': shop_id,
                'action': 'individual',
                'note': str(item_id) + '/' + str(product_sku) + ' ' + log,
                'submission_id': False,
                'update_datetime': time.strftime('%Y-%m-%dT%H:%M:%S')
            }
            self.env['master.ecommerce.logs'].create(vals_log)

        return True

    def get_variation_data(self, result_variations, product_sku):
        context = self._context.copy()
        for result_variation in result_variations:
            if result_variation.get('SKU', False):
                logger.info("---result_variation['SKU']---- %s", result_variation['SKU'])
                if product_sku != result_variation['SKU']:
                    continue
                return result_variation
        return False

    def export_stock_and_price(self):
        """
        This function is used to Export stock and Price on ebay
        parameters:
            No Parameter
        """
        context = self._context.copy()
        connection_obj = self.env['ebayerp.osv']
        ebay_prod_list_obj = self.env['ebay.product.listing']

        update_stock = context.get('update_stock', False)
        update_price = context.get('update_price', False)

        if context is None:
            context = {}

        context.update({'from_date': datetime.datetime.now()})

        (data,) = self
        ebay_inst_data = data.instance_id

        if context.get('eactive_ids'):
            listing_ids = context.get('eactive_ids')
        else:
            listing_ids = ebay_prod_list_obj.search(
                [('active_ebay', '=', True), ('shop_id', '=', data.id), ('name', '!=', False)])
        logger.info("test--------export_stock_and_price---listing_ids---- %s", listing_ids)
        if isinstance(listing_ids, list) or isinstance(listing_ids, int):
            listing_browse_data = ebay_prod_list_obj.browse(listing_ids)
        else:
            listing_browse_data = listing_ids
        for ebay_list_data in listing_browse_data:

            try:
                item_id = ebay_list_data.name

                if item_id:

                    result = connection_obj.call(ebay_inst_data, 'GetItem', item_id,
                                                 ebay_list_data.product_id.default_code)
                    #                    logger.info("test--------export_stock_and_price---result---- %s",result)
                    if len(result):
                        if result[0].get('ItemID', False):
                            is_variation = result[0].get('variations') and True or False
                            ebay_sku = ebay_list_data.ebay_sku or ebay_list_data.product_id.default_code or False
                            #
                            if not ebay_sku:
                                continue

                            if is_variation:
                                variation_data = self.get_variation_data(result[0]['variations'], ebay_sku)
                                #                                logger.info("test--------export_stock_and_price---variation_data---- %s",variation_data)
                                if not variation_data:
                                    continue
                                initial_qty = int(variation_data.get('Quantity', 0))
                                qty_sold = int(variation_data.get('QuantitySold', 0))

                            else:
                                if result[0].get('SellerSKU', False):
                                    if result[0]['SellerSKU'] != ebay_sku:
                                        continue

                                else:
                                    continue

                                initial_qty = result[0]['Quantity']
                                qty_sold = result[0]['QuantitySold']

                            qty = int(ebay_list_data.product_id.virtual_available)
                            qty_on_ebay = int(initial_qty) - int(qty_sold)
                            logger.info("test--------export_stock_and_price---qty_on_ebay---- %s", qty_on_ebay)
                            logger.info("test--------export_stock_and_price---qty---- %s", qty)
                            if qty_on_ebay == qty:
                                continue
                            else:
                                price = False
                                if update_price:
                                    price = ebay_list_data.price

                                stock = False
                                if update_stock:
                                    stock = qty

                                results = connection_obj.call(ebay_inst_data, 'ReviseInventoryStatus',
                                                              ebay_list_data.name, price, stock, ebay_sku,
                                                              context.get('val'))

            except Exception as e:
                if e in ('Item not found.', 'FixedPrice item ended.'):
                    pass
                else:
                    #                    raise osv.except_osv(_('Error !'),e)
                    raise UserError(_("Error ! '%s'") % e)

        self.write({'last_export_stock_date': datetime.datetime.now()})
        return True

    def import_shipping_services(self):
        """
        This function is used to Import the Shipping Services
        parameters:
            No Parameter
        """
        context = self._context.copy()
        connection_obj = self.env['ebayerp.osv']
        shop_obj = self

        results = connection_obj.call(shop_obj.instance_id, 'GeteBayDetails', shop_obj.instance_id.site_id.site)

        if results:
            results_first_array = results.get('ShippingServiceDetails', False)
            for info in results_first_array:
                serv_carr = info.get('Description', False)
                vals = {
                    'serv_carr': serv_carr,
                    'ship_serv': info.get('ShippingService', False),
                }
                if info.get('ExpeditedService', False):
                    vals.update({'serv_type': info.get('ExpeditedService', False)})
                test = self.with_context(context).create_carrier(vals)
        return True

    def create_carrier(self, vals):
        """
        This function is used to create Carrier
        parameters:
            vals :- dictionary of all the Carrier data
        """
        context = self._context.copy()
        carrier_obj = self.env['delivery.carrier']
        product_object = self.env['product.product']
        partner_object = self.env['res.partner']
        categry_obj = self.env['product.category']
        carr_ids = carrier_obj.search([('carrier_code', '=', vals.get('ship_serv'))])
        if carr_ids:
            c_id = carr_ids[0]
            if vals.get('serv_type', False) and vals.get('serv_type') == 'true':
                c_id.write({'ship_type': 'expedited'})
        else:
            prod_ids = product_object.search([('name', '=', 'Shipping and Handling')])
            if prod_ids:
                p_id = prod_ids[0]
            else:
                categ_ids = categry_obj.search([('name', '=', 'All')])
                if categ_ids:
                    categ_id = categ_ids[0]
                else:
                    categ_id = categry_obj.create({'name': 'All'})
                p_id = product_object.create(
                    {'name': 'Shipping and Handling', 'type': "service", 'categ_id': categ_id.id})
            partner_search_ids = partner_object.search([('name', '=', vals.get('serv_carr'))])
            if partner_search_ids:
                patner_id = partner_search_ids[0]
            else:
                patner_id = partner_object.create({'name': vals.get('serv_carr')})
            carrier_vals = {'name': vals.get('serv_carr'), 'carrier_code': vals.get('ship_serv'), 'product_id': p_id.id,
                            'partner_id': patner_id.id}
            if vals.get('serv_type', False) and vals.get('serv_type') == 'true':
                carrier_vals.update({'ship_type': 'expedited'})
            c_id = carrier_obj.create(carrier_vals)
            self._cr.commit()
        return c_id.id

    @api.model
    def run_import_ebay_orders_scheduler(self, ids=None):
        """
        This function is used to run scheduler to Import ebay Orders
        parameters:
            No Parameter
        """
        context = self._context.copy()
        shop_ids = self.search([('ebay_shop', '=', True)])
        if context is None:
            context = {}
        for shop_id in shop_ids:
            current_date = datetime.datetime.now()
            sequence = self.env['ir.sequence'].next_by_code('import.order.unique.id')
            context['import_unique_id'] = sequence
            shop_id.with_context(context).import_ebay_orders()
            shop_id.last_import_order_date = current_date
        return True

    @api.model
    def run_update_ebay_order_status_scheduler(self, ids=None):
        """
        This function is used to run scheduler to Update Ebay Order Status
        parameters:
            No Parameter
        """
        context = self._context.copy()
        shop_ids = self.search([('ebay_shop', '=', True)])
        if context is None:
            context = {}
        for shop_id in shop_ids:
            #            self.with_context(context).update_ebay_order_status([shop_id.id])
            shop_id.with_context(context).update_ebay_order_status()
        return True

    def run_export_ebay_stock_scheduler(self):
        """
        This function is used to run scheduler to export ebay stock
        parameters:
            No Parameter
        """
        context = self._context.copy()
        shop_ids = self.search([('ebay_shop', '=', True)])
        if context is None:
            context = {}
        for shop_id in shop_ids:
            context['update_stock'] = True
            self.with_context(context).export_stock_and_price([shop_id.id])
        return True

    # scheduler for return items
    @api.model
    def run_get_user_returns_scheduler(self, ids=None):
        start_datetime = fields.datetime.now()
        context = self._context.copy()
        shop_ids = self.search([('ebay_shop', '=', True)])
        for shop_obj in shop_ids:
            try:
                connection_obj = self.env['ebayerp.osv']
                url = "https://api.ebay.com/post-order/v2/return/search"

                querystring = {"return_state": "RETURN_STARTED"}

                # payload = "\n}\n"
                # token = "TOKEN "+shop_obj.instance_id.auth_token
                token = "TOKEN " + shop_obj.instance_id.auth_token

                headers = {
                    'authorization': token,
                    'x-ebay-c-marketplace-id': "EBAY_GB",
                    'content-type': "application/json",
                    'accept': "application/json"
                }

                response = requests.request("GET", url, headers=headers, params=querystring)

                print("-----response----", response.text)

                # results = connection_obj.call(shop_obj.instance_id, 'getUserReturns', shop_obj.instance_id.site_id.site)
                # results =response.text
                # print("------v--response.content.encode('utf-8')------",response.content.decode('utf-8'))
                if response.status_code == requests.codes.ok:
                    results = json.loads(response.content.decode('utf-8'))
                    result1 = results.get('members', False)

                    if result1:
                        for result in result1:

                            return_id = result.get('returnId', '')
                            status = result.get('status', '')
                            creationInfo = result.get('creationInfo', )
                            item = creationInfo.get('item', '')
                            # item_list = result.get('ns1:returnRequest', [])
                            # for item_details in item_list:
                            transaction_id = item.get('transactionId', '')
                            return_qty = item.get('returnQuantity', '')
                            sale_line = self.env['sale.order.line'].search(
                                [('unique_sales_line_rec_no', 'ilike', transaction_id)])
                            if sale_line:
                                sale_line.write({
                                    'return_id': return_id,
                                    'return_status': status,
                                    'returned': True,
                                    'return_qty': int(return_qty)
                                })
                else:
                    # if response.status_code == 400:
                    res_error = json.loads(response.content.decode('utf-8'))
                    if res_error.get('error', False)[0].get('parameter', False)[0].get('value', False):
                        log_obj = self.env['ecommerce.logs']
                        log_vals = {
                            'start_datetime': start_datetime,
                            'end_datetime': fields.datetime.now(),
                            'shop_id': shop_obj.id,
                            'message': str(
                                res_error.get('error', False)[0].get('parameter', False)[0].get('value', False))
                        }
                        log_obj.create(log_vals)
            except Exception as e:
                logger.info("--------Exception----------- %s", e)
                continue

    def debug_log(self):

        log_obj = self.env['ecommerce.logs']

        #        shop_data = self.browse(cr, uid, ids, context)
        if self.use_debug:
            log_obj.log_data("logs");
        #            log_obj.log_data(cr,uid,"logs",args);

        else:
            return False

    def update_order_status(self):
        """
        This function is used to Update Order Status Based on the shops selected
        parameters: No parameters
        """

        log_obj = self.env['ecommerce.logs']

        log_vals = {}
        shop_obj = self
        logger.info('shop_obj.instance_id.module_id==== %s', shop_obj.instance_id.module_id)
        if shop_obj.instance_id.module_id == 'amazon_odoo_v11':
            self.update_amazon_order_status()

        if shop_obj.instance_id.module_id == 'ebay_base_ecommerce_merge':
            self.update_ebay_order_status()

        if shop_obj.instance_id.module_id == 'jet_teckzilla':
            self.update_jet_order_status()

        if shop_obj.instance_id.module_id == 'magento_odoo_v10':
            self.update_magento_order_status()

        if shop_obj.instance_id.module_id == 'groupon_teckzilla':
            self.update_groupon_order_status()

        if shop_obj.instance_id.module_id == 'woocommerce_odoo':
            self.update_woocommerce_order_status()

        if shop_obj.instance_id.module_id == 'shopify_odoo_v10':
            self.update_shopify_order_status()

        shop_obj.write({'last_update_order_status_date': datetime.datetime.now()})
        log_vals = {
            'activity': 'update_order_status',
            'start_datetime': self._context.get('from_date', False),
            'end_datetime': datetime.datetime.now(),
            'shop_id': self._ids[0],

            'message': 'SuccessFul'
        }
        log_obj.create(log_vals)
        return True

    def export_price(self):
        """
        This function is used to Export price Based on the shops selected
        parameters: No parameters
        """
        context = self._context.copy()
        log_obj = self.env['ecommerce.logs']
        field_obj = self.env['ir.model.fields']
        shop_obj = self
        if shop_obj.instance_id.module_id == 'virtuemart_odoo':
            self.export_product_price()
        if shop_obj.instance_id.module_id == 'shopify_odoo_v10':
            self.update_price_in_shopify()

        amazon_field_true = field_obj.search([('model', '=', 'sale.shop'), ('name', '=', 'amazon_shop')])
        magento_field_true = field_obj.search([('model', '=', 'sale.shop'), ('name', '=', 'magento_shop')])
        woocommerce_field_true = field_obj.search([('model', '=', 'sale.shop'), ('name', '=', 'woocom_shop')])
        ebay_field_true = field_obj.search([('model', '=', 'sale.shop'), ('name', '=', 'ebay_shop')])
        log_vals = {}
        #        try:
        if amazon_field_true:
            if self.amazon_shop:
                self.export_amazon_price()
        if ebay_field_true:
            if self.ebay_shop:
                context['update_price'] = True
                self.export_stock_and_price()
        if magento_field_true:
            if self.magento_shop:
                print("****************self.magento_shop******************", self.magento_shop)
                self.export_magento_price()
        if woocommerce_field_true:
            if self.woocom_shop:
                print("****************self.woocom_shop******************", self.woocom_shop)
                self.export_woocommerce_price()

        self.write({'last_export_price_date': datetime.datetime.now()})
        log_vals = {
            'activity': 'export_price',
            'start_datetime': context.get('from_date', False),
            'end_datetime': datetime.datetime.now(),
            'shop_id': self[0].id,
            'message': 'Successful'
        }
        #        except Exception as e:
        #            log_vals = {
        #                            'activity': 'import_orders',
        #                            'start_datetime': self._context.get('from_date',False),
        #                            'end_datetime': datetime.datetime.now(),
        #                            'shop_id': self[0].id,
        #                            'message':'Failed ' + str(e)
        #                          }
        log_obj.create(log_vals)
        return True

    #    def export_magento_price(self, cr, uid, ids, context):
    #        prod_obj=self.pool.get('product.product')
    #        log_obj = self.pool.get('ecommerce.logs')
    def export_magento_price(self):
        prod_obj = self.env['product.product']
        log_obj = self.env['ecommerce.logs']
        for shop_data in self.browse(self.cr, self.uid, self.ids, self.context):
            mage = (shop_data.instance_id.location, shop_data.instance_id.apiusername,
                    shop_data.instance_id.apipassoword)
            mage.connect()
            if self.env.context.get('active_ids', False):
                product_id = self.env.context['active_ids']
            else:
                product_id = prod_obj.search([('magento_exported', '=', True)])
                print("**************------product_id--------****************", product_id)
            for browse_obj in prod_obj.browse(product_id):
                sku_list = {'price': browse_obj.magento_price or browse_obj.list_price}
                print("***************########## sku_list ###########*****************", sku_list)
                mage.client.service.catalogProductUpdate(mage.token, browse_obj.default_code, sku_list,
                                                         shop_data.store_id, 'sku')

        return True

    def export_stock(self):
        """
        This function is used to Export Stock Based on the shops selected
        parameters: No parameters
        """
        context = self._context.copy()
        log_obj = self.env['ecommerce.logs']
        log_vals = {}
        shop_obj = self
        if shop_obj.instance_id.module_id == 'virtuemart_odoo':
            self.export_product_stock()
        if shop_obj.instance_id.module_id == 'amazon_odoo_v11':
            self.export_amazon_stock()
        if shop_obj.instance_id.module_id == 'ebay_base_ecommerce_merge':
            context['update_stock'] = True
            self.with_context(context).export_stock_and_price()
        if shop_obj.instance_id.module_id == 'magento_odoo_v10':
            self.export_magento_stock()
        if shop_obj.instance_id.module_id == 'shopify_odoo_v10':
            self.update_stock_in_shopify()
        shop_obj.write({'last_export_stock_date': datetime.datetime.now()})
        log_vals = {
            'activity': 'export_stock',
            'start_datetime': context.get('from_date', False),
            'end_datetime': datetime.datetime.now(),
            'shop_id': self[0].id,
            'message': 'Successful'
        }
        log_obj.create(log_vals)
        return True

    def import_orders(self):

        """
        This function is used to Import Orders Based on the shops selected
        parameters: No parameters
        """
        log_obj = self.env['ecommerce.logs']

        log_vals = {}
        sequence = self.env['ir.sequence'].next_by_code('import.order.unique.id')
        #        context['import_unique_id']= sequence
        ctx = self._context.copy()
        ctx.update({'import_unique_id': 'sequence'})
        print("--------self._ids[0]-----------", self._ids[0])
        print("----------self.id---------", self.id)
        shop_obj = self.browse(self._ids[0])
        print("--------shop_obj----------", shop_obj)
        if shop_obj.instance_id.module_id == 'amazon_odoo_v11':
            self.with_context(ctx).import_amazon_orders()
        if shop_obj.instance_id.module_id == 'ebay_base_ecommerce_merge':
            print("shop_obj.instance_id.module_id == 'ebay_base_ecommerce_merge'")
            self.with_context(ctx).import_ebay_orders()
        if shop_obj.instance_id.module_id == 'jet_teckzilla':
            self.import_jet_orders()
        if shop_obj.instance_id.module_id == 'magento_odoo_v10':
            self.import_magento_orders()
        if shop_obj.instance_id.module_id == 'groupon_teckzilla':
            self.import_groupon_orders()
        if shop_obj.instance_id.module_id == 'woocommerce_odoo':
            self.import_woocommerce_orders()
        if shop_obj.instance_id.module_id == 'virtuemart_odoo':
            self.import_sale_order(self.last_import_order_date)
        if shop_obj.instance_id.module_id == 'magento_2_v10':
            self.with_context(ctx).import_magento_2_order()
        if shop_obj.instance_id.module_id == 'shopify_odoo_v10':
            self.with_context(ctx).import_shopify_orders()
        #        if shop_obj.sent_thankyou_email:
        #            print"if shop_obj.sent_thankyou_email",shop_obj.sent_thankyou_email
        #            print"shop_obj.template_id",shop_obj.template_id
        #            if not shop_obj.template_id:
        #                raise UserError(_("Please Select Email Template For Thanks Email Template For Shop - %s")%(shop_obj.name))
        #               raise UserError(_('Please enter reason for product '+ rec.name.name or ""))
        #            self.sent_thankyou_email()
        #            self.sent_thankyou_email(cr,uid,shop_obj,context=context)

        shop_obj.write({'last_import_order_date': time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())})
        log_vals = {
            'activity': 'import_orders',
            'start_datetime': self._context.get('from_date', False),
            'end_datetime': datetime.datetime.now(),
            'shop_id': self._ids[0],
            'message': 'Successful'
        }
        log_obj.create(log_vals)
        #        log_obj.create(cr, uid, log_vals)
        return True

    def sent_thankyou_email(self):
        email_template_obj = self.env['email.template']
        order_obj = self.env['sale.order']
        order_ids = order_obj.search([('sent_thanksemail', '=', False), ('shop_id', '=', self.shop_obj.id)])
        for data in order_obj.browse(order_ids):
            if data.partner_id.email:
                shop_obj = self.browse(self._ids[0])
                mail = email_template_obj.send_mail(shop_obj.template_id, data.partner_id.id, True)
        return True

    def manageCountryCode(self, country_code):
        """
        This function is used to Manage country code
        parameters:
            country_code : character
        """
        self._cr.execute("SELECT id from res_country WHERE lower(name) = %s or lower(code) in %s",
                         (country_code.lower(), (country_code.lower(), country_code[:2].lower())))
        res = self._cr.fetchall()
        if not res:
            country_id = self.env['res.country'].create(
                {'code': country_code[:2].upper(), 'name': country_code.title()})
        else:
            country_id = res[0][0]
        return country_id

    def manageStateCode(self, state_code, country_id):
        print("=====state_code========", state_code)
        print("=====country_id========", country_id)
        '''
        This function is used to Manage StateCode 
        parameters: 
            state_code : character
            country_id : 
        '''
        state_name = re.sub('[^a-zA-Z ]*', '', state_code.upper())
        # self._cr.execute("SELECT id from res_country_state WHERE lower(name) = %s and lower(code) = %s AND country_id=%s", (state_name.lower(), (state_name[:3].lower()),country_id))
        self._cr.execute("SELECT id from res_country_state WHERE lower(code) = %s AND country_id=%s",
                         ((state_name[:3].lower()), country_id))
        res = self._cr.fetchall()
        if not res:
            state_id = self.env['res.country.state'].create(
                {'country_id': country_id, 'name': state_name.title(), 'code': state_name[:3].upper()})
            print("=====state_id========", state_id.id)
        else:
            state_id = res[0][0]
            print("=====state_id====123====", state_id)
        return state_id

    def updatePartnerInvoiceAddress(self, resultvals):
        print("===================resultvals===========", resultvals)
        partneradd_obj = self.env['res.partner']
        if resultvals.get('BillingCountryCode', False):
            country_id = self.manageCountryCode(resultvals['BillingCountryCode'])
        else:
            country_id = False

        if resultvals.get('BillingStateOrRegion', False):
            state_id = self.manageStateCode(resultvals['BillingStateOrRegion'], country_id)
            print("------state_id-------", type(state_id))
            if not type(state_id) == int:
                state_id = state_id.id
        else:
            state_id = False

        addressvals = {
            'name': resultvals['BillingName'],
            'street': resultvals.get('BillingAddressLine1', False),
            'street2': resultvals.get('BillingAddressLine2', False),
            'city': resultvals.get('BillingCity', False),
            'country_id': country_id,
            'state_id': state_id,
            'phone': resultvals.get('BillingPhone', False),
            'zip': resultvals.get('BillingPostalCode', False),
            'email': resultvals.get('BillingEmail', False),
            'type': 'invoice',
            'shop_id': resultvals.get('partner_shop', False)
        }
        print("****===>>addressvals", addressvals)
        #        if resultvals.get('UserID',False):
        #            addressvals.update({'ebay_user_id':resultvals['UserID']})
        ctx = self._context.copy()
        if ctx.get('shoppartnerinvoiceaddrvals', False):
            addressvals.update(ctx['shoppartnerinvoiceaddrvals'])
        partnerinvoice_ids = partneradd_obj.search(
            [('street', '=', resultvals.get('BillingAddressLine1') and resultvals['BillingAddressLine1'] or ''),
             ('zip', '=', resultvals.get('BillingPostalCode') and resultvals['BillingPostalCode'] or '')])
        #        partnerinvoice_ids = partneradd_obj.search([('name','=',resultvals['BillingName']),('street','=',resultvals.get('BillingAddressLine1') and resultvals['BillingAddressLine1'] or ''),('zip','=',resultvals.get('BillingPostalCode') and resultvals['BillingPostalCode'] or '')])
        print("partnerinvoice_ids", partnerinvoice_ids)
        if partnerinvoice_ids:
            partnerinvoice_id = partnerinvoice_ids[0]
            partnerinvoice_id.write(addressvals)
        else:
            print("partnerinvoice_ids_else")
            partnerinvoice_id = partneradd_obj.create(addressvals)
            print("partnerinvoice_id", partnerinvoice_id)
        self._cr.commit()
        print("partnerinvoice_ids==>>1>>", partnerinvoice_ids)
        return partnerinvoice_id

    def updatePartnerShippingAddress(self, resultvals):

        partneradd_obj = self.env['res.partner']

        country_id = False
        state_id = False

        if resultvals.get('ShippingCountryCode', False):
            country_id = self.manageCountryCode(resultvals['ShippingCountryCode'])

        if country_id and resultvals.get('ShippingStateOrRegion', False):
            state_id = self.manageStateCode(resultvals['ShippingStateOrRegion'], country_id)

        addressvals = {
            'name': resultvals['ShippingName'],
            'street': resultvals.get('ShippingAddressLine1', False),
            'street2': resultvals.get('ShippingAddressLine2', False),
            'city': resultvals.get('ShippingCity', False),
            'country_id': country_id,
            'state_id': state_id,
            'phone': resultvals.get('ShippingPhone', False),
            'zip': resultvals.get('ShippingPostalCode', False),
            'email': resultvals.get('ShippingEmail', False),
            'type': 'delivery',
            #            'ebay_user_id' :resultvals.get('UserID',False),
        }
        ctx = self._context.copy()
        if ctx.get('shoppartnershippingaddrvals', False):
            addressvals.update(ctx['shoppartnershippingaddrvals'])
        partnershippingadd_ids = partneradd_obj.search([('name', '=', resultvals['ShippingName']), (
            'street', '=', resultvals.get('ShippingAddressLine1') and resultvals['ShippingAddressLine1'] or ''), (
                                                            'zip', '=',
                                                            resultvals.get('ShippingPostalCode') and resultvals[
                                                                'ShippingPostalCode'])])
        if partnershippingadd_ids:
            partnershippingadd_id = partnershippingadd_ids[0]
            partnershippingadd_id.write(addressvals)
        else:
            partnershippingadd_id = partneradd_obj.create(addressvals)
        return partnershippingadd_id

    def import_listing(self, shop_id, product_id, resultvals):
        """
        This function is a super function willl be called for import listing of different shops
        parameters:
            shop_id :- integer
            product_id :- integer
            resultvals :- dictionary of all the order data
        """
        return True

    def createAccountTax(self, value, shop_id):
        accounttax_obj = self.env['account.tax']
        accounttax_id = accounttax_obj.create(
            {'type': 'percent', 'price_include': shop_id.tax_include, 'name': 'Sales Tax(' + str(value) + '%)',
             'amount': value, 'type_tax_use': 'sale'})
        #        accounttax_id = accounttax_obj.create(cr,uid,{'name':'Sales Tax(' + str(value) + '%)','amount':float(value)/100,'type_tax_use':'sale'})
        return accounttax_id

    def computeTax(self, shop_id, resultval):

        log_obj = self.env['ecommerce.logs']

        tax_id = []
        if float(resultval.get('ItemTax', 0.0)) > 0.0:
            if resultval.get('ItemTaxPercentage', False):
                ship_tax_vat = float(resultval['ItemTaxPercentage']) / 100.00
                # ship_tax_vat = float(resultval['ItemTaxPercentage'])
            else:
                if not shop_id.tax_include:
                    if resultval.get('ItemPriceTotal', False):
                        ship_tax_vat = float(resultval['ItemTax']) / float(resultval['ItemPriceTotal'])
                    else:
                        ship_tax_vat = float(resultval['ItemTax']) / float(resultval['ItemPrice'])
                else:
                    if resultval.get('ItemPriceTotal', False):
                        ship_tax_vat = float(resultval['ItemTax']) / (
                                float(resultval['ItemPriceTotal']) - float(resultval['ItemTax']))
                    else:
                        ship_tax_vat = float(resultval['ItemTax']) / (
                                float(resultval['ItemPrice']) - float(resultval['ItemTax']))

            #            ship_tax_percent= float(math.floor(ship_tax_percent))/100
            # changed, added a new search condition to check by company_id
            ship_tax_vat = ship_tax_vat * 100
            acctax_id = self.env['account.tax'].search([('type_tax_use', '=', 'sale'), ('amount', '=', ship_tax_vat),
                                                        ('price_include', '=', shop_id.tax_include)])
            #            acctax_id = self.pool.get('account.tax').search(cr,uid,[('type_tax_use', '=', 'sale'),('company_id', '=',shop_id.company_id.id), ('amount', '>=', ship_tax_vat - 0.001), ('amount', '<=', ship_tax_vat + 0.001)])

            #            log_obj.log_data(cr,uid,"test account tax",acctax_id);

            #            log_obj.log_data(cr,uid,"test shop_id.company_id.id account tax",shop_id.company_id.id)

            #            logger.info("test--------account---tax---- %s",acctax_id)
            #            logger.info("ship_tax_vat--------account---tax---- %s",ship_tax_vat)
            #            logger.info("test--shop_id.company_id.id------account---tax---- %s",shop_id.company_id.id)
            if not acctax_id:
                acctax_id = self.createAccountTax(ship_tax_vat, shop_id)
                tax_id = [(6, 0, [acctax_id][0].id)]
            else:
                tax_id = [(6, 0, [acctax_id[0].id])]
        return tax_id

    def createProduct(self, shop_id, product_details):
        """Logic for creating products in odoo
          Getting Product Category #"""
        ctx = self._context
        prodtemp_obj = self.env['product.template']
        prod_obj = self.env['product.product']
        prod_cat_obj = self.env['product.category']
        product_ids = prod_obj.search([('default_code', '=', product_details.get('SellerSKU', '').strip())])
        print("prod_cat_obj", prod_cat_obj)
        cat_ids = prod_cat_obj.search([])
        print("cat_ids", cat_ids)
        if not product_ids:
            template_vals = {
                'list_price': product_details.get('ItemPrice', 0.00),
                'purchase_ok': 'TRUE',
                'sale_ok': 'TRUE',
                'name': product_details['Title'],
                'type': 'product',
                #                'procure_method' : 'make_to_stock',
                'cost_method': 'average',
                'standard_price': 0.00,
                'categ_id': cat_ids[0].id,
                'weight_net': product_details.get('ItemWeight', 0.00),
                'default_code': product_details.get('SellerSKU', '').strip()
            }
            if ctx.get('shopproductvals', False):
                template_vals.update(ctx.get('shopproductvals'))
            template_id = prod_obj.create(template_vals)
            print("template_id", template_id)
            prod_id = prod_obj.search([('id', '=', template_id.id)])
        else:
            prod_id = prod_obj.search([('id', '=', product_ids[0].id)])
        ebay_exp_id = prod_id.write({'ebay_exported': True})
        return prod_id[0]

    def oe_status(self, sale_order_data, resultval):
        print("----------++++++++====WELCOME ALL=====+++++++++----------")
        inv_obj = self.env['account.move']
        if resultval.get('confirm', False):
            if sale_order_data.order_line:
                # confirm quotation
                sale_order_data.action_confirm()
                sale_order_data.action_invoice_create()
                self._cr.commit()
        invoice_ids = []
        if sale_order_data.name:
            invoice_ids = inv_obj.search([('origin', '=', sale_order_data.name)])
        print('========invoice_ids====>', invoice_ids)
        if len(invoice_ids):
            invoice = invoice_ids[0]
            invoice.action_invoice_open()
            if resultval.get('paid', False):
                context = {}
                if resultval.get('journal_id', False):
                    context.update({'journal_id': resultval['journal_id']})
                    self.env['pay.invoice'].with_context(context).pay_invoice(sale_order_data, invoice_ids[0])
        return True

    #       call_ids = self.search(cr,uid,[('invoice_id','=',open_act.id)])
    #       call_ids = self.search(cr,uid,[('invoice_id','=',open_act.id[0])])

    def manageSaleOrderLine(self, shop_id, saleorderid, resultval):
        ctx = self._context.copy()
        saleorder_obj = self.env['sale.order']
        saleorderline_obj = self.env['sale.order.line']
        product_obj = self.env['product.product']
        log_obj = self.env['ecommerce.logs']
        saleorderlineid = False
        product = ''
        # if resultval.has_key('product_id'):
        if 'product_id' in resultval:
            if not resultval['product_id']:
                print("IF not resultval['product_id']")
                product = self.with_context(ctx).createProduct(shop_id, resultval)
                logger.info('product==== %s', product)
                if isinstance(product, int):
                    product = product_obj.browse(product)
                else:
                    product = product
            else:
                print("else")
                product_id = resultval['product_id']
                logger.info('product_id==== %s', product_id)
                if isinstance(product_id, int):
                    product = product_obj.browse(product_id)
                else:

                    product = product_id
                logger.info('product==== %s', product)
                print("product product product", product)
        else:
            product = self.with_context(ctx).createProduct(shop_id, resultval)

        if not ctx.get('create_tax_product_line', False):
            tax_id = self.computeTax(shop_id, resultval) if float(resultval['ItemTax']) > 0.00 else False
        #            [(6, 0, [41])]
        else:
            tax_id = False

        if not tax_id:
            self._cr.execute(
                "select tax_id from product_taxes_rel where prod_id = '" + str(product.product_tmpl_id.id) + "'")
            for tax in self._cr.fetchall():
                if len(tax):
                    tax_id = [(6, 0, [tax[0]])]
                #                    tax_id = [(6, 0, [tax[0].id])]
                print("***======>>>tax_id", tax_id)
        # changed,it will get price unit from product if price = 0.00
        price_unit = float(resultval['ItemPrice'])

        includetax = float(resultval.get('ItemPriceTotal', False))
        if resultval.get('ItemTax', False):
            if not resultval.get('ItemPriceTotal', False):
                includetax = float(resultval.get('ItemPrice ', False)) + float(resultval['ItemTax'])
        if float(resultval.get('ItemPriceTotal', False)) >= 1.0:
            price_unit = includetax / float(resultval['QuantityOrdered'])

        logger.info('tax_id==== %s', tax_id)
        # if tax_id and isinstance(tax_id[0][2], (int, long)):
        if tax_id and isinstance(tax_id[0][2], (int)):
            tax_id = [(tax_id[0][0], tax_id[0][1], [tax_id[0][2]])]
        orderlinevals = {
            'order_id': saleorderid.id,
            'product_uom_qty': resultval['QuantityOrdered'],
            'product_uom': product.product_tmpl_id.uom_id.id,
            'name': product.product_tmpl_id.name,
            'price_unit': price_unit,
            'invoiced': False,
            'state': 'draft',
            'product_id': product.id,
            'tax_id': tax_id,
            'unique_sales_line_rec_no': resultval.get('unique_sales_line_rec_no')
        }
        print("===orderlinevals==>>>>>>>>", orderlinevals)
        logger.info('**********orderlinevals**** %s', orderlinevals)

        if ctx.get('shoporderlinevals', False):
            orderlinevals.update(ctx['shoporderlinevals'])

        # if resultval.has_key('product_id'):
        if 'product_id' in resultval:
            product_id = resultval['product_id']
            if resultval.get('listing_id', False):
                self.import_listing(shop_id, product_id, resultval)

        get_lineids = saleorderline_obj.search(
            [('unique_sales_line_rec_no', '=', resultval.get('unique_sales_line_rec_no')),
             ('product_id', '=', product.id), ('order_id', '=', saleorderid.id)])
        if not get_lineids:
            logger.info('orderlinevals==== %s', orderlinevals)
            saleorderlineid = saleorderline_obj.create(orderlinevals)
        else:
            saleorderlineid = get_lineids[0].id
        logger.info('**********saleorderlineid**** %s', saleorderlineid)
        return saleorderlineid

    def createShippingProduct(self):
        prod_obj = self.env['product.product']
        prodcateg_obj = self.env['product.category']
        print("prodcateg_obj", prodcateg_obj)
        categ_id = prodcateg_obj.search([('name', '=', 'Service')])
        print("categ_id", categ_id)
        if not categ_id:
            categ_id = prodcateg_obj.create({'name': 'Service', 'type': 'normal'})
        else:
            categ_id = categ_id[0]
        ctx = self._context.copy()
        prod_id = prod_obj.create(
            {'type': 'service', 'name': 'Shipping and Handling', 'default_code': ctx['shipping_product_default_code'],
             'categ_id': categ_id.id})
        return prod_id

    def manageSaleOrderLineShipping(self, shop_data, saleorderid, resultval):
        context = dict(self._context or {})
        saleorderline_obj = self.env['sale.order.line']
        product_obj = self.env['product.product']

        prod_shipping_id = product_obj.search([('default_code', '=', context['shipping_product_default_code'])])
        if not prod_shipping_id:
            prod_shipping_id = self.createShippingProduct()
        else:
            prod_shipping_id = prod_shipping_id[0]

        Shippingdiscount = float(resultval.get('ShippingDiscount', 0.00))
        shipping_price = float(resultval.get('ShippingPrice', 0.00))
        shipping_price = shipping_price - Shippingdiscount
        if shipping_price == 0.0:
            return False

        shiplineids = saleorderline_obj.search(
            [('order_id', '=', saleorderid.id), ('product_id', '=', prod_shipping_id.id)])
        # changed, here it will skip shipping price addition only for magento
        if shiplineids:
            if context.get('is_magento', False) or context.get('is_shopify'):
                return shiplineids[0]
            else:
                new_price_unit = shipping_price
                shiplineids[0].write({'price_unit': new_price_unit})
                return shiplineids[0]
        else:
            product = prod_shipping_id

            shiporderlinevals = {
                'order_id': saleorderid.id,
                'product_uom_qty': 1,
                'product_uom': product.product_tmpl_id.uom_id.id,
                'name': product.product_tmpl_id.name,
                'price_unit': shipping_price,
                'invoiced': False,
                'tax_id': '',
                'state': 'done',
                'product_id': prod_shipping_id.id,
            }
            shiplineid = saleorderline_obj.create(shiporderlinevals)
            #            cr.commit()
            return shiplineid

    def manageSaleOrder(self, shop_data, resultval):

        '''
        This function is used to create  sale orders
        parameters:
            shop_id :- integer
            resultvals :- dictionary of all the order data
        '''
        print("==manageSaleOrder==>", "called")
        saleorder_obj = self.env['sale.order']
        shop_obj = self.env['sale.shop']
        partner_obj = self.env['res.partner']
        payment_method_obj = self.env['payment.method.ecommerce']

        payment_id = False
        if self._context.get('order_search_clause', False):
            saleorderids = saleorder_obj.search(
                [('unique_sales_rec_no', '=', resultval['unique_sales_rec_no']), ('shop_id', '=', shop_data.id)])
            print("saleorderids-1-------->>", saleorderids)
        else:
            saleorderids = saleorder_obj.search(
                [('unique_sales_rec_no', '=', resultval['unique_sales_rec_no']), ('shop_id', '=', shop_data.id)])
        print("saleorderids--2------->>", saleorderids)

        if saleorderids:
            print("saleorderids", saleorderids)
            print("saleorderids_invoice_status", saleorderids[0].invoice_status)
            #            saleorder = saleorder_obj.browse(saleorderids[0])
            if saleorderids[0].invoice_status == 'invoiced':
                return False
            else:
                return saleorderids[0]

        resultval.update({'partner_shop': shop_data.id})
        partnerinvoiceaddress_id = self.updatePartnerInvoiceAddress(resultval) or False
        partner_id = partnerinvoiceaddress_id
        print("partner_id--------", partner_id)
        logger.info('invoice==== %s', partnerinvoiceaddress_id)
        if resultval.get('ShippingName', False):
            partnershippingaddress_id = self.updatePartnerShippingAddress(resultval) or False
        else:
            # partnershippingaddress_id = False
            # change false to partner_id
            partnershippingaddress_id = partner_id
        print("***=======>>partner_id", partner_id)
        if not partner_id or not (partnershippingaddress_id or partnerinvoiceaddress_id):
            """Skip it since the address info is wrong """
            return False
        pricelist_id = partner_id['property_product_pricelist'].id
        print("pricelist_id", pricelist_id)
        carrier_ids = []
        ctx = self._context.copy()
        if resultval.get('Carrier', False) and ctx.get('shipping_code_key', False):
            carrier_code_ebay = resultval.get('Carrier')
            carrier_ids = self.env['delivery.carrier'].search(
                [(ctx.get('shipping_code_key', False), '=', str(carrier_code_ebay))])
            if not carrier_ids:
                carrier_ids = self.env['delivery.carrier'].search([('name', '=', resultval['Carrier'])])

        carrier_id = carrier_ids[0].id if carrier_ids else False

        if ctx.get('date_format', False):
            date_order = time.strptime(resultval['PurchaseDate'], ctx['date_format'])
            date_order = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", date_order)
        else:
            date_order = resultval['PurchaseDate']
        print("resultval['PaymentMethod']", resultval['PaymentMethod'])
        logger.info('===resultval====>>>%s', resultval)
        logger.info('===PaymentMethod====>>>%s', resultval['PaymentMethod'])
        if resultval.get('PaymentMethod', False) and resultval['PaymentMethod'] != 'None':
            print("resultval.get('PaymentMethod',False) and resultval['PaymentMethod'] != 'None'")
            payment_ids = payment_method_obj.search([('code', '=', resultval['PaymentMethod'])])
            print("payment_ids", payment_ids)
            if payment_ids:
                payment_id = payment_ids[0]
                print("payment_id", payment_id)
            else:
                print("else----payment_ids")
                acq_obj = self.env['payment.acquirer'].search([])
                if acq_obj:
                    payment_id = payment_method_obj.create(
                        {'name': resultval['PaymentMethod'], 'code': resultval['PaymentMethod'],
                         'acquirer_id': acq_obj[0].id, 'acquirer_ref': acq_obj[0].name, 'partner_id': partner_id.id})
        print("===ctx====>>>", ctx)
        logger.info('===ctx====>>>%s', ctx)
        ordervals = {
            'picking_policy': shop_data.picking_policy or 'direct',
            'order_policy': resultval.get('order_policy', False) or 'picking',
            'partner_invoice_id': partnerinvoiceaddress_id.id,
            'date_order': date_order,
            'shop_id': shop_data.id,
            'partner_id': partner_id.id,
            'user_id': self._uid,
            #            'name' : resultval.get('unique_sales_rec_no',False),
            'partner_shipping_id': partnershippingaddress_id.id,
            'shipped': False,
            'state': 'draft',
            'pricelist_id': shop_data.pricelist_id.id,
            'warehouse_id': shop_data.warehouse_id and shop_data.warehouse_id.id,
            'payment_method_id': payment_id.id,
            'carrier_id': carrier_id,
            'unique_sales_rec_no': resultval.get('unique_sales_rec_no', False),
            'channel_carrier': resultval.get('Carrier', False),
            'import_unique_id': ctx['import_unique_id'],
            'external_transaction_id': resultval.get('ExternalTransactionID', False)
        }
        print("AAAA=====>>>>>ordervals", ordervals)
        if ctx.get('shopordervals', False):
            ordervals.update(ctx['shopordervals'])

        saleorderids = saleorder_obj.search(
            [('unique_sales_rec_no', '=', resultval['unique_sales_rec_no']), ('shop_id', '=', shop_data.id)])
        #        log_obj.log_data(cr,uid,"ordervals",ordervals);
        #        log_obj.log_data(cr,uid,"salesorderid",saleorderids);
        print("saleorderids", saleorderids)
        if not saleorderids:
            print("not saleorderids")
            saleorderid = saleorder_obj.create(ordervals)
            print("saleorderid", saleorderid)
        else:
            saleorderid = saleorderids[0]
        print("==saleorderid==>", saleorderid)
        return saleorderid

    def createOrderIndividual(self, shop_data, resultval):
        '''
        This function is used to create orders
        parameters:
            shop_data :- Browse records
            resultvals :- dictionary of all the order data
        '''
        saleorder_obj = self.env['sale.order']
        log_obj = self.env['ecommerce.logs']
        ctx = self._context.copy()
        print("======ctx====>", ctx)
        saleorderid = self.with_context(ctx).manageSaleOrder(shop_data, resultval)
        print("*****=======>>>>>saleorderid", saleorderid)
        if not saleorderid:
            return False

        sale_data = saleorderid
        #        log_obj.log_data(cr,uid,"context======",context)
        print("sale_data.import_unique_id==========>>>>", sale_data.import_unique_id)
        ctx = dict(self._context)
        if sale_data.import_unique_id == ctx['import_unique_id']:

            """ Order has been reversed bcoz in Sales order it comes in right order """

            saleorderlineid = self.with_context(ctx).manageSaleOrderLine(shop_data, saleorderid, resultval)

            if resultval.get('ItemTax', False) and float(resultval['ItemTax']) > 0.00 and ctx.get(
                    'create_tax_product_line', False):
                print("manageSaleOrderLineTax")
                self.manageSaleOrderLineTax(shop_data, saleorderid, resultval)

            if resultval.get('ShippingPrice', False) and float(resultval['ShippingPrice']) > 0.00:
                print("manageSaleOrderLineShipping")
                self.manageSaleOrderLineShipping(shop_data, saleorderid, resultval)

            logger.info('**********saleorderlineid**** %s', saleorderlineid)
        self._cr.commit()
        return saleorderid

    #    def createOrderIndividual(self,shop_data, resultval):
    #        '''
    #        This function is used to create orders
    #        parameters:
    #            shop_data :- Browse records
    #            resultvals :- dictionary of all the order data
    #        '''
    #        print "==createOrderIndividual==>","called"
    #        saleorder_obj = self.env['sale.order']
    #        print "==saleorder_obj==>",saleorder_obj
    #        print "==shop_data==>",shop_data
    #        print "==resultval==>",resultval
    #        saleorderid = self.manageSaleOrder(shop_data, resultval)
    #        print "==saleorderid==>",saleorderid
    #        if not saleorderid:
    #            return False
    #
    #        sale_data = saleorderid
    #        print"+++++++++++sale_data=======>>+++++++++++",sale_data
    #        log_obj.log_data(cr,uid,"context======",context)
    #        print"sale_data.import_unique_id==========>>>>",sale_data.import_unique_id
    #        ctx = dict(self._context)
    #        if sale_data.import_unique_id == ctx['import_unique_id']:
    #
    #            """ Order has been reversed bcoz in Sales order it comes in right order """
    #
    #            if resultval.get('ShippingPrice',False) and float(resultval['ShippingPrice']) > 0.00 :
    #                print"manageSaleOrderLineShipping"
    #                self.manageSaleOrderLineShipping(shop_data, saleorderid, resultval)
    #
    #            if resultval.get('ItemTax',False) and float(resultval['ItemTax']) > 0.00 and ctx.get('create_tax_product_line',False):
    #                print"manageSaleOrderLineTax"
    #                self.manageSaleOrderLineTax(shop_data, saleorderid, resultval)
    #
    #            saleorderlineid = self.manageSaleOrderLine(shop_data, saleorderid, resultval)
    #            print"QQQQQQQQQQQQQ++++++++++++++++++saleorderlineid",saleorderlineid
    #        self._cr.commit()
    #        return saleorderid

    def handleMissingOrders(self, shop_data, missed_resultvals):
        """
        This function is used to create missing orders
        parameters:
            shop_data :- integer
            resultvals :- dictionary of all the  misssing order data
        """
        count = 0
        while (missed_resultvals):
            """ count is to make sure loop doesn't go into endless iteraiton"""
            count = count + 1
            if count > 3:
                break

            resultvals = missed_resultvals[:]

            for resultval in resultvals:
                try:
                    resultval = self.get_payment_method(shop_data, resultval)
                    if not resultval.get('SellerSKU', False):
                        continue

                    saleorderid = self.createOrderIndividual(shop_data, resultval)
                    if not saleorderid:
                        continue

                    missed_resultvals.remove(resultval)
                    self.oe_status(saleorderid, resultval)
                    self.cr.commit()
                except Exception as e:
                    if str(e).find('concurrent update') != -1 or str(e).find('current transaction') != -1:
                        self.cr.rollback()
                        time.sleep(5)
                        pass

                    raise osv.except_osv(_('Error !'), e)

        return {}

    def get_payment_method(self, shop_data, resultval):
        """
        This function is used to Get the payment method from the order
        parameters:
            shop_data :- integer
            resultvals :- dictionary of the order data with the payment info
        """
        pay_obj = self.env['payment.method.ecommerce']
        log_obj = self.env['ecommerce.logs']
        print("SSSSSSSSSSSSSS++++shop_data++++++>>>>>>>>>>>>>>>", shop_data)
        #        log_obj.log_data(cr,uid,"shop======",shop_data)
        pay_ids = pay_obj.search([('shop_id', '=', shop_data.id)])

        # changed, initialized the keys to confirm and get paid
        resultval.update({'confirm': False})
        resultval.update({'journal_id': False})
        resultval.update({'paid': False})
        resultval.update({'order_policy': False})
        for pay in pay_ids:
            print("???????********???????????**********?????==========pay.name", pay.name)
            methods = (pay.name).split(',')
            payment_method = resultval.get('PaymentMethod', False) and resultval['PaymentMethod'] or ''
            print("###############??????payment_method???????#################", payment_method)
            print("###############??????pay.pay_invoice???????#################", pay.pay_invoice)
            print("###############??????pay.val_order???????#################", pay.val_order)
            print("###############??????pay.order_policy???????#################", pay.order_policy)
            print("###############??????pay.journal_id.id???????#################", pay.journal_id.id)
            if payment_method in methods:
                resultval.update({'paid': pay.pay_invoice})
                resultval.update({'confirm': pay.val_order})
                resultval.update({'order_policy': pay.order_policy})
                resultval.update({'journal_id': pay.journal_id.id})
                break
        return resultval

    def createOrder(self, shop_data, resultvals):
        '''
        This function is used to get the order data and pass data to functions to create the order and related things
        parameters:
            shop_data :- integer
            resultvals :- dictionary of all the order data
        '''
        print("HHHHHHHHHH************HHHHHHHHHHHHello=========>>>")
        saleorderid = False
        order_data = []
        #        context['import_type'] = 'api'
        ctx = dict(self._context)
        ctx.update({'import_type': 'api'})

        order_ids_confirm = []
        missed_resultvals = []
        missed_order_ids = []
        order_ids = []

        log_obj = self.env['ecommerce.logs']
        SKUs_missing = []

        for resultval in resultvals:
            #            try:
            resultval = self.get_payment_method(shop_data, resultval)
            print("===resultval=>>", resultval)
            if not resultval.get('SellerSKU', False):
                log_obj.log_data("No Seller SKU", resultval)
                SKUs_missing.append(resultval)
                continue

            saleorderid = self.with_context(ctx).createOrderIndividual(shop_data, resultval)
            print("saleorderid----->>>>>", saleorderid)
            #                pppp
            if not saleorderid:
                continue
            print("@@@@@@@@@@@@@@@@@=====order_ids_confirm=======>>>>>>>>", order_ids_confirm)
            #                log_obj.log_data(cr,uid,"order_ids_confirm======",order_ids_confirm)
            # changed, here it will update the payment and generate invoice for the collected order ids.
            if saleorderid not in order_ids:
                oe_data = {
                    'paid': resultval['paid'],
                    'confirm': resultval['confirm'],
                    'order_policy': resultval['order_policy'],
                    'journal_id': resultval['journal_id'],
                    'order_id': saleorderid
                }
                order_ids_confirm.append(oe_data)
                order_ids.append(saleorderid)
            print("*******  +++++ order_ids_confirm ++++++  ********", order_ids_confirm)

        #            except Exception as e:
        #                if str(e).find('concurrent update') != -1 or str(e).find('current transaction') != -1:
        #                    cr.rollback()
        #                    time.sleep(20)
        #                    pass
        #                else:
        #                    raise osv.except_osv(_('Error !'),e)

        for order_id_result in order_ids_confirm:
            print("SSSSSSSSSSSSSSSSSSSSS********order_id_result*****SSSSSSSSSSSSSSSSSSSSSSSSSS")
            print("SSSSSSSSSSSSSSSSSSSSS********order_id_result*****SSSSSSSSSSSSSSSSSSSSSSSSSS", order_id_result)
            print("========order_id_result['order_id'],order_id_result===========", order_id_result['order_id'],
                  order_id_result)
            log_obj.log_data("order_id_result['order_id']", order_id_result['order_id'])
            #            try:
            """ Function for Confirming Orders and Paying the Invoices """
            self.oe_status(order_id_result['order_id'], order_id_result)
        #            except Exception as e:
        #                pass

        #        self.handleMissingOrders(cr,uid,shop_data,missed_resultvals,context)
        if SKUs_missing:
            un_imported_items = []
            for sku_missing in SKUs_missing:
                un_imported_items.append(sku_missing.get('ItemID').strip('[]'))
                un_imported_items = list(set(un_imported_items))
            raise UserError(
                "Unable to import orders with the following item id's due to missing SKU's. "
                "\n Please update product SKU's and try again.\n %s" % un_imported_items)

        return order_ids

    # @api.depends('name')
    # def _marketplace_image(self):
    #     colorize, image_path, image = False, False, False
    #
    #     shop_obj = self
    #     if shop_obj.instance_id.module_id == 'amazon_odoo_v10':
    #         image_path = get_module_resource('base_ecommerce_v10', 'static/images', 'amazon_logo.png')
    #
    #     if shop_obj.instance_id.module_id == 'ebay_odoo_v10':
    #         image_path = get_module_resource('base_ecommerce_v10', 'static/images', 'EBay_logo.png')
    #
    #     # if shop_obj.instance_id.module_id == 'jet_teckzilla':
    #     #     self.marketplace_image = "Text which will be replaced"
    #
    #     if shop_obj.instance_id.module_id == 'magento_odoo_v10':
    #         image_path = get_module_resource('base_ecommerce_v10', 'static/images', 'logomagento.png')
    #
    #     # if shop_obj.instance_id.module_id == 'groupon_teckzilla':
    #     #     self.marketplace_image = "Text which will be replaced"
    #
    #     # if shop_obj.instance_id.module_id == 'woocommerce_odoo':
    #     #     self.marketplace_image = "Text which will be replaced"
    #
    #     if shop_obj.instance_id.module_id == 'shopify_odoo_v10':
    #         image_path = get_module_resource('base_ecommerce_v10', 'static/images', 'shopify.png')
    #
    #     if image_path:
    #         with open(image_path, 'rb') as f:
    #             image = f.read()
    #
    #     image = tools.image_resize_image_big(image.encode('base64'))
    #     self.marketplace_image = image


# sale_shop()

class sale_order(models.Model):
    _inherit = 'sale.order'

    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    shop_id = fields.Many2one('sale.shop', string="Shop")
    unique_sales_rec_no = fields.Char(string="Order Unique ID", size=100)
    external_transaction_id = fields.Char(string="External Transaction ID", size=64, readonly=True)
    channel_carrier = fields.Char(string="Channel Carrier", size=100)
    carrier_tracking_ref = fields.Char(string="Carrier Tracking Reference", size=100)
    import_unique_id = fields.Char(string="Import ID", size=200)
    payment_method_id = fields.Many2one('payment.method.ecommerce', string="Payment Method")
    track_exported = fields.Boolean(string="Track Exported", default=False)
    sent_thanksemail = fields.Boolean(string="Sent Thanks Email")
    product_details = fields.Many2one('product.product', related='order_line.product_id', string='Product')
    products_sku = fields.Char(related='product_id.default_code')
    products_name = fields.Char(related='product_id.name', string='Product')
    products_image = fields.Image(related='product_id.image_1920')
    # products_image = fields.Binary("Image")
    marketplace_image = fields.Binary(related='shop_id.marketplace_image')

    def _get_sale_order_name(self, shop_id):
        shop_obj = self.env['sale.shop']
        shop = shop_obj.browse(shop_id)
        if shop_id and not self.name.startswith(shop.prefix or '') and not self.name.endswith(shop.suffix or ''):
            return str(shop.prefix or '') + self.name + str(shop.suffix or '')
        return self.name

    @api.model
    def create(self, vals):
        print("vals", vals)
        if vals.get('shop_id', False) and vals.get('name'):
            vals.update({'name': self._get_sale_order_name(vals['shop_id'], vals['name'])})

        return super(sale_order, self).create(vals)

    #        return super(sale_order, self).create(cr, uid, vals, context=context)

    def generate_payment_with_journal(self, journal_id, partner_id, amount, payment_ref, entry_name, date,
                                      should_validate, defaults=None):
        voucher_obj = self.env['account.move']
        voucher_line_obj = self.env['account.move.line']
        data = voucher_obj.onchange_partner_id([], partner_id, journal_id, int(amount), False, 'receipt', date)['value']
        account_id = data['account_id']
        currency_id = self.env.context.get('currency_id', False)
        statement_vals = {
            'reference': 'ST_' + entry_name,
            'journal_id': journal_id,
            'amount': amount,
            'date': date,
            'partner_id': partner_id,
            'account_id': account_id,
            'type': 'receipt',
            'currency_id': currency_id,
            'number': '/'
        }
        statement_id = voucher_obj.create(statement_vals)
        self.env.context.update(
            {'type': 'receipt', 'partner_id': partner_id, 'journal_id': journal_id, 'default_type': 'cr'})
        #        context.update({'type': 'receipt', 'partner_id': partner_id, 'journal_id': journal_id, 'default_type': 'cr'})
        line_account_id = voucher_line_obj.default_get(['account_id'])['account_id']
        statement_line_vals = {
            'voucher_id': statement_id,
            'amount': amount,
            'account_id': line_account_id,
            'type': 'cr',
        }
        statement_line_id = voucher_line_obj.create(statement_line_vals)

        return statement_id
