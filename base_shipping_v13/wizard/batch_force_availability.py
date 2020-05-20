from odoo import fields, api
from odoo.models import TransientModel
from odoo.tools.translate import _


class StockPickingMassAction(TransientModel):
    _name = 'stock.picking.mass.action'
    _description = 'Stock Picking Mass Action'

    @api.model
    def _default_force_availability(self):
        return self.env.context.get('force_availability', False)

    force_availability = fields.Boolean(
        string='Force Stock Availability', default=_default_force_availability,
        help="check this box if you want to force the availability"
             " of the selected Pickings.")

    def mass_action(self):
        self.ensure_one()
        picking_obj = self.env['stock.picking']
        picking_ids = self.env.context.get('active_ids')

        # Get confirmed pickings
        domain = [('state', 'in', ['confirmed', 'partially_available']),
                  ('id', 'in', picking_ids)]
        # changed scheduled_date
        confirmed_picking_lst = picking_obj.search(domain, order='scheduled_date')

        # Force availability if asked
        if self.force_availability:
            confirmed_picking_lst.force_assign()
