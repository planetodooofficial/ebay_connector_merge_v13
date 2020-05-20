import json
import logging
import urllib.request
from xml.dom.minidom import parseString
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ebaysdk.exception import ConnectionError
from ebaysdk.trading import Connection as Trading

logger = logging.getLogger('attribute')


class product_attribute_value(models.Model):
    _inherit = "product.attribute.value"

    value = fields.Char(string='Label', size=100)
    imported = fields.Boolean(string='Imported', default=False)
    ebay_product_id1 = fields.Many2one('product.product', string='Product')
    ebay_product_id2 = fields.Many2one('product.product', string='Product')
    shop_id3 = fields.Many2one('list.item', string='Shop id3')
    shop_id4 = fields.Many2one('list.item', string='Shop id4')


class product_attribute(models.Model):
    _inherit = "product.attribute"

    def get_leaf(self):
        res = True
        for rec in self:
            attrs_ids = self.search([('parent_id', '=', rec.id)])
            if not attrs_ids:
                rec.write({'is_leaf': True})
        return res

    attribute_code = fields.Char(string='Attribute Code', size=255)
    attr_set_id = fields.Many2one('product.attribute.set', string='Attribute Set')
    parent_id = fields.Many2one('product.attribute', string='Parent', default=False)
    pattern = fields.Selection([('choice', 'Choice'),
                                ('restricted', 'Ristricted'),
                                ('other', 'Other')], string='Product Type Pattern')

    is_leaf = fields.Boolean(string="Leaf", default=False)
    imported = fields.Boolean(string="Imported")
    variation_enabled = fields.Boolean(string='variation Enabled', help="If checked then this attribute is variation")


class product_attribute_set(models.Model):
    _name = "product.attribute.set"

    name = fields.Char(string='Name', size=255)
    code = fields.Char(string='Code', size=255)
    imported = fields.Boolean(string='Import')
    shop_id = fields.Many2one('sale.shop', string='Shop')
    attribute_ids = fields.One2many('product.attribute', 'attr_set_id', string='Attributes')
    ebay_category_id = fields.Integer(string='Category ID', help="Ebay Category ID")
    item_specifics = fields.Boolean(string='Item Specific Enabled',
                                    help="If checked then this category supports Custom Item Specifics", readonly=True,
                                    default=False)
    class_ad = fields.Boolean(string='Classified Ad Enabled',
                              help="If checked then this category supports the Classified Ad Format", readonly=True,
                              default=False)
    condition_enabled = fields.Boolean('Condition Enabled',
                                       help="If checked then this category supports item condition", readonly=True,
                                       default=False)
    catlog_enabled = fields.Boolean(string='Catlaog Enabled', help="If checked then this category is catalog enabled",
                                    readonly=True, default=False)
    shop = fields.Boolean(string="Shop")

    def ebay_sdk(self):
        try:
            api = Trading(config_file=False, appid='ReviveOn-ZestERP-PRD-05d7504c4-7e62e952',
                          token='AgAAAA**AQAAAA**aAAAAA**514uWg**nY+sHZ2PrBmdj6wVnY+sEZ2PrA2dj6AFloCgAJaEogidj6x9nY+seQ**4M8DAA**AAMAAA**pJTxWPk5v7uA4HdkanTFWcUAzgQdjHsD7hreui/eFJdqrxw3PsgdsK+WGP5fY8urMJ9rmIozaeVq5Wh7rU9FchyAwcTYu42LFXXM+7Q/TGo+KhsDuWL2WGz4t4JtuFw4iVJpWWLnkdGNkMed6S+xYjvfSU0XOYKIRnSIcs4JfzK1uwgCuSaUS1ajmH5ZCpVciLjtm9pQvguT4j3odY5CoGh5wsRYMJnjvYvQqCI114Nx65XBmShPKRLVZOfvO6OWYL6bkBhd8grmR3JFYMGj5LZz3Z3lF/Xy7Qdfz9Lpjt49k7TThwXzZw0jjsKCUUJBdfEvFBg/qZcVPreCDgm3h8X3p55e78mBnqV+OQFmIh38Kk1ZKAaYiicOHxRvVxTcZib+6bBB/5Jb1gBYTLDdqYZ6BC0B6TYc49BsOE8yMAe3/VTm0V5SZw0R3WAiyy3Csj7pFy8KN6oxXwLJsC8v2RqqnueejMPp08Vn6kRohh5uoLFSiTdxMoam5Bim/3KLXH7qNeM4y720Rw/FIantaeezF5kVug9Ic/9gq84nXj1rqRfeZfRrr2BofIBF9rjiLmZ5YHHhNKXCMsLctNgCyOosPeMc08jhZIS53ELYqZ/RB8fVCIHXAZyXFy5Vg5D/2YP9T+4NELQjJgYIx2EYh079iNJMxE9jBYOsKQP5qshRuJqOCZvubTFCiJN9e0MPLaaUz5569T2Xxi9QTlSBLuaMNmEGHeFCwGKt31cWgx9oEQroxRKBE7unHGNUY9Ws',
                          certid='PRD-5d7504c480f9-39be-4693-bc3c-5485', devid='12b0abb8-96e5-4f07-b012-97081166a3a8',
                          warnings=True)

            # pass in an open file
            # the Requests module will close the file
            files = {'file': ('EbayImage', open('/opt/on_copy.jpg', 'rb'))}

            pictureData = {
                "WarningLevel": "High",
                "PictureName": "WorldLeaders"
            }

            response = api.execute('UploadSiteHostedPictures', pictureData, files=files)
            print(response.dict())
            json.dumps(api)
        except ConnectionError as e:
            print(e)
            print(e.response.dict())

    def get_attribute(self):
        """
        This function is used to Get the attributes from Ebay
        parameters:
            No Parameter
        """
        shop_obj = self.env['sale.shop']
        connection_obj = self.env['ebayerp.osv']
        results = False
        attribute = False

        if self:
            print("-------self._ids----", self._ids)
            if isinstance(self, int):
                ids = [self._ids]
            # if isinstance(self, int):
            #     ids = [ids]
            attr_set_obj = self
            site_id_value = attr_set_obj.shop_id
            if site_id_value:
                siteid = site_id_value.instance_id.site_id.site
            else:
                siteid = ''
            category_code = attr_set_obj.code
            if category_code:
                search_ebay_true = [attr_set_obj.shop_id.id]
                if search_ebay_true:
                    leafcategory = ''
                    inst_lnk = shop_obj.browse(search_ebay_true[0]).instance_id
                    app_id = inst_lnk.app_id
                    if inst_lnk.sandbox:
                        server_url = "http://open.api.sandbox.ebay.com/"
                    else:
                        server_url = "http://open.api.ebay.com/"
                    if app_id and server_url and siteid and category_code:
                        concate_url = """ %sshopping?callname=GetCategoryInfo&appid=%s&siteid=%s&CategoryID=%s&version=743&responseencoding=XML""" % (
                            server_url, app_id, siteid, category_code)
                        try:
                            urlopen = urllib.request.urlopen(concate_url)
                        except Exception as e:
                            urlopen = ''
                        if urlopen:
                            mystring = urlopen.read()
                            if mystring:
                                response = parseString(mystring)
                                if response:
                                    if response.getElementsByTagName('Ack'):
                                        if response.getElementsByTagName('Ack')[0].childNodes[0].data == 'Success':
                                            if response.getElementsByTagName('LeafCategory'):
                                                leafcategory = \
                                                    response.getElementsByTagName('LeafCategory')[0].childNodes[0].data
                                                if leafcategory == 'false':
                                                    raise UserError("Warning ! Category is not a Leaf Category")
                                                elif leafcategory == 'true':
                                                    leafcategory = 'true'
                                            else:
                                                raise Warning(_('Category is Invalid on Current Site'))
                                        elif response.getElementsByTagName('Ack')[0].childNodes[0].data == 'Failure':
                                            long_message = response.getElementsByTagName('LongMessage')[0].childNodes[
                                                0].data
                                            raise Warning(_('%s') % long_message)
                    if leafcategory == 'true':
                        results = connection_obj.call(inst_lnk, 'GetCategory2CS', category_code, siteid)

                        results1 = connection_obj.call(inst_lnk, 'GetCategoryFeatures', category_code, siteid)

                        if results1:
                            if results1.get('ItemSpecificsEnabled', False) == 'Enabled':
                                self.write({'item_specifics': True})
                            if results1.get('AdFormatEnabled', False) == 'ClassifiedAdEnabled':
                                self.write({'class_ad': True})
                            if results1.get('ConditionEnabled', False) == 'Disabled':
                                self.write({'condition_enabled': True})

        return True

    def get_category_specifics(self):
        """
        This function is used to Get Category specifics from Ebay
        parameters:
            No Parameter
        """
        results = False
        attribute = False
        shop_obj = self.env['sale.shop']
        connection_obj = self.env['ebayerp.osv']
        attribute_obj = self.env['product.attribute']
        attribute_val_obj = self.env['product.attribute.value']

        if self:
            if isinstance(self, int):
                ids = [self._ids]
            # if isinstance(self, long ):
            #     ids = [ids]
            attr_set_obj = self
            siteid = attr_set_obj.shop_id.instance_id.site_id.site
            category_code = attr_set_obj.code
            if category_code:
                search_ebay_true = [attr_set_obj.shop_id.id]
                if search_ebay_true:
                    leafcategory = ''
                    inst_lnk = shop_obj.browse(search_ebay_true[0]).instance_id
                    app_id = inst_lnk.app_id
                    if inst_lnk.sandbox:
                        server_url = "http://open.api.sandbox.ebay.com/"
                    else:
                        server_url = "http://open.api.ebay.com/"
                    if app_id and server_url and siteid and category_code:
                        concate_url = """ %sshopping?callname=GetCategoryInfo&appid=%s&siteid=%s&CategoryID=%s&version=743&responseencoding=XML""" % (
                            server_url, app_id, siteid, category_code)
                        try:
                            urlopen = urllib.request.urlopen(concate_url)
                        except Exception as e:
                            urlopen = ''
                        if urlopen:
                            mystring = urlopen.read()
                            if mystring:
                                response = parseString(mystring)
                                if response:
                                    if response.getElementsByTagName('Ack'):
                                        if response.getElementsByTagName('Ack')[0].childNodes[0].data == 'Success':
                                            if response.getElementsByTagName('LeafCategory'):
                                                leafcategory = \
                                                    response.getElementsByTagName('LeafCategory')[0].childNodes[0].data
                                                if leafcategory == 'false':
                                                    raise Warning(_("Category is not a Leaf Category"))
                                                elif leafcategory == 'true':
                                                    leafcategory = 'true'
                                            else:
                                                raise Warning(_("Category is Invalid on Current Site"))
                                        elif response.getElementsByTagName('Ack')[0].childNodes[0].data == 'Failure':
                                            long_message = response.getElementsByTagName('LongMessage')[0].childNodes[
                                                0].data
                                            raise Warning(_("%s") % long_message)
                    if leafcategory == 'true':
                        results = connection_obj.call(inst_lnk, 'GetCategorySpecifics', category_code, siteid)
                        for item in results:
                            search_id = attribute_obj.search(
                                [('attr_set_id', '=', self[0].id), ('attribute_code', '=', item)])
                            if not search_id:
                                var = True
                                if results[item]:
                                    if results[item][0] == 'novariation':
                                        var = False
                                att_id = attribute_obj.create({'attr_set_id': self[0].id, 'name': item.encode("utf-8"),
                                                               'attribute_code': item.encode("utf-8"),
                                                               'variation_enabled': var})
                                if len(results[item]):
                                    for val in results[item]:
                                        att_val_id = attribute_val_obj.create(
                                            {'attribute_id': att_id.id, 'name': val, 'value': val})

        return True

    @api.onchange('shop_id')
    def on_shop_change(self):
        if self.shop_id.ebay_shop:
            self.shop = True
        else:
            self.shop = False


class product_attribute_info(models.Model):
    _name = "product.attribute.info"

    name = fields.Many2one('product.attribute', string='Attribute', required=True)
    value = fields.Many2one('product.attribute.value', string='Values')
    value_text = fields.Text(string='Text')
    ebay_product_id1 = fields.Many2one('product.product', string='Product')
    ebay_product_id2 = fields.Many2one('product.product', string='Product')
    shop_id3 = fields.Many2one('list.item', string='Shop id3')
    shop_id4 = fields.Many2one('list.item', string='Shop id4')

