from odoo import api, fields, models, _, netsvc, osv
import time
import odoo.netsvc


class account_invoice(models.Model):
    _inherit = "account.move"

    def invoice_pay_customer_base(self):
        """
        This function is used to have invoice auto paid is payment method defined
        parameters:
            No Parameters

        """
        context = self._context.copy()
        if context is None:
            context = {}
        wf_service = netsvc.LocalService("workflow")
        accountinvoice_link = self
        saleorder_obj = self.env['sale.order']
        journal_obj = self.env['account.journal']
        currentTime = time.strftime("%Y-%m-%d")
        if accountinvoice_link.type == 'out_invoice':
            self._cr.execute(
                "SELECT invoice_id, order_id FROM sale_order_invoice_rel WHERE invoice_id =%d" % (self[0].id,))
            saleorder_res = dict(self._cr.fetchall())
            saleorder_id = saleorder_res[self[0].id]
            saleorder_link = saleorder_obj.browse(saleorder_id)
            period_id = self.env['account.period'].search(
                [('date_start', '<=', currentTime), ('date_stop', '>=', currentTime),
                 ('company_id', '=', saleorder_link.company_id.id)])
            if not period_id:
                raise osv.except_osv
            else:
                period_id = period_id[0].id
            context['type'] = 'out_invoice'
            journal_ids = journal_obj.search([('type', '=', 'bank')])
            if journal_ids:
                journal_id = journal_ids[0].id
            else:
                journal_id = self._get_journal()
            journal = journal_obj.browse(journal_id)
            acc_id = journal.default_credit_account_id and journal.default_credit_account_id.id or False
            if not acc_id:
                raise self.wizard.except_wizard(_('Error !'),
                                                _('Your journal must have a default credit and debit account.'))

            paid = True
            currency_id = self._get_currency()
            context['currency_id'] = currency_id
            voucher_id = saleorder_obj.with_context(context).generate_payment_with_journal(journal_id,
                                                                                           saleorder_link.partner_id.id,
                                                                                           saleorder_link.amount_total,
                                                                                           accountinvoice_link.reference,
                                                                                           accountinvoice_link.origin,
                                                                                           currentTime, paid)
            self.pay_and_reconcile(saleorder_link.amount_total, acc_id, period_id, journal_id, False, period_id, False)

            wf_service.trg_write(self._uid, 'account.move', self[0].id, self._cr)
            wf_service.trg_write(self._uid, 'sale.order', saleorder_id, self._cr)

        self.env['account.move'].action_move_line_create([voucher_id])
        self._cr.commit()
        return True
