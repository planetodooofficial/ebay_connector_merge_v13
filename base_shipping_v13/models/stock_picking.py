from odoo import models, fields, api, _
from odoo.exceptions import Warning
import datetime
import base64
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_round
import logging

logger = logging.getLogger(__name__)


class stock_picking(models.Model):
    _inherit = 'stock.picking'

    label_printed = fields.Boolean(string='Label Printed')
    label_printed_date = fields.Datetime('Label Printed Date')
    label_printed_uid = fields.Many2one('res.users', 'User')
    label_generated = fields.Boolean(string='Label Generated')
    label_generated_date = fields.Datetime('Label Generate Date')
    label_generated_uid = fields.Many2one('res.users', 'User')
    shipment_created = fields.Boolean(string='Shipment Created')
    shipment_created_date = fields.Datetime(string='Shipment Created Date')
    shipment_created_uid = fields.Many2one('res.users', 'User')
    picklist_printed = fields.Boolean(string='Picklist Printed')
    manifested = fields.Boolean(string='Added to Manifest')
    error_log = fields.Text(string='Error log')
    faulty = fields.Boolean(string='Faulty')

    products_sku = fields.Char(related='product_id.default_code')
    products_name = fields.Char(related='product_id.name')

    # manifest_id = fields.Many2one('royalmail.manifest','Manifest')
    manifested_date = fields.Datetime(string='Manifested Date')
    # replacing with old one this is already in delivery module
    # carrier_tracking_ref = fields.Char(string='Carrier Tracking Reference', copy=False)

    length = fields.Integer(string='Package Length (mm)', default='1')
    width = fields.Integer(string='Package Width (mm)', default='1')
    height = fields.Integer(string='Package Height (mm)', default='1')

    customer_postcode = fields.Char(related='partner_id.zip')
    customer_country = fields.Many2one(related='partner_id.country_id')
    is_wizard_weight = fields.Boolean('Wizard weight')
    state = fields.Selection(selection_add=[('needs_package_details', 'Needs Package Details')], string='Status', compute='_compute_state',
        copy=False, index=True, readonly=True, store=True, track_visibility='onchange',
        help=" * Draft: not confirmed yet and will not be scheduled until confirmed.\n"
             " * Waiting Another Operation: waiting for another move to proceed before it becomes automatically available (e.g. in Make-To-Order flows).\n"
             " * Waiting: if it is not ready to be sent because the required products could not be reserved.\n"
             " * Ready: products are reserved and ready to be sent. If the shipping policy is 'As soon as possible' this happens as soon as anything is reserved.\n"
             " * Done: has been processed, can't be modified or cancelled anymore.\n"
             " * Cancelled: has been cancelled, can't be confirmed anymore.")
    # to hide and show shipping setting, shipping info tabs in internal transfer picking
    picking_internal_type = fields.Char(compute='_compute_picking_type', string='internal type')

    @api.depends('picking_type_id')
    def _compute_picking_type(self):
        if self.picking_type_id and (
                'Sequence internal' in self.picking_type_id.sequence_id.name or 'Sequence in' in self.picking_type_id.sequence_id.name):
            self.picking_internal_type = False
        elif self.picking_type_id:
            self.picking_internal_type = True
        else:
            self.picking_internal_type = False

    # For needs package details
    @api.depends('move_type', 'move_lines.state', 'move_lines.picking_id')
    def _compute_state(self):
        if not self.move_lines:
            self.state = 'draft'
        elif any(move.state == 'draft' for move in self.move_lines):  # TDE FIXME: should be all ?
            self.state = 'draft'
        elif all(move.state == 'cancel' for move in self.move_lines):
            self.state = 'cancel'
        elif all(move.state in ['cancel', 'done'] for move in self.move_lines):
            self.state = 'done'
        else:
            relevant_move_state = self.move_lines._get_relevant_state_among_moves()
            if relevant_move_state == 'partially_available':
                if 'Sequence internal' in self.picking_type_id.sequence_id.name or 'Sequence in' in self.picking_type_id.sequence_id.name or (
                        self.origin and 'Return of' in self.origin) or self.picking_type_id.code in ['incoming',
                                                                                                     'mrp_operation']:
                    self.state = 'assigned'
                elif not self.shipping_weight or not self.length or not self.width or not self.height:
                    if self.picking_type_id.warehouse_id.delivery_steps == 'pick_pack_ship':
                        if self.picking_type_id.name == 'Pack':
                            self.state = 'needs_package_details'
                        else:
                            self.state = relevant_move_state
                    if self.picking_type_id.warehouse_id.delivery_steps == 'pick_ship':
                        if self.picking_type_id.name == 'Pick':
                            self.state = 'needs_package_details'
                        else:
                            self.state = relevant_move_state
                    if self.picking_type_id.warehouse_id.delivery_steps == 'ship_only':
                        self.state = 'needs_package_details'
                else:
                    self.state = 'assigned'
            else:

                if relevant_move_state == 'assigned':
                    if 'Sequence internal' in self.picking_type_id.sequence_id.name or 'Sequence in' in self.picking_type_id.sequence_id.name or (
                            self.origin and 'Return of' in self.origin) or self.picking_type_id.code in ['incoming',
                                                                                                         'mrp_operation']:
                        self.state = relevant_move_state
                    elif not self.shipping_weight or not self.length or not self.width or not self.height:
                        if self.picking_type_id.warehouse_id.delivery_steps == 'pick_pack_ship':
                            if self.picking_type_id.name == 'Pack':
                                self.state = 'needs_package_details'
                            else:
                                self.state = relevant_move_state
                        if self.picking_type_id.warehouse_id.delivery_steps == 'pick_ship':
                            if self.picking_type_id.name == 'Pick':
                                self.state = 'needs_package_details'
                            else:
                                self.state = relevant_move_state
                        if self.picking_type_id.warehouse_id.delivery_steps == 'ship_only':
                            self.state = 'needs_package_details'
                    else:
                        self.state = relevant_move_state
                else:
                    self.state = relevant_move_state

    @api.depends('state', 'is_locked')
    def _compute_show_validate(self):
        for picking in self:
            if self._context.get('planned_picking') and picking.state == 'draft':
                picking.show_validate = False
            elif picking.state not in (
                    'draft', 'confirmed', 'assigned', 'needs_package_details') or not picking.is_locked:
                picking.show_validate = False
            else:
                picking.show_validate = True

    def update_tracking_ref(self):
        order_id = self.env['sale.order'].search([('name', '=', self.origin)])
        vals = {'carrier_id': self.carrier_id.id}
        if self.carrier_tracking_ref:
            vals['carrier_tracking_ref'] = self.carrier_tracking_ref
        else:
            vals['carrier_tracking_ref'] = self.origin
        order_id.write(vals)
        return True

    @api.depends('move_line_ids')
    def _compute_bulk_weight(self):
        weight = 0.0
        packop = False
        normal = False
        for move_line in self.move_line_ids:
            if move_line.product_id and not move_line.result_package_id:
                weight += move_line.product_uom_id._compute_quantity(move_line.qty_done,
                                                                     move_line.product_id.uom_id) * move_line.product_id.weight
        if self.is_wizard_weight:
            packop = False
        else:
            if weight >= 0.0:
                packop = True
            else:
                packop = False
        if packop:
            self.weight_bulk = weight
        else:
            self.weight_bulk = self.weight

    def create_attachment(self, pick_id, attach_id):
        filename = pick_id.name or pick_id.origin
        filename += '.pdf'
        data_attach = {
            'name': filename,
            'datas_fname': filename,
            'datas': attach_id.datas,
            'description': 'Label',
            'res_name': self.name,
            'res_model': 'stock.picking',
            'res_id': self.id,
        }
        attachment_id = self.env['ir.attachment'].create(data_attach)
        if attachment_id:
            return attachment_id
        else:
            return False

    def new_action_done(self):
        if not self.carrier_tracking_ref:
            self.env['update.base.picking'].with_context({'picking_id': self.id}).create_shipment()

    def base_manifest(self):
        for picking in self:
            manifest_obj = self.env['base.manifest']
            # need to check state
            # if picking.carrier_id.select_service.name == 'Royalmail':
            #     return

            current_date = datetime.datetime.now().strftime('%Y-%m-%d')
            manifest_id = manifest_obj.search(
                [('service_provider', '=', picking.carrier_id.select_service.name), ('state', '=', 'draft'),
                 ('date', '=', current_date)])
            if manifest_id:
                update_manifest_id = manifest_id[0].write(
                    {'manifest_lines': [(0, 0, {'picking_id': picking.id, 'carrier_id': picking.carrier_id.id})]})
                if update_manifest_id == True:
                    return manifest_id[0]
            else:
                created_manifest_id = manifest_obj.create({
                    'service_provider': picking.carrier_id.select_service.name,
                    'date': datetime.datetime.now(),
                    'user_id': picking._uid,
                    'base_manifest_ref': datetime.datetime.now().strftime("%m-%d-%Y"),
                    'base_manifest_desc': picking.carrier_id.select_service.name,
                    'manifest_lines': [(0, 0, {'picking_id': picking.id, 'carrier_id': picking.carrier_id.id})]
                })
                return created_manifest_id

    def action_done(self):
        picking_obj = self.env['stock.picking']
        picking_attach = self.env['ir.attachment']
        if self.picking_type_id.code in ['incoming', 'mrp_operation']:
            res = super(stock_picking, self).action_done()
        elif 'Sequence internal' in self.picking_type_id.sequence_id.name or 'Sequence in' in self.picking_type_id.sequence_id.name:
            res = super(stock_picking, self).action_done()
        else:
            if self.origin and 'Return of' in self.origin:
                res = super(stock_picking, self).action_done()
            else:
                if self.manifested == True:
                    res = super(stock_picking, self).action_done()
                else:
                    if self.picking_type_id.warehouse_id.delivery_steps == 'ship_only':
                        ship_attach_id = picking_attach.search(
                            [('res_id', '=', self.id), ('res_name', '=', self.name)])
                        if not self.carrier_tracking_ref and not ship_attach_id and not self.shipment_created:
                            self.new_action_done()
                        ship_has_attach_id = picking_attach.search(
                            [('res_id', '=', self.id), ('res_name', '=', self.name)])
                        if self.carrier_tracking_ref or ship_has_attach_id or self.shipment_created:
                            if self.carrier_id.select_service.name == 'Royalmail':
                                # return
                                res = super(stock_picking, self).action_done()
                            manifest_id = self.base_manifest()
                            if manifest_id:
                                res = super(stock_picking, self).action_done()
                            else:
                                return
                        else:
                            return

                    if self.picking_type_id.warehouse_id.delivery_steps == 'pick_ship':
                        if self.picking_type_id.name == 'Pick':
                            pick_ship_attach_id = picking_attach.search(
                                [('res_id', '=', self.id), ('res_name', '=', self.name)])
                            if not self.carrier_tracking_ref and not pick_ship_attach_id and not self.shipment_created:
                                self.new_action_done()
                            pick_ship_has_new_attach_id = picking_attach.search(
                                [('res_id', '=', self.id), ('res_name', '=', self.name)])
                            if self.carrier_tracking_ref or pick_ship_has_new_attach_id or self.shipment_created:
                                res = super(stock_picking, self).action_done()
                        else:
                            if self.picking_type_id.name == 'Delivery Orders':
                                pick_ship_del_attach_id = picking_attach.search(
                                    [('res_id', '=', self.id), ('res_name', '=', self.name)])
                                if not self.carrier_tracking_ref and not pick_ship_del_attach_id and not self.shipment_created:
                                    pick_id = picking_obj.search([('origin', '=', self.origin), ('state', '=', 'done')])
                                    if pick_id.picking_type_id.name == 'Pick':
                                        # added extra
                                        # if pick_id.carrier_id.select_service.name != 'Royalmail':
                                        #
                                        pick_ship_has_attach_id = picking_attach.search(
                                            [('res_id', '=', pick_id.id), ('res_name', '=', pick_id.name)])
                                        if pick_id.carrier_tracking_ref or pick_ship_has_attach_id or pick_id.shipment_created:
                                            data_vals = {'carrier_tracking_ref': pick_id.carrier_tracking_ref,
                                                         'carrier_id': pick_id.carrier_id.id, 'shipment_created': True,
                                                         'faulty': False, 'error_log': ''}
                                            if pick_ship_has_attach_id:
                                                delivery_attach_id = self.create_attachment(pick_id,
                                                                                            pick_ship_has_attach_id)
                                                if delivery_attach_id:
                                                    data_vals['label_generated'] = True

                                            pick_obj = self.write(data_vals)
                                            if pick_id.carrier_id.select_service.name == 'Royalmail':
                                                # return
                                                res = super(stock_picking, self).action_done()
                                            else:
                                                if pick_obj:
                                                    manifest_id = self.base_manifest()
                                                    if manifest_id:
                                                        res = super(stock_picking, self).action_done()
                                                    else:
                                                        return
                                        else:
                                            return
                                else:
                                    if self.carrier_id.select_service.name == 'Royalmail':
                                        # return
                                        res = super(stock_picking, self).action_done()
                                    manifest_id = self.base_manifest()
                                    if manifest_id:
                                        res = super(stock_picking, self).action_done()
                                    else:
                                        return

                    if self.picking_type_id.warehouse_id.delivery_steps == 'pick_pack_ship':
                        if self.picking_type_id.name == 'Pick':
                            res = super(stock_picking, self).action_done()
                        if self.picking_type_id.name == 'Pack':
                            pack_ship_attach_id = picking_attach.search(
                                [('res_id', '=', self.id), ('res_name', '=', self.name)])
                            if not self.carrier_tracking_ref and not pack_ship_attach_id and not self.shipment_created:
                                self.new_action_done()
                            pack_ship_has_new_attach_id = picking_attach.search(
                                [('res_id', '=', self.id), ('res_name', '=', self.name)])
                            if self.carrier_tracking_ref or pack_ship_has_new_attach_id or self.shipment_created:
                                res = super(stock_picking, self).action_done()
                        else:
                            if self.picking_type_id.name == 'Delivery Orders':
                                pack_ship_del_attach_id = picking_attach.search(
                                    [('res_id', '=', self.id), ('res_name', '=', self.name)])
                                if not self.carrier_tracking_ref and not pack_ship_del_attach_id and not self.shipment_created:
                                    pick_id = picking_obj.search([('origin', '=', self.origin), ('state', '=', 'done')])
                                    if pick_id:
                                        for pick in pick_id:
                                            if pick.picking_type_id.name == 'Pack':
                                                # added extra
                                                # if pick.carrier_id.select_service.name != 'Royalmail':
                                                #
                                                pack_ship_has_attach_id = picking_attach.search(
                                                    [('res_id', '=', pick.id), ('res_name', '=', pick.name)])
                                                if pick.carrier_tracking_ref or pack_ship_has_attach_id or pick.shipment_created:
                                                    data_vals = {'carrier_tracking_ref': pick.carrier_tracking_ref,
                                                                 'carrier_id': pick.carrier_id.id,
                                                                 'shipment_created': True,
                                                                 'faulty': False, 'error_log': ''}
                                                    if pack_ship_has_attach_id:
                                                        delivery_attach_id = self.create_attachment(pick,
                                                                                                    pack_ship_has_attach_id)
                                                        if delivery_attach_id:
                                                            data_vals['label_generated'] = True
                                                    pick_obj = self.write(data_vals)
                                                    if pick.carrier_id.select_service.name == 'Royalmail':
                                                        # return
                                                        res = super(stock_picking, self).action_done()
                                                    else:
                                                        if pick_obj:
                                                            manifest_id = self.base_manifest()
                                                            if manifest_id:
                                                                res = super(stock_picking, self).action_done()
                                                            else:
                                                                return
                                                else:
                                                    return
                                else:
                                    if self.carrier_id.select_service.name == 'Royalmail':
                                        res = super(stock_picking, self).action_done()
                                    manifest_id = self.base_manifest()
                                    if manifest_id:
                                        res = super(stock_picking, self).action_done()
                                    else:
                                        return

    def total_amount(self):
        sale_order_id = self.env['sale.order'].search([('name', '=', self.origin)])
        if sale_order_id:
            return sale_order_id.amount_total
        else:
            return 0.0


class url_class(models.Model):
    _name = "url.class"

    url_name = fields.Char('Url Name.')
    url = fields.Char('Url')


class stock_move(models.Model):
    _inherit = "stock.move"

    def _get_new_picking_values(self):
        """ Prepares a new picking for this move as it could not be assigned to
        another picking. This method is designed to be inherited. """
        length = 0
        width = 0
        height = 0
        if self.origin:
            sale_id = self.env['sale.order'].search([('name', '=', self.origin)])
            heavy_weight = 0.00
            product_id = False

            for line in sale_id.order_line:
                # if line.product_id.weight:
                if line.product_id.weight >= heavy_weight:
                    heavy_weight = line.product_id.weight
                    product_id = line.product_id
            if product_id:
                # prod_id=self.env['product.product'].browse('product_id')
                length = product_id.length
                width = product_id.width
                height = product_id.height
        return {
            'origin': self.origin,
            'company_id': self.company_id.id,
            'move_type': self.group_id and self.group_id.move_type or 'direct',
            'partner_id': self.partner_id.id,
            'picking_type_id': self.picking_type_id.id,
            'location_id': self.location_id.id,
            'location_dest_id': self.location_dest_id.id,
            'length': length,
            'width': width,
            'height': height
        }
