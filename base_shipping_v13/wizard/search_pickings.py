from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger('sale')


class search_picking(models.TransientModel):
    _name = 'search.picking.base'

    from_date = fields.Date('From')
    to_date = fields.Date('To')
    recieve_date = fields.Date('Recieve Date')
    process_date = fields.Date('Process Date')
    tracking_no = fields.Char('Tracking Number')

    postcode = fields.Char('Post Code')
    cust_name = fields.Char('Customer Name')
    street = fields.Char('Street')
    street2 = fields.Char('Street2')
    city = fields.Char('city')
    country_id = fields.Many2one('res.country', 'Country')
    state_id = fields.Many2one('res.country.state', 'State')
    email = fields.Char('Email')

    reference_no = fields.Char('Reference Number')
    note = fields.Text('Order Note')

    processed = fields.Boolean('Processed Order')

    def search_pickings(self):

        domain = []
        if self.processed:
            domain.append(('manifested', '=', True))
        else:
            domain.append(('manifested', '=', False))
        if self.postcode:
            domain.append(('partner_id.zip', 'ilike', self.postcode))
        if self.email:
            domain.append(('partner_id.email', '=', self.email))
        if self.tracking_no:
            domain.append(('carrier_tracking_ref', '=', self.tracking_no))
        if self.from_date:
            domain.append(('create_date', '>=', self.from_date))
        if self.to_date:
            domain.append(('create_date', '<=', self.to_date))
        if self.recieve_date:
            domain.append(('create_date', '=', self.recieve_date))
        if self.process_date:
            domain.append(('manifested_date', '=', self.process_date))
        if self.reference_no:
            domain.append(('origin', 'ilike', self.reference_no))
        if self.street:
            domain.append(('partner_id.street', '=', self.street))
        if self.street2:
            domain.append(('partner_id.street2', '=', self.street2))
        if self.city:
            domain.append(('partner_id.city', 'ilike', self.city))
        if self.country_id:
            domain.append(('partner_id.country_id', '=', self.country_id))
        if self.state_id:
            domain.append(('partner_id.state_id', '=', self.state_id))
        if self.cust_name:
            domain.append(('partner_id.name', '=', self.cust_name))

        picking_ids = self.env['stock.picking'].search(domain)
        pick_ids = [x.id for x in picking_ids]
        view = self.env.ref('stock.vpicktree')
        result = {
            'name': _('Search Results'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'views': [(view.id, 'tree')],
            'view_id': view.id,
            'target': 'self',
            'domain': [('id', 'in', pick_ids)],
        }
        return result
