from odoo import models, fields


class delivery_carrier(models.Model):
    _inherit = "delivery.carrier"

    carrier_code = fields.Char(tring='Carrier Code', size=150)
    ship_type = fields.Selection([('standard', 'Standard'), ('expedited', 'Expedited')], string='Shipping Service Type',
                                 default='standard')


class res_partner(models.Model):
    _inherit = "res.partner"

    ebay_user_id = fields.Char(string='Ebay Customer ID', size=256)