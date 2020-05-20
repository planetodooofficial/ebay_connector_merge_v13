from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import requests
# import sha
import hashlib
import binascii
import base64

import time
import random
import os
import datetime

import logging
from xml.dom.minidom import parse, parseString
import xml.etree.ElementTree as ET
from PyPDF2 import PdfFileWriter, PdfFileReader
from tempfile import mkstemp
from datetime import timedelta
from io import FileIO as file

_logger = logging.getLogger('sale')


class update_base_picking(models.TransientModel):
    _name = 'update.base.picking'

    def _get_operation(self):
        op_list = [
            ('create_shipment', 'Create Shipment'),
            ('print_batch_label', 'Print Batch Label'),
            ('remove_faulty', 'Move Faulty Orders'),
            ('add_carrier', 'Add Carrier'),
            ('cancel_shipments', 'Cancel Shipments'),
            ('bulk_validate', 'Bulk Vallidate')
        ]
        return op_list

    # ('process_orders', 'Process Shipment'),
    # ('create_all_manifest', 'Create Manifest')

    carrier_id = fields.Many2one('delivery.carrier', 'Carrier')
    operations = fields.Selection(_get_operation, string='Select Operation')
    # operations = fields.Selection([
    #     ('create_shipment', 'Create Shipment'),
    #     ('print_batch_label', 'Print Batch Label'),
    #     # ('print_label', 'Print Label'),
    #     ('remove_faulty', 'Move Faulty Orders'),
    #     ('process_orders', 'Process Shipment'),
    #     ('add_carrier', 'Add Carrier'),
    # ], string='Select Operation')

    base_manifest_ref = fields.Text('Manifest Reference')
    base_manifest_desc = fields.Text('Manifest Description')
    select_delivery_service = fields.Many2one('select.service', 'Select Delivery Service')

    def add_carrier(self):
        carrier_id = self.carrier_id

        if not carrier_id:
            raise UserError(_("Please Select Carrier to perform this Operation"))
        for picking in self.env['stock.picking'].browse(self._context['active_ids']):
            if picking.shipment_created or picking.label_generated or picking.label_printed:
                continue
            picking.carrier_id = carrier_id.id

        return True

    # def create_shipment(self):
    #
    #     return True

    def create_shipment(self):
        # base = super(update_base_picking, self).create_shipment()
        log_obj = self.env['base.shipping.logs']
        operation = False
        if self.env.context.get('picking_id', False):
            active_ids = self.env.context.get('picking_id', False)
            operation = False
        else:
            active_ids = self.env.context.get('active_ids', [])
            operation = True
        dpd_pickings = []
        hermes_pickings = []
        csv_shipping_dict = {}
        csv_shipping_list = []
        csv_shipment_id = self.env['ir.module.module'].search(
            [('name', '=', 'csv_shipment'), ('state', '=', 'installed')])
        if csv_shipment_id:
            config_obj = self.env['csv.configuration']
            configuration_list = config_obj.search([]).mapped('name').ids
            no_csv_fields = config_obj.search([('shipping_field_lines', '=', False)]).mapped('name').ids
        for picking in self.env['stock.picking'].browse(active_ids):
            # extra
            if picking.state != 'assigned':
                continue
            if picking.picking_type_id.warehouse_id.delivery_steps == 'pick_ship':
                if picking.picking_type_id.name != 'Pick':
                    continue
            if picking.picking_type_id.warehouse_id.delivery_steps == 'pick_pack_ship':
                if picking.picking_type_id.name == 'Pick':
                    if picking.state == 'done':
                        continue
                    else:
                        wiz = self.env['stock.immediate.transfer'].create({'pick_ids': [(4, picking.id)]})
                        wiz.process()
                        continue
                if picking.picking_type_id.name != 'Pack':
                    continue

                # end
            if not picking.carrier_id:
                picking.faulty = True
                picking.write({'error_log': 'Please select delivery carrier'})
                log_obj.create({
                    'date': datetime.datetime.now(),
                    'picking_id': picking.id,
                    'message': 'Please select delivery carrier'
                })
                continue
            # commented
            # if picking.shipment_created and picking.carrier_tracking_ref:
            if picking.shipment_created or picking.carrier_tracking_ref:
                continue

            try:
                if picking.carrier_id.select_service.name == 'Netdespatch Royalmail':
                    config = self.env['netdespatch.config'].search([])
                    if not config:
                        raise UserError(_("Netdespatch  configuration not found!"))
                    elif not config[0].rm_enable:
                        raise UserError(_("Please enable Royal Mail in Netdespatch configuration"))
                    if picking.carrier_id.rm_category == 'is_domestic':
                        self.create_netdespatch_domestic_Shipment(config[0], picking, operation)

                    if picking.carrier_id.rm_category == 'is_international':
                        self.create_netdespatch_international_Shipment(config[0], picking, operation)
                if picking.carrier_id.select_service.name == 'Netdespatch APC':
                    config = self.env['netdespatch.config'].search([])
                    if not config:
                        raise UserError(_("Netdespatch  configuration not found!"))
                    elif not config[0].apc_enable:
                        raise UserError(_("Please enable Apc in Netdespatch configuration"))
                    self.create_netdespatch_apc_Shipment(config[0], picking, operation)

                if picking.carrier_id.select_service.name == 'Netdespatch UKMail':
                    config = self.env['netdespatch.config'].search([])
                    if not config:
                        raise UserError(_("Netdespatch  configuration not found!"))
                    elif not config[0].ukmail_enable:
                        raise UserError(_("Please enable UKmail in Netdespatch configuration"))
                    self.create_netdespatch_ukmail_Shipment(config[0], picking, operation)

                if picking.carrier_id.select_service.name == 'Netdespatch Yodel':
                    config = self.env['netdespatch.config'].search([])
                    if not config:
                        raise UserError(_("Netdespatch  configuration not found!"))
                    elif not config[0].yodel_enable:
                        raise UserError(_("Please enable Yodel in Netdespatch configuration"))
                    self.create_netdespatch_yodel_Shipment(config[0], picking, operation)

                if picking.carrier_id.select_service.name == 'Fedex':
                    config = self.env['fedex.config'].search([('active', '=', True)])
                    if not config:
                        raise UserError(_("Fedex Configuration not found!"))
                    self.generate_fedex_tracking_no(config[0], picking, operation)

                # if picking.carrier_id.select_service.name == 'DPD':
                #     dpd_pickings.append(picking.id)
                if picking.carrier_id.select_service.name == 'DPD':
                    config = self.env['dpd.login'].search([])
                    if not config:
                        raise UserError(_("DPD Configuration not found!"))
                    self.create_dpd_Shipment(config[0], picking, operation)

                if picking.carrier_id.select_service.name == 'Ups':
                    self.generate_ups_tracking_no(picking, operation)

                if picking.carrier_id.select_service.name == 'UKmail':
                    config = self.env['ukmail.configuration'].search([])
                    if not config:
                        raise UserError(_("Ukmail configuration not found!"))
                    self.create_ukmail_shipping(config[0], picking, operation)

                if picking.carrier_id.select_service.name == 'Despatch Bay DX' or picking.carrier_id.select_service.name == 'Despatch Bay ParcelForce' or picking.carrier_id.select_service.name == 'Despatch Bay RoyalMail' or picking.carrier_id.select_service.name == 'Despatch Bay Yodel' or picking.carrier_id.select_service.name == 'Despatch Bay DHL':
                    self.genrate_despatchbay_barcode(picking, operation)

                if picking.carrier_id.select_service.name == 'Royalmail':
                    config = self.env['royalmail.config'].search([])
                    if not config:
                        raise UserError(_("Royalmail configuration not found!"))
                    self.create_royalmail_shipping(config[0], picking, operation)

                if picking.carrier_id.select_service.name == 'Docket Hub':
                    config = self.env['dockethub.config'].search([])
                    if not config:
                        raise UserError(_("Docket Hub configuration not found!"))
                    self.submit_item_advice(picking, operation)
                # if picking.carrier_id.select_service.name == 'Hermes':
                #     hermes_pickings.append(picking.id)
                if csv_shipment_id:
                    if picking.carrier_id.select_service.id in configuration_list:

                        if picking.carrier_id.select_service.id in csv_shipping_dict:
                            csv_shipping_dict[picking.carrier_id.select_service.id].append(picking.id)
                        else:
                            if picking.carrier_id.select_service.id in no_csv_fields:
                                raise UserError(_(
                                    'CSV Fields not found, please check the CSV Configuration for %s.' % picking.carrier_id.select_service.name))
                            csv_shipping_list = []
                            csv_shipping_list.append(picking.id)
                            csv_shipping_dict[picking.carrier_id.select_service.id] = csv_shipping_list

                    else:
                        raise UserError(_("CSV configuration not found"))
            except Exception as e:
                picking.faulty = True
                picking.write({'error_log': e})
                log_obj.create({
                    'date': datetime.datetime.now(),
                    'picking_id': picking.id,
                    'message': e
                })
                continue

        # if len(dpd_pickings):
        #     carrier_file = self.env['delivery.carrier.file'].search([])
        #     if carrier_file:
        #         self.env['delivery.carrier.file'].generate_files(carrier_file[0],dpd_pickings)
        if len(hermes_pickings):
            config = self.env['hermes.configuration'].search([])
            if not config:
                raise UserError(_("Hermes configuration not found!"))
            self.generate_consignment(config[0], hermes_pickings)
        if csv_shipment_id:
            if len(csv_shipping_dict):
                action_url = {}
                if not operation:
                    raise UserError(_("Please use the Shipping Operations from Actions Menu"))
                action = self.generate_shipping_csv(csv_shipping_dict)
                return action

        return True

    def print_label(self):

        return True

    def process_orders(self):
        for picking in self.env['stock.picking'].browse(self._context['active_ids']):
            picking.force_assign()
            # picking.do_transfer()
            picking.action_done()
            picking.manifested = True
        return True

    def remove_faulty(self):
        for picking in self.env['stock.picking'].browse(self._context['active_ids']):

            if picking.faulty:
                picking.faulty = False
            if picking.error_log:
                picking.write({'error_log': ''})
        return True

    def get_sorted_pickings(self, pickings):

        product_list = []
        move_list_id = []
        sorted_pickings = []
        move_list = []
        picking_ids = []
        to_be_added = []
        movelist = ()
        set_product_list = []
        new_product_list1 = []
        stock_move_obj = self.env['stock.move']

        for picking in pickings:
            if len(picking.move_lines) == 1:
                picking_ids.append(picking)
            else:
                to_be_added.append(picking)

        for move_list in picking_ids:

            for move_lines in move_list.move_lines:
                products = move_lines.product_id
                product_list.append(products)
                set_product_list = set(product_list)
                # new_product_list1 = []
                move_list_id.append(move_lines.id)
                movelist = tuple(move_list_id)

        len_movelist = len(movelist)

        if len_movelist == 1:
            movelist = str(movelist).replace(",", "")

        for new_product_list in set_product_list:
            new_product_list1.append(new_product_list.id)
        prod_list = tuple(new_product_list1)

        if len(prod_list) == 1:
            prod_list = str(prod_list).replace(",", "")

        if prod_list:
            self._cr.execute('select id from product_product where id in ' + str(prod_list) + ' ORDER BY default_code')
            products = self._cr.fetchall()
            if products:
                for id in products:
                    self._cr.execute(
                        'select id from stock_move where product_id = ' + str(id[0]) + ' and id in ' + str(movelist)
                    )
                    fetch = self._cr.fetchall()
                    if fetch:
                        for fetch_id in fetch:
                            fetch_id = fetch_id[0]
                            stock_move_id = stock_move_obj.browse(fetch_id)
                            sorted_pickings.append(stock_move_id.picking_id)
        sorted_pickings += to_be_added
        return sorted_pickings

    def print_batch_label(self):
        final_pickings = []
        fd_final, result = mkstemp()
        output = PdfFileWriter()
        picking_ids = []
        sorted_pickings = []

        for picking in self.env['stock.picking'].browse(self._context['active_ids']):
            if not picking.label_generated:
                continue

            picking_ids.append(picking)

        # sorts and returns the picking ids with the product's default code
        if picking_ids:
            sorted_pickings = self.get_sorted_pickings(picking_ids)

        for picking in sorted_pickings:
            fd, file_name = mkstemp()
            attachment_id = self.env['ir.attachment'].search(
                [('res_model', '=', 'stock.picking'), ('res_id', '=', picking.id)])
            if not attachment_id:
                continue
            os.write(fd, base64.decodestring(attachment_id[0].datas))
            pdf = PdfFileReader(file(file_name, "rb"))
            pgcnt = pdf.getNumPages()
            for i in range(0, pgcnt):
                output.addPage(pdf.getPage(i))
            final_pickings.append(picking)
        if sorted_pickings:
            binary_pdfs = output
            outputStream = file(result, "wb")
            output.write(outputStream)
            outputStream.close()
            f = open(result, "rb")
            batch = f.read()
            filename = str(datetime.datetime.now()).replace('-', '') + '.pdf'
            batch_id = self.env['batch.file'].create({'file': base64.encodestring(batch), 'filename': filename, })
            action = {'name': 'Generated Batch File', 'type': 'ir.actions.act_url',
                      'url': "web/content/?model=batch.file&id=" + str(
                          batch_id.id) + "&filename_field=filename&field=file&download=true&filename=" + filename,
                      'target': 'self', }
            for picking in final_pickings:
                if picking.label_generated and picking.shipment_created:
                    picking.label_printed = True

            return action

    def cancel_shipments(self):
        active_ids = self.env.context.get('active_ids', [])
        log_obj = self.env['base.shipping.logs']
        dpd_pickings = []
        for picking in self.env['stock.picking'].browse(active_ids):
            try:
                if picking.carrier_id.select_service.name == 'Royalmail':
                    config = self.env['royalmail.config'].search([])
                    if not config:
                        raise UserError(_("Royalmail configuration not found!"))
                    self.cancel_royalmail_shipment(config[0], picking)
                if picking.carrier_id.select_service.name == 'UKmail':
                    config = self.env['ukmail.configuration'].search([])
                    if not config:
                        raise UserError(_("Ukmail configuration not found!"))
                    self.cancel_ukconsignment(config[0], picking)
            except Exception as e:
                picking.faulty = True
                picking.write({'error_log': e})
                log_obj.create({
                    'date': datetime.datetime.now(),
                    'picking_id': picking.id,
                    'message': e
                })
                continue

    def create_all_manifest(self):
        netdespatch_royalmail = []
        netdespatch_apc = []
        netdespatch_ukmail = []
        netdespatch_yodel = []
        net_royalmail_list = []
        net_apc_list = []
        net_yodel_list = []
        net_ukmail_list = []

        # -----
        append_list = []
        create_list = []

        start_datetime = fields.datetime.now()
        picking_obj = self.env['stock.picking']
        manifest_obj = self.env['base.manifest']
        # picking_ids = picking_obj.search([('state', 'not in', ['cancel']),
        #                                   ('label_generated', '=', True),
        #                                   ('label_printed', '=', True),
        #                                   ('faulty', '=', False),
        #                                   ('shipment_created','=',True),
        #                                   ('manifested','=',False)
        #                                    ])

        picking_ids = picking_obj.search([('state', 'in', ['assigned']),
                                          ('faulty', '=', False),
                                          ('manifested', '=', False)
                                          ])
        # for pick in self.env['stock.picking'].browse(self._context['active_ids']).search([('state', 'not in', ['cancel']),
        #                                   ('state','=','assigned'),
        #                                   ('faulty', '=', False),
        #                                   ('manifested', '=', False)
        #                                   ]):

        for pick in picking_ids:
            # extra
            if pick.picking_type_id.name != 'Delivery Orders':
                log_obj = self.env['ecommerce.logs']
                log_vals = {
                    'start_datetime': start_datetime,
                    'end_datetime': fields.datetime.now(),
                    'message': 'This type of operation can only perform with outgoing shipments - ' + pick[0].origin
                }
                log_obj.create(log_vals)
                continue
                # raise UserError(_("This type of operation can only perform with outgoing shipments."))
                # continue
            # sale_order_id=self.env['sale.order'].search([('name','=',pick.origin)])
            if pick.picking_type_id.warehouse_id.delivery_steps == 'ship_only':
                if pick.carrier_id and pick.shipment_created == True:
                    if pick.carrier_id.select_service.name == self.select_delivery_service.name:
                        append_list.append(pick)

                    # if pick.carrier_id.select_service.name == 'Netdespatch Royalmail':
                    #     netdespatch_royalmail.append(pick)
                    # elif pick.carrier_id.select_service.name == 'Netdespatch APC':
                    #     netdespatch_apc.append(pick)
                    # elif pick.carrier_id.select_service.name == 'Netdespatch Yodel':
                    #     netdespatch_yodel.append(pick)
                    # elif pick.carrier_id.select_service.name == 'Netdespatch UKMail':
                    #     netdespatch_ukmail.append(pick)
                    # else:
                    #     print("-----no tracking---", pick)
            elif pick.picking_type_id.warehouse_id.delivery_steps == 'pick_ship':
                pick_id = picking_obj.search([('origin', '=', pick.origin)])
                pick_list = []
                for pick_ship in pick_id:
                    if pick_ship.picking_type_id.name == 'Pick':
                        pick_list.append(pick_ship)
                if len(pick_list) == 0:
                    log_obj = self.env['ecommerce.logs']
                    log_vals = {
                        'start_datetime': start_datetime,
                        'end_datetime': fields.datetime.now(),
                        'message': 'Outgoing shipment is not available for this order - ' + pick[0].origin
                    }
                    log_obj.create(log_vals)
                    continue

                else:
                    # end
                    for picks in pick_list:
                        if picks.carrier_id:
                            if picks.carrier_id.select_service.name == self.select_delivery_service.name:
                                pick.write({'shipment_created': True, 'carrier_id': picks.carrier_id.id,
                                            'carrier_tracking_ref': picks.carrier_tracking_ref})
                                append_list.append(pick)
                            # if pack_id.carrier_id.select_service.name == 'Netdespatch Royalmail':
                            #     netdespatch_royalmail.append(pack_id)
                            # elif pack_id.carrier_id.select_service.name == 'Netdespatch APC':
                            #     netdespatch_apc.append(pack_id)
                            # elif pack_id.carrier_id.select_service.name == 'Netdespatch Yodel':
                            #     netdespatch_yodel.append(pack_id)
                            # elif pack_id.carrier_id.select_service.name == 'Netdespatch UKMail':
                            #     netdespatch_ukmail.append(pack_id)
                            # else:
                            #     print("-----no tracking---",pack_id)
            elif pick.picking_type_id.warehouse_id.delivery_steps == 'pick_pack_ship':
                pack_id = picking_obj.search([('origin', '=', pick.origin)])
                pack_list = []
                for pack_ship in pack_id:
                    if pack_ship.picking_type_id.name == 'Pick':
                        continue
                    if pack_ship.picking_type_id.name == 'Pack':
                        pick.write({'shipment_created': True, 'carrier_id': pack_ship.carrier_id.id,
                                    'carrier_tracking_ref': pack_ship.carrier_tracking_ref})
                        pack_list.append(pack_ship)
                if len(pack_list) == 0:
                    log_obj = self.env['ecommerce.logs']
                    log_vals = {
                        'start_datetime': start_datetime,
                        'end_datetime': fields.datetime.now(),
                        'message': 'Outgoing shipment is not available for this order - ' + pick[0].origin
                    }
                    log_obj.create(log_vals)
                    continue

                else:
                    # end
                    for packs in pack_list:
                        if packs.carrier_id:
                            if packs.carrier_id.select_service.name == self.select_delivery_service.name:
                                append_list.append(pick)

        for nr in append_list:
            create_list.append((0, 0, {'picking_id': nr.id, 'carrier_id': nr.carrier_id.id}))
        if create_list:
            create_list_vals = {
                'service_provider': self.select_delivery_service.name,
                'date': datetime.datetime.now(),
                'user_id': self._uid,
                'base_manifest_ref': self.base_manifest_ref,
                'base_manifest_desc': self.base_manifest_desc,
                'manifest_lines': create_list
            }
            manifest_id = manifest_obj.create(create_list_vals)

    def bulk_validate(self):
        active_ids = self.env.context.get('active_ids', [])
        assign_orders = self.env['stock.picking'].browse(active_ids)
        for picking_id in assign_orders:
            if picking_id.state == 'assigned':
                if picking_id.picking_type_id.name == 'Delivery Orders':
                    wiz = self.env['stock.immediate.transfer'].create({'pick_ids': [(4, picking_id.id)]})
                    wiz.process()
                else:
                    return


update_base_picking()


class batch_file(models.TransientModel):
    _name = 'batch.file'

    file = fields.Binary('Batch File')
    filename = fields.Char('Filename')
