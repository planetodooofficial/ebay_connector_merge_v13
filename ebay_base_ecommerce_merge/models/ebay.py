from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.http import request
import base64
import json
import urllib
# from urllib.parse import urlparse
from datetime import datetime, timedelta
import requests
import logging

logger = logging.getLogger(__name__)


class sales_channel_instance(models.Model):
    _inherit = 'sales.channel.instance'

    @api.model
    def create(self, vals):
        if self.sandbox:
            vals['server_url'] = 'https://api.sandbox.ebay.com/ws/api.dll'
        else:
            vals.update({'server_url': 'https://api.ebay.com/ws/api.dll'})
        return super(sales_channel_instance, self).create(vals)

    def write(self, vals):
        if self.sandbox:
            vals['server_url'] = 'https://api.sandbox.ebay.com/ws/api.dll'
        else:
            vals.update({'server_url': 'https://api.ebay.com/ws/api.dll'})
        return super(sales_channel_instance, self).write(vals)

    ebayuser_id = fields.Char(string='User ID', size=256, help="eBay User ID")
    dev_id = fields.Char(string='Dev ID', size=256, help="eBay Dev ID")
    app_id = fields.Char(string='App ID', size=256, help="eBay App ID")
    cert_id = fields.Char(string='Cert ID', size=256, help="eBay Cert ID")
    auth_token = fields.Text(string='OAuth Token', help="eBay Token")
    site_id = fields.Many2one('ebay.site', string='Site')
    sandbox = fields.Boolean(string='Sandbox')
    server_url = fields.Char(string='Server Url', size=255)
    ebay_oauth = fields.Boolean(string='Use eBay Oauth', default=1)
    refresh_token = fields.Char(string='Refresh Token')
    auth_token_expiry = fields.Datetime('OAuth Token Expiry Date')
    refresh_token_expiry = fields.Datetime('Refresh Token Expiry Date')
    auth_n_auth_token = fields.Char('Auth Token')

    def get_authorization_code(self):
        callbck_url = request.env['ir.config_parameter'].get_param('web.base.url')
        state_dict = {
            'db_name': request.session.get('db'),
            'res_id': self.id,
            'url': callbck_url
        }
        state_json = json.dumps(state_dict)
        encoded_params = base64.urlsafe_b64encode(state_json.encode('utf-8'))
        # print("----encoded_params", encoded_params)
        encoded_params = encoded_params.decode('utf-8')
        # print("------", encoded_params)
        ebay_outh = self.env['ebay.oauth'].search([])
        scope = "https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/buy.order.readonly https://api.ebay.com/oauth/api_scope/buy.guest.order https://api.ebay.com/oauth/api_scope/sell.marketing.readonly https://api.ebay.com/oauth/api_scope/sell.marketing https://api.ebay.com/oauth/api_scope/sell.inventory.readonly https://api.ebay.com/oauth/api_scope/sell.inventory https://api.ebay.com/oauth/api_scope/sell.account.readonly https://api.ebay.com/oauth/api_scope/sell.account https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly https://api.ebay.com/oauth/api_scope/sell.fulfillment https://api.ebay.com/oauth/api_scope/sell.analytics.readonly https://api.ebay.com/oauth/api_scope/sell.marketplace.insights.readonly https://api.ebay.com/oauth/api_scope/commerce.catalog.readonly https://api.ebay.com/oauth/api_scope/buy.shopping.cart https://api.ebay.com/oauth/api_scope/buy.offer.auction https://api.ebay.com/oauth/api_scope/commerce.identity.readonly https://api.ebay.com/oauth/api_scope/commerce.identity.email.readonly https://api.ebay.com/oauth/api_scope/commerce.identity.phone.readonly https://api.ebay.com/oauth/api_scope/commerce.identity.address.readonly https://api.ebay.com/oauth/api_scope/commerce.identity.name.readonly https://api.ebay.com/oauth/api_scope/commerce.identity.status.readonly https://api.ebay.com/oauth/api_scope/sell.finances https://api.ebay.com/oauth/api_scope/sell.item.draft https://api.ebay.com/oauth/api_scope/sell.payment.dispute https://api.ebay.com/oauth/api_scope/sell.item"
        final_scope = urllib.parse.quote(scope)
        if not ebay_outh:
            raise UserError(_("eBay App credentials not found"))
        url = ebay_outh[0].app_auth_url
        # url = 'https://signin.ebay.com/authorize?client_id=Abhishek-OdooTest-PRD-b8dfd86bc-7c49bfad&response_type=code&redirect_uri=Abhishek_Ingole-Abhishek-OdooTe-yugjhedr&scope=https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/sell.marketing.readonly https://api.ebay.com/oauth/api_scope/sell.marketing https://api.ebay.com/oauth/api_scope/sell.inventory.readonly https://api.ebay.com/oauth/api_scope/sell.inventory https://api.ebay.com/oauth/api_scope/sell.account.readonly https://api.ebay.com/oauth/api_scope/sell.account https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly https://api.ebay.com/oauth/api_scope/sell.fulfillment https://api.ebay.com/oauth/api_scope/sell.analytics.readonly'
        state_param = '&grant_type=authorization_code' + '&scope=' + final_scope + '&state=' + str(encoded_params)
        url += state_param
        return {
            'name': 'Go to website',
            'res_model': 'ir.actions.act_url',
            'type': 'ir.actions.act_url',
            'target': 'current',
            'url': url
        }

    def renew_token(self):
        client_id = self.app_id
        client_secret = self.cert_id
        outh = client_id + ':' + client_secret
        # basic=outh.encode("utf-8")
        basic = base64.b64encode(outh.encode('utf-8'))
        # scope = "https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/sell.marketing.readonly https://api.ebay.com/oauth/api_scope/sell.marketing https://api.ebay.com/oauth/api_scope/sell.inventory.readonly https://api.ebay.com/oauth/api_scope/sell.inventory https://api.ebay.com/oauth/api_scope/sell.account.readonly https://api.ebay.com/oauth/api_scope/sell.account https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly https://api.ebay.com/oauth/api_scope/sell.fulfillment https://api.ebay.com/oauth/api_scope/sell.analytics.readonly"
        scope = "https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/buy.order.readonly https://api.ebay.com/oauth/api_scope/buy.guest.order https://api.ebay.com/oauth/api_scope/sell.marketing.readonly https://api.ebay.com/oauth/api_scope/sell.marketing https://api.ebay.com/oauth/api_scope/sell.inventory.readonly https://api.ebay.com/oauth/api_scope/sell.inventory https://api.ebay.com/oauth/api_scope/sell.account.readonly https://api.ebay.com/oauth/api_scope/sell.account https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly https://api.ebay.com/oauth/api_scope/sell.fulfillment https://api.ebay.com/oauth/api_scope/sell.analytics.readonly https://api.ebay.com/oauth/api_scope/sell.marketplace.insights.readonly https://api.ebay.com/oauth/api_scope/commerce.catalog.readonly https://api.ebay.com/oauth/api_scope/buy.shopping.cart https://api.ebay.com/oauth/api_scope/buy.offer.auction https://api.ebay.com/oauth/api_scope/commerce.identity.readonly https://api.ebay.com/oauth/api_scope/commerce.identity.email.readonly https://api.ebay.com/oauth/api_scope/commerce.identity.phone.readonly https://api.ebay.com/oauth/api_scope/commerce.identity.address.readonly https://api.ebay.com/oauth/api_scope/commerce.identity.name.readonly https://api.ebay.com/oauth/api_scope/commerce.identity.status.readonly https://api.ebay.com/oauth/api_scope/sell.finances https://api.ebay.com/oauth/api_scope/sell.item.draft https://api.ebay.com/oauth/api_scope/sell.payment.dispute https://api.ebay.com/oauth/api_scope/sell.item"
        final_scope = urllib.parse.quote(scope)
        if self.sandbox:
            request_url = 'https://api.sandbox.ebay.com/identity/v1/oauth2/token'
        else:
            request_url = 'https://api.ebay.com/identity/v1/oauth2/token'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': 'Basic ' + basic.decode('utf-8'),
        }
        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            'scope': final_scope
        }
        resp = requests.post(url=request_url, data=payload, headers=headers)
        print("--------resp--------", json.loads(resp.text))
        logger.info("---resp-----%s", json.loads(resp.text))
        if resp.status_code == requests.codes.ok:
            post_data = json.loads(resp.text)
            token = post_data.get('access_token', False)
            self.auth_token = token
            self.auth_token_expiry = datetime.now() + timedelta(seconds=int(post_data.get('expires_in', False)))
        return True

    @api.model
    def run_schedular_renew_token(self):
        ebay_instnce = self.search([])
        for instance in ebay_instnce:
            if instance.ebay_oauth and instance.refresh_token:
                instance.renew_token()
        return True

    def create_stores(self):
        sale_obj = self.env['sale.shop']
        instance_obj = self
        res = super(sales_channel_instance, self).create_stores()
        if instance_obj.module_id == 'ebay_base_ecommerce_merge':
            res.write({'ebay_shop': True})
        return res
