from odoo import fields, models, api, exceptions
from datetime import date
from dateutil import relativedelta
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_compare, float_is_zero, float_repr, float_round, float_split, float_split_str


class EstateProperty(models.Model):
    _name = "estate.property"
    _description = "Estate Property"

    name = fields.Char("Title", required=True)
    tag_ids = fields.Many2many('estate.property.tag')
    property_type_id = fields.Many2one("estate.property.type", string="Property Type")
    description = fields.Text()
    postcode = fields.Char()
    date_availability = fields.Date("Available From", copy=False,
                                    default=lambda self: fields.Datetime.add(
                                        value=fields.Datetime.today(),
                                        months=3
                                    ))
    expected_price = fields.Float(required=True)
    selling_price = fields.Float(readonly=True, copy=False)
    bedrooms = fields.Integer(default=2)
    living_area = fields.Integer("Living Area (sqm)")
    facades = fields.Integer()
    garage = fields.Boolean()
    garden = fields.Boolean()
    garden_area = fields.Integer("Garden Area (sqm)")
    garden_orientation = fields.Selection(
        [('north', 'North'), ('south', 'South'), ('east', 'East'), ('west', 'West')])
    state = fields.Selection(
        required=True,
        copy=False,
        string='Status',
        selection=[
            ('new', 'New'),
            ('offer received', 'Offer Received'),
            ('offer accepted', 'Offer Accepted'),
            ('sold', 'Sold'),
            ('canceled', 'Canceled'),
        ],
        default='new'
    )
    active = fields.Boolean(default=True)
    salesperson_id = fields.Many2one('res.users', string='Salesman', default=lambda self: self.env.user)
    buyer_id = fields.Many2one('res.partner', copy=False)
    offer_ids = fields.One2many('estate.property.offer', 'property_id')
    best_offer = fields.Integer(compute="_compute_best_offer")
    total_area = fields.Integer("Total Area (sqm)", compute="_compute_total_area")

    _sql_constraints = [
        ('check_expected_price', 'check(expected_price > 0)', 'The expected price must be strictly positive'),
        ('check_selling_price', 'check(selling_price >= 0)', 'The selling price must be positive')
    ]

    @api.depends('living_area', 'garden_area')
    def _compute_total_area(self):
        for rec in self: rec.total_area = rec.living_area + rec.garden_area

    @api.depends('offer_ids.price')
    def _compute_best_offer(self):
        [setattr(rec, 'best_offer', max(rec.offer_ids.mapped('price')) if rec.offer_ids else 0) for rec in self]

    @api.onchange('garden')
    def _onchange_garden(self):
        self.garden_area, self.garden_orientation = (10, 'north') if self.garden else (False, False)

    def action_sold(self):
        if self.state == 'canceled':
            raise UserError("Canceled property cannot be sold.")
        self.state = 'sold'
        return

    def action_cancel(self):
        if self.state == 'sold':
            raise exceptions.UserError("Sold property cannot be canceled.")
        self.state = 'canceled'
        return

    @api.constrains('expected_price', 'selling_price')
    def _check_selling_price(self):
        for rec in self:
            if float_is_zero(rec.selling_price, precision_digits=2):
                continue
            if float_compare(rec.selling_price, rec.expected_price * 0.9, 2) < 0:
                raise ValidationError(
                    "The selling price must be at least 90% of the expected price! You must reduce the expected price if you want to accept this offer.")


class EstatePropertyOffer(models.Model):
    _name = "estate.property.offer"
    _description = "Estate Property Offer"

    price = fields.Float()
    status = fields.Selection(copy=False, selection=[('accepted', 'Accepted'), ('refused', 'Refused')])
    partner_id = fields.Many2one('res.partner', required=True)
    property_id = fields.Many2one('estate.property', required=True)
    validity = fields.Integer('validity (Days)', default=7)
    date_deadline = fields.Date('Deadline', compute='_compute_date_deadline', inverse='_inverse_compute_date_deadline')

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
        return

    def action_refused(self):
        for rec in self:
            if rec.status == 'accepted':
                rec.status = 'refused'
                rec.property_id.selling_price = 0
                rec.property_id.buyer_id = False
        return
