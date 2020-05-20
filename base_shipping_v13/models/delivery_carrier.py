from odoo import models, fields, api, _


class delivery_carrier(models.Model):
    _inherit = 'delivery.carrier'

    select_service = fields.Many2one('select.service', string='Select Service')
    service_name = fields.Char('Service Name', related='select_service.name', store=True)
    # base_carrier_code = fields.Char('Carrier Code')
    base_carrier_code = fields.Many2one('base.carrier.code', 'Carrier Code')


class select_service(models.Model):
    _name = 'select.service'

    name = fields.Char('Service name')
