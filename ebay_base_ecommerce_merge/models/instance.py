import base64

from odoo import api, fields, models, tools
from odoo.modules.module import get_module_resource


# from PIL import Image


class sales_channel_instance(models.Model):
    """ For instance of Sales Channel"""
    _name = 'sales.channel.instance'

    def _get_installed_module(self):
        sel_obj = self.env['ir.module.module']
        sele_ids = sel_obj.search([('name', 'in',
                                    ['magento_2_v10', 'magento_odoo_v10', 'ebay_base_ecommerce_merge', 'amazon_odoo_v11',
                                     'woocommerce_odoo', 'virtuemart_odoo']), ('state', '=', 'installed')])
        print("**********sele_ids**************", sele_ids)
        select = []
        for s in sele_ids:
            select.append((str(s.name), s.shortdesc))
        print("#########select######################", select)
        return select

    name = fields.Char(string='Name', size=64, required=True)
    module_id = fields.Selection(_get_installed_module, string='Module', size=100)
    # image = fields.Binary(compute='_get_default_image')
    image = fields.Image(string="Image", max_width=64, max_height=64, compute='_get_default_image')

    @api.model
    def get_module_id(self, module_id):
        return {'value': {'m_id': module_id}}

    @api.model
    def _get_default_image(self):

        # if partner_type in ['other'] and parent_id:
        #     parent_image = self.browse(parent_id).image
        #     image = parent_image and parent_image.decode('base64') or None
        image_path, colorize = False, False

        if self.module_id == 'amazon_odoo_v11':
            image_path = get_module_resource('ebay_base_ecommerce_merge', 'static/images', 'amazon_logo.png')

        if self.module_id == 'ebay_base_ecommerce_merge':
            image_path = get_module_resource('ebay_base_ecommerce_merge', 'static/images', 'EBay_logo.png')

        if self.module_id == 'magento_odoo_v10':
            image_path = get_module_resource('ebay_base_ecommerce_merge', 'static/images', 'logomagento.png')

        if self.module_id == 'shopify_odoo_v10':
            image_path = get_module_resource('ebay_base_ecommerce_merge', 'static/images', 'shopify.png')

        # if image_path:
        #     with open(image_path, 'rb') as f:
        #         image = f.read()
        # if image_path:
        #     f = open(image_path, 'rb')
        #     image = f.read()
        # image=Image.open(image_path)

        # if image and colorize:
        #     image = tools.image_colorize(image)

        # self.image = tools.image_resize_image_big(image.encode('base64'))
        # self.image = base64.b64encode(image).decode('ascii')
        self.image = base64.b64encode(open(image_path, 'rb').read())

    def create_stores(self):
        """ For create store of Sales Channel """
        (instances,) = self
        shop_obj = self.env['sale.shop']
        shop_ids = shop_obj.search([('instance_id', '=', self[0].id)])
        payment_ids = self.env['account.payment.term'].search([])

        if not shop_ids:
            shop_data = {
                'sale_channel_shop': True,
                'name': instances.name + ' Shop',
                'payment_default_id': payment_ids[0].id,
                'warehouse_id': 1,
                'instance_id': self[0].id,
                'marketplace_image': instances.image,
                'order_policy': 'prepaid'
            }
            shop_id = shop_obj.create(shop_data)
        else:
            shop_id = shop_ids[0]
        return shop_id


class module_selection(models.Model):
    """ Manage selection for Multi Sales Channel"""
    _name = "module.selection"

    name = fields.Char(string='Name', size=64)
    module = fields.Char(string='Module', size=255)
    is_installed = fields.Boolean(string='install')
    no_instance = fields.Integer(string='Instance')
    code = fields.Integer(string='Code')
