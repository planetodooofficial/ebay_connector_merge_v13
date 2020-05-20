from odoo import api, fields, models, _
import logging

logger = logging.getLogger(__name__)


class ecommerce_logs(models.Model):
    _name = "ecommerce.logs"

    start_datetime = fields.Datetime(string='Start time', readonly="1")
    end_datetime = fields.Datetime(string='End Date', readonly="1")
    shop_id = fields.Many2one('sale.shop', string='Shop', readonly="1")
    message = fields.Text(string='Message', readonly="1")
    activity = fields.Selection([
        ('import_orders', 'Import Orders'),
        ('update_order_status', 'Update Order Status'),
        ('import_price', 'Import Price'),
        ('export_price', 'Export Price'),
        ('import_stock', 'Import Stock'),
        ('export_stock', 'Export Stock'),
    ], string='Activity')

    def log_data(self, print_log, message):
        res_user_obj = self.env['res.users']
        res_user_data = res_user_obj.browse(self._uid)
        if res_user_data:
            if res_user_data.company_id.debugging_mode:
                logger.info(print_log + "---> %s", message)
        return True


class res_company(models.Model):
    _inherit = "res.company"

    debugging_mode = fields.Boolean(string='Enable Debugging Mode')
    local_media_repository = fields.Char(string='Images Repository Path', size=256, required=True,
                                         help='Local mounted path on odoo server where all your images are stored.')

    def get_local_media_repository(self, id=None):
        if id:
            return self.browse(id).local_media_repository
        user = self.env['res.users'].browse(self._uid)
        return user.company_id.local_media_repository


