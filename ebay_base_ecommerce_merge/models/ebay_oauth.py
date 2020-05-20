from odoo import models, fields, api, _


class ebay_oauth(models.Model):
    _name = 'ebay.oauth'

    dev_id = fields.Char(string='Dev ID', size=256, required=True, help="eBay Dev ID")
    app_id = fields.Char(string='App ID', size=256, required=True, help="eBay App ID")
    cert_id = fields.Char(string='Cert ID', size=256, required=True, help="eBay Cert ID")
    app_auth_url = fields.Char(string='Auth URL', required=True)
    run_name = fields.Char(string='RuName Value', required=True)
