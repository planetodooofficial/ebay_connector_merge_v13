from odoo import api, fields, models, _

import logging

logger = logging.getLogger(__name__)


class res_partner(models.Model):
    _inherit = 'res.partner'

    shop_id = fields.Many2one('sale.shop', string='Source')
    ebay_user_id = fields.Char(string='UserID')