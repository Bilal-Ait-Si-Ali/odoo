from odoo import models
from odoo.exceptions import UserError


class EstateProperty(models.Model):
    _inherit = "estate.property"

    administrative_fees = 100.00
    tax_rate = 0.06

    def action_sold(self):
        result = super(EstateProperty, self).action_sold()
        journal = self._get_customer_invoices_journal()
        invoice = self._create_customer_invoice(journal)
        self._create_invoice_lines(invoice)
        return result

    def _get_customer_invoices_journal(self):
        journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        if not journal:
            raise UserError("The 'Customer Invoices' journal is not found.")
        return journal

    def _create_customer_invoice(self, journal):
        invoice_vals = {
            'partner_id': self.buyer_id.id,
            'move_type': 'out_invoice',
            'journal_id': journal.id,
        }
        return self.env['account.move'].create(invoice_vals)

    def _create_invoice_lines(self, invoice):
        lines_to_create = []
        for rec in self:
            if rec.state == 'sold' and rec.selling_price > 0:
                lines_to_create.extend(
                    (
                        {
                            'move_id': invoice.id,
                            'name': 'Selling Price',
                            'quantity': 1,
                            'price_unit': rec.selling_price,
                        },
                        {
                            'move_id': invoice.id,
                            'name': 'Administrative Fees',
                            'quantity': 1,
                            'price_unit': self.administrative_fees,
                        },
                        {
                            'move_id': invoice.id,
                            'name': 'Tax',
                            'quantity': 1,
                            'price_unit': rec.selling_price * self.tax_rate,
                        },
                    )
                )
        return self.env['account.move.line'].create(lines_to_create)
