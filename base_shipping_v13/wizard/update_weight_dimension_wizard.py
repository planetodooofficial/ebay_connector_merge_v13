from odoo import fields, api
from odoo import api, fields, models
from odoo.exceptions import UserError


class UpdateWeightDimension(models.TransientModel):
    _name = 'update.weight.dimension'
    _description = 'Update Wight and Dimension'

    weight = fields.Float('Weight')
    length = fields.Integer('Length')
    width = fields.Integer('Width')
    height = fields.Integer('Height')

    @api.model
    def update_dim(self):
        pickings = self.env['stock.picking'].browse(self._context.get('active_ids'))
        list = []
        dict_to_list = []
        pick_list = []
        for p in pickings:
            if not p.state == 'done' or not p.state == 'cancel':
                for m in p.move_lines:
                    if m.product_id.type == 'service':
                        continue
                    list.append(m.product_id.id)
                pick_list.append(p)
        if list:
            for d in set(list):
                # dict_to_list.append(d)
                prod_id = self.env['product.product'].browse(d)
                dict_to_list.append({'product_id': d, 'default_code': prod_id.default_code, 'weight': prod_id.weight,
                                     'length': prod_id.length, 'width': prod_id.width, 'height': prod_id.height})
        return dict_to_list

    product_lines = fields.One2many('weight.dimension', 'update_weight_dimension_id', string='Weight Dimension',
                                    default=update_dim)

    def update_product_data(self):
        for prod in self.product_lines:
            prod.product_id.write(
                {'weight': prod.weight, 'length': prod.length, 'width': prod.width, 'height': prod.height})
            self.env.cr.commit()
        pickings = self.env['stock.picking'].browse(self._context.get('active_ids'))

        product_id = False
        for p in pickings:
            length = 0
            width = 0
            height = 0
            weight = 0.00
            # if self.origin:
            #     sale_id = self.env['sale.order'].search([('name', '=', self.origin)])
            heavy_weight = 0.00
            for line in p.move_lines:
                # if line.product_id.weight:
                if line.product_id.weight >= heavy_weight:
                    heavy_weight = line.product_id.weight
                    product_id = line.product_id
            if product_id:
                # prod_id=self.env['product.product'].browse('product_id')
                length = product_id.length
                width = product_id.width
                height = product_id.height
                weight = product_id.weight
                vals = {'length': length,
                        'width': width,
                        'height': height,
                        'weight': weight,
                        'is_wizard_weight': True,
                        }
                if product_id.length and product_id.width and product_id.height and product_id.weight:
                    vals['state'] = 'assigned'
                p.write(vals)

        return True
