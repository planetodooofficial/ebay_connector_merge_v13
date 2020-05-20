from odoo import models, fields, api, _


class base_carrier_code(models.Model):
    _name = 'base.carrier.code'

    name = fields.Char('Tariff Code')
    select_service = fields.Many2one('select.service', string='Service')
