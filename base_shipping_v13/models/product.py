from odoo import models, fields, api, _


class product_product(models.Model):
    _inherit = 'product.product'

    length = fields.Integer('Length(mm)')
    width = fields.Integer('Width(mm)')
    height = fields.Integer('Height(mm)')


class product_template(models.Model):
    _inherit = 'product.template'

    length = fields.Integer('Length(mm)', inverse='_set_length_wid_height', store=True)
    width = fields.Integer('Width(mm)', inverse='_set_length_wid_height', store=True)
    height = fields.Integer('Height(mm)', inverse='_set_length_wid_height', store=True)

    # @api.depends('product_variant_ids', 'product_variant_ids.length')
    # def _compute_length(self):
    #     unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
    #     # for template in unique_variants:
    #     #     template.length = template.product_variant_ids.length
    #     for template in (self - unique_variants):
    #         template.length = ''

    def _set_length_wid_height(self):
        if len(self.product_variant_ids) == 1:
            self.product_variant_ids.length = self.length
            self.product_variant_ids.width = self.width
            self.product_variant_ids.height = self.height

    # @api.depends('product_variant_ids', 'product_variant_ids.width')
    # def _compute_width(self):
    #     unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
    #     for template in unique_variants:
    #         template.width = template.product_variant_ids.width
    #     for template in (self - unique_variants):
    #         template.width = ''
    #
    # def _set_width(self):
    #     if len(self.product_variant_ids) == 1:
    #         self.product_variant_ids.width = self.width
    #
    #
    # @api.depends('product_variant_ids', 'product_variant_ids.height')
    # def _compute_height(self):
    #     unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
    #     for template in unique_variants:
    #         template.height = template.product_variant_ids.height
    #     for template in (self - unique_variants):
    #         template.height = ''
    #
    # def _set_height(self):
    #     if len(self.product_variant_ids) == 1:
    #         self.product_variant_ids.height = self.height
