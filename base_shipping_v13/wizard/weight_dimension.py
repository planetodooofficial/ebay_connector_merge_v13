from odoo import fields, api

from odoo import api, fields, models
from odoo.exceptions import UserError


class WeightDimension(models.TransientModel):
    _name = 'weight.dimension'

    update_weight_dimension_id = fields.Many2one('update.weight.dimension', 'Update Weight Dimension')
    product_id = fields.Many2one('product.product', 'Product')
    # default_code=fields.Char('SKU',related='product_id.default_code')
    default_code = fields.Char('SKU')
    weight = fields.Float('Weight(KGS)')
    length = fields.Integer('Length(mm)')
    width = fields.Integer('Width(mm)')
    height = fields.Integer('Height(mm)')
