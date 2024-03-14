from odoo import fields, models, api
from datetime import date
from dateutil import relativedelta
from odoo.exceptions import ValidationError, UserError


class EstatePropertyOffer(models.Model):
    _name = "estate.property.offer"
    _description = "Estate Property Offer"
    _order = "id desc"

    price = fields.Float()
    status = fields.Selection(copy=False, selection=[('accepted', 'Accepted'), ('refused', 'Refused')])
    partner_id = fields.Many2one('res.partner', required=True)
    property_id = fields.Many2one('estate.property', required=True, ondelete="cascade")
    validity = fields.Integer('validity (Days)', default=7)
    date_deadline = fields.Date('Deadline', compute='_compute_date_deadline', inverse='_inverse_compute_date_deadline')
    property_type_id = fields.Many2one(related="property_id.property_type_id", store="True")

    _sql_constraints = [
        ('check_price', 'check(price > 0)', 'The price must be strictly positive')
    ]

    @api.depends('validity')
    def _compute_date_deadline(self):
        for rec in self:
            if rec.validity:
                rec.date_deadline = (rec.create_date or date.today()) + relativedelta.relativedelta(
                    days=rec.validity)

    @api.onchange('date_deadline')
    def _inverse_compute_date_deadline(self):
        if self.date_deadline:
            create_date = date.today()
            if self.create_date:
                create_date = self.create_date.date()
            self.validity = (self.date_deadline - create_date).days

    def action_accepted(self):
        for rec in self:
            for r in rec.property_id.offer_ids:
                r.action_refused()
            rec.status = 'accepted'
            rec.property_id.selling_price = rec.price
            rec.property_id.buyer_id = rec.partner_id
            rec.property_id.state = 'offer accepted'
        return

    def action_refused(self):
        for rec in self:
            rec.status = 'refused'
        return

    @api.model
    def create(self, vals):
        property_id = self.env['estate.property'].browse(vals['property_id'])
        if property_id.expected_price > vals['price']:
            raise ValidationError(f"The offer must be higher than {property_id.expected_price}")
        property_id.state = 'offer received'
        return super(EstatePropertyOffer, self).create(vals)
