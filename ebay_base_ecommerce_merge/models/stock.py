import logging

from odoo import models, fields

logger = logging.getLogger(__name__)


class stock_picking(models.Model):
    _inherit = "stock.picking"

    shop_id = fields.Many2one('sale.shop', string='Shop')
    track_exported = fields.Boolean(string="Track Exported", default=False)


class stock_move(models.Model):
    _name = "stock.move"
    _inherit = "stock.move"

    def action_done(self):
        context = self._context.copy()
        if context is None:
            context = {}
        action_done = super(stock_move, self).action_done()
        real_time_update_listing = []
        shop_obj = self.env['sale.shop']
        ebay_list_obj = self.env['ebay.product.listing']

        for move in self:
            ebay_listing = move.product_id.prodlisting_ids
            for ebay_listing_data in ebay_listing:
                if ebay_listing_data.shop_id.stock_update_on_time:
                    if ebay_listing_data.id not in real_time_update_listing:
                        real_time_update_listing.append(ebay_listing_data.id)

        context = dict(context)
        context['update_stock'] = True
        if len(real_time_update_listing):
            ebay_shop_id = shop_obj.search([('ebay_shop', '=', True), ('stock_update_on_time', '=', True)])

            for shop_id in ebay_shop_id:
                new_listing = []
                for list_data in ebay_list_obj.browse(real_time_update_listing):
                    if shop_id == list_data.shop_id.id:
                        new_listing.append(list_data.id)

                if len(new_listing):
                    context['eactive_ids'] = new_listing
                    shop_obj.with_context(context).export_stock_and_price([shop_id.id])
        return action_done
