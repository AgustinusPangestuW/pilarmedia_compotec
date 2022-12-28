from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import requests
from bs4 import BeautifulSoup

class InheritAccountMove(models.Model):
    _inherit = 'account.move'

    payment_periode = fields.Selection([("10/25","10/25"),("non_10/25","Bukan 10/25")], 
        string='Payment Periode', default="non_10/25", compute="get_from_supplier", readonly=False,
        store=True)
    tax_link = fields.Text(string='Tax Link')
    delivery_date = fields.Date(string='Delivery Date', compute="set_base_on_po", store=1)
    is_pkp = fields.Boolean(string='is pkp?', compute="get_from_supplier")
    no_faktur = fields.Char(string='No. Faktur', size=13)
    npwp = fields.Char(string='NPWP', compute="get_from_supplier", readonly=0, store=1)
    valid_faktur = fields.Boolean(string='Valid Faktur ?', readonly=1)
    document_date = fields.Date(string='Document Date')
    is_hpp_23 = fields.Boolean(string='Hpp 23 ?')
    hpp23 = fields.Float(string='Hpp 23')

    @api.onchange('tax_link', 'invoice_line_ids', 'invoice_line_ids.quantity', 'invoice_line_ids.price_unit')
    def check_tax_link(self):
        for rec in self:
            if rec.tax_link:
                try:
                    res = requests.get(rec.tax_link)
                    if res and res.text:
                        res = BeautifulSoup(res.text, "xml")
                        rec.no_faktur = res.resValidateFakturPm.nomorFaktur.text or ""
                        rec.document_date = datetime.strptime(res.resValidateFakturPm.tanggalFaktur.text, '%d/%m/%Y').date() or ""
                        if float(res.resValidateFakturPm.jumlahDpp.text) == float(rec.amount_untaxed):
                            rec.valid_faktur = 1
                except Exception as e:
                    pass
            else:
                rec.valid_faktur = 0
                rec.no_faktur = ""

    def redirect_tax_link(self):
        for rec in self:
            if rec.tax_link:
                return {
                    'type': 'ir.actions.act_url',
                    'url': rec.tax_link,
                    'target': 'new',
                }

    @api.onchange('is_hpp_23', 'invoice_line_ids', 'invoice_line_ids.quantity', 'invoice_line_ids.price_unit')
    def calculate_hpp_23(self):
        for rec in self:
            if rec.is_hpp_23:
                rec.hpp23 = rec.amount_untaxed * 0.02

    @api.depends('partner_id')
    def get_from_supplier(self):
        for rec in self:
            rec.payment_periode = rec.partner_id.payment_periode or "non_10/25"
            rec.is_pkp = 1 if rec.partner_id.l10n_id_pkp else 0
            if not rec.npwp:
                rec.npwp = rec.partner_id.npwp

    @api.onchange(
        'invoice_payment_term_id', 
        'payment_periode', 
        'invoice_date_due',
        'invoice_date', 
        'delivery_date')
    def onchange_payment_periode(self):
        def set_date_base_10_or_25(date):
            day_due = int((date).strftime('%d'))
            if day_due in range(26, 32):
                date = date + relativedelta(months=+1)
                day_due = 10
            elif day_due in range(1, 11):
                day_due = 10
            elif day_due in range(13, 26):
                day_due = 25 
            newdate_due = date.replace(day=day_due)
            return newdate_due

        def set_due_base_working_time(date):
            working_time = self.env['resource.resource'].sudo().search([('user_id', '=', self.env.user.id)])
            # validate date not in holiday
            for i in working_time.calendar_id.global_leave_ids:
                if i.date_from.date() <= date <= i.date_to.date():
                    date = date + relativedelta(days=1)
                    date = set_due_base_working_time(date)

            return date

        for rec in self:
            if rec.payment_periode == "10/25" and rec.invoice_date_due:
                newdate_due = set_date_base_10_or_25(rec.invoice_date_due)
                newdate_due = set_due_base_working_time(newdate_due)
                rec.invoice_date_due = newdate_due
            else:
                rec._recompute_payment_terms_lines()

    @api.depends('invoice_line_ids', 'invoice_line_ids.purchase_line_id.order_id.delivery_date')
    def set_base_on_po(self):
        for rec in self:
            for i in rec.invoice_line_ids:
                if not rec.delivery_date or (i.purchase_line_id.order_id.delivery_date and \
                    i.purchase_line_id.order_id.delivery_date >= rec.delivery_date):
                    rec.delivery_date = i.purchase_line_id.order_id.delivery_date
                
    def _recompute_payment_terms_lines(self):
        ''' Compute the dynamic payment term lines of the journal entry.'''
        self.ensure_one()
        in_draft_mode = self != self._origin
        today = fields.Date.context_today(self)
        self = self.with_context(force_company=self.journal_id.company_id.id)

        def _get_payment_terms_computation_date(self):
            ''' Get the date from invoice that will be used to compute the payment terms.
            :param self:    The current account.move record.
            :return:        A datetime.date object.
            '''
            if self.invoice_payment_term_id:
                # check if base on receipt
                for i in self.invoice_payment_term_id.line_ids:
                    if i.value == "balance" and i.option == "day_after_receipt_date":
                        return self.delivery_date or today

                return self.invoice_date or today
            else:
                return self.invoice_date_due or self.invoice_date or today

        def _get_payment_terms_account(self, payment_terms_lines):
            ''' Get the account from invoice that will be set as receivable / payable account.
            :param self:                    The current account.move record.
            :param payment_terms_lines:     The current payment terms lines.
            :return:                        An account.account record.
            '''
            if payment_terms_lines:
                # Retrieve account from previous payment terms lines in order to allow the user to set a custom one.
                return payment_terms_lines[0].account_id
            elif self.partner_id:
                # Retrieve account from partner.
                if self.is_sale_document(include_receipts=True):
                    return self.partner_id.property_account_receivable_id
                else:
                    return self.partner_id.property_account_payable_id
            else:
                # Search new account.
                domain = [
                    ('company_id', '=', self.company_id.id),
                    ('internal_type', '=', 'receivable' if self.type in ('out_invoice', 'out_refund', 'out_receipt') else 'payable'),
                ]
                return self.env['account.account'].search(domain, limit=1)

        def _compute_payment_terms(self, date, total_balance, total_amount_currency):
            ''' Compute the payment terms.
            :param self:                    The current account.move record.
            :param date:                    The date computed by '_get_payment_terms_computation_date'.
            :param total_balance:           The invoice's total in company's currency.
            :param total_amount_currency:   The invoice's total in invoice's currency.
            :return:                        A list <to_pay_company_currency, to_pay_invoice_currency, due_date>.
            '''
            if self.invoice_payment_term_id:
                to_compute = self.invoice_payment_term_id.compute(total_balance, date_ref=date, currency=self.company_id.currency_id)
                if self.currency_id != self.company_id.currency_id:
                    # Multi-currencies.
                    to_compute_currency = self.invoice_payment_term_id.compute(total_amount_currency, date_ref=date, currency=self.currency_id)
                    return [(b[0], b[1], ac[1]) for b, ac in zip(to_compute, to_compute_currency)]
                else:
                    # Single-currency.
                    return [(b[0], b[1], 0.0) for b in to_compute]
            else:
                return [(fields.Date.to_string(date), total_balance, total_amount_currency)]

        def _compute_diff_payment_terms_lines(self, existing_terms_lines, account, to_compute):
            ''' Process the result of the '_compute_payment_terms' method and creates/updates corresponding invoice lines.
            :param self:                    The current account.move record.
            :param existing_terms_lines:    The current payment terms lines.
            :param account:                 The account.account record returned by '_get_payment_terms_account'.
            :param to_compute:              The list returned by '_compute_payment_terms'.
            '''
            # As we try to update existing lines, sort them by due date.
            existing_terms_lines = existing_terms_lines.sorted(lambda line: line.date_maturity or today)
            existing_terms_lines_index = 0

            # Recompute amls: update existing line or create new one for each payment term.
            new_terms_lines = self.env['account.move.line']
            for date_maturity, balance, amount_currency in to_compute:
                currency = self.journal_id.company_id.currency_id
                if currency and currency.is_zero(balance) and len(to_compute) > 1:
                    continue

                if existing_terms_lines_index < len(existing_terms_lines):
                    # Update existing line.
                    candidate = existing_terms_lines[existing_terms_lines_index]
                    existing_terms_lines_index += 1
                    candidate.update({
                        'date_maturity': date_maturity,
                        'amount_currency': -amount_currency,
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                    })
                else:
                    # Create new line.
                    create_method = in_draft_mode and self.env['account.move.line'].new or self.env['account.move.line'].create
                    candidate = create_method({
                        'name': self.invoice_payment_ref or '',
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                        'quantity': 1.0,
                        'amount_currency': -amount_currency,
                        'date_maturity': date_maturity,
                        'move_id': self.id,
                        'currency_id': self.currency_id.id if self.currency_id != self.company_id.currency_id else False,
                        'account_id': account.id,
                        'partner_id': self.commercial_partner_id.id,
                        'exclude_from_invoice_tab': True,
                    })
                new_terms_lines += candidate
                if in_draft_mode:
                    candidate._onchange_amount_currency()
                    candidate._onchange_balance()
            return new_terms_lines

        existing_terms_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
        others_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
        company_currency_id = (self.company_id or self.env.company).currency_id
        total_balance = sum(others_lines.mapped(lambda l: company_currency_id.round(l.balance)))
        total_amount_currency = sum(others_lines.mapped('amount_currency'))

        if not others_lines:
            self.line_ids -= existing_terms_lines
            return

        computation_date = _get_payment_terms_computation_date(self)
        account = _get_payment_terms_account(self, existing_terms_lines)
        to_compute = _compute_payment_terms(self, computation_date, total_balance, total_amount_currency)
        new_terms_lines = _compute_diff_payment_terms_lines(self, existing_terms_lines, account, to_compute)

        # Remove old terms lines that are no longer needed.
        self.line_ids -= existing_terms_lines - new_terms_lines

        if new_terms_lines:
            self.invoice_payment_ref = new_terms_lines[-1].name or ''
            self.invoice_date_due = new_terms_lines[-1].date_maturity
    


    