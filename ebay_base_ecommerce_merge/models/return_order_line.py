from odoo import models, fields


# class refund_order(models.Model):
#     _name = "refund.order"
#     _description = "Refund Orders"
#
#     name = fields.Char('Refund Id')
#     amount = fields.Float('Amount')
#     return_status = fields.Char('Return Status')
#     refund_type = fields.Selection([('ORIGINAL_SHIPPING', 'Orignal Shipping'),
#                              ('OTHER', 'Other'),
#                              ('PURCHASE_PRICE', 'Purchase Price'),
#                              ('RESTOCKING_FEE', 'Restocking Fee')], string='Refund Fee Type')
#     note = fields.Text('Comment')
#     return_line = fields.One2many('refund.order.line','refund_id',string='Return Item Line')
#     refund_status = fields.Char('Refund Status')
#     state = fields.Selection([('new', 'New'),
#                                 ('done', 'Done'),
#                                ], string='Status',default='new')
#     def issue_refund(self):
#         context = self._context.copy()
#         sale_data = self.env[context.get('active_model')].search([('id','=',context.get('active_id'))])
#         connection_obj = self.env['ebayerp.osv']
#         shop_obj = sale_data.shop_id
#         refund_status = connection_obj.call(shop_obj.instance_id, 'issueRefund', self.name,self.amount,self.refund_type,self.note,shop_obj.instance_id.site_id.site)
#         self.write({'refund_status':refund_status,
#                     'state':'done'})
#         return True


class return_order_line(models.Model):
    _name = "return.order.line"

    def _compute_product_id(self):
        for rec in self:
            if rec.item_id:
                listing_data = self.env['ebay.product.listing'].search([('name', '=', rec.item_id)])
                if listing_data:
                    rec.product_id = listing_data.product_id.id

    order_id = fields.Many2one('sale.order', 'Sale Order')
    item_id = fields.Char('Item Id')
    product_id = fields.Many2one('product.product', 'Product', compute='_compute_product_id')
    transaction_id = fields.Char('Transaction Id')
    return_qty = fields.Integer('Return Qty')
