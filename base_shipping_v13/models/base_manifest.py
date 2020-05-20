from odoo import models, fields, api, _
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class base_manifest(models.Model):
    _name = 'base.manifest'

    name = fields.Char('Name')
    batch_no = fields.Char('Batch')
    manifest_lines = fields.One2many('base.manifest.lines', 'manifest_id', string='Delivery Orders')
    state = fields.Selection([('draft', 'New'),
                              ('closed', 'Closed')],
                             'Status', readonly=True, index=True, copy=False, store=True, default='draft')
    date = fields.Date('Date')
    user_id = fields.Many2one('res.users', 'User')
    error_log = fields.Text('Error Logs')
    service_provider = fields.Char('Service Provider Name')
    base_manifest_ref = fields.Text('Manifest Reference')
    base_manifest_desc = fields.Text('Manifest Description')
    account_id = fields.Char('Account ID')
    account_name = fields.Char('Account Name')

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('base.manifest') or _('New')
        res = super(base_manifest, self).create(vals)
        if res.manifest_lines:
            for line in res.manifest_lines:
                picking_id = line.picking_id
                picking_id.manifested = True

        return res

    def write(self, vals):

        for manifest in self:
            if manifest.manifest_lines:
                for line in manifest.manifest_lines:
                    picking_id = line.picking_id
                    picking_id.manifested = True
        return super(base_manifest, self).write(vals)

    def unlink(self):
        for manifest in self:
            if manifest.manifest_lines:
                for line in manifest.manifest_lines:
                    picking_id = line.picking_id
                    picking_id.manifested = False

        return super(base_manifest, self).unlink()

    def close_manifest(self):
        date = datetime.now()
        # for mani in self.manifest_lines:
        # wiz = self.env['stock.immediate.transfer'].create({'pick_ids': [(4, mani.picking_id.id)]})
        # wiz.process()
        # mani.picking_id.action_done()
        return self.write({'state': 'closed', 'date': date})

    def print_manifest(self):
        report_xml_pool = self.env['ir.actions.report']
        datas = {'ids': self.id}
        result = self.env.ref('base_shipping_v13.base_manifest_report').report_action([self.id])
        return result


class manifest_lines(models.Model):
    _name = 'base.manifest.lines'

    def unlink(self):
        self.picking_id.manifested = False
        return super(manifest_lines, self).unlink()

    manifest_id = fields.Many2one('base.manifest', string='Manifest')
    picking_id = fields.Many2one('stock.picking', string='Delivery Order',
                                 domain=[('label_printed', '=', True), ('manifested', '=', False)])
    carrier_id = fields.Many2one('delivery.carrier', string='Delivery Carrier', related='picking_id.carrier_id')
