from odoo import fields, models, api
from datetime import date
from dateutil import relativedelta


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
        string='State',
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

    @api.depends('living_area', 'garden_area')
    def _compute_total_area(self):
        for rec in self: rec.total_area = rec.living_area + rec.garden_area

    @api.depends('offer_ids.price')
    def _compute_best_offer(self):
        [setattr(rec, 'best_offer', max(rec.offer_ids.mapped('price')) if rec.offer_ids else 0) for rec in self]

    @api.onchange('garden')
    def _onchange_garden(self):
        self.garden_area, self.garden_orientation = (10, 'north') if self.garden else (False, False)


class EstatePropertyOffer(models.Model):
    _name = "estate.property.offer"
    _description = "Estate Property Offer"

    price = fields.Float()
    status = fields.Selection(copy=False,
                              selection=[
                                  ('accepted', 'Accepted'),
                                  ('refused', 'Refused'),
                              ]
                              )
    partner_id = fields.Many2one('res.partner', required=True)
    property_id = fields.Many2one('estate.property', required=True)
    validity = fields.Integer('validity (Days)', default=7)
    date_deadline = fields.Date('Deadline', compute='_compute_date_deadline', inverse='_inverse_compute_date_deadline')

    @api.depends('validity')
    def _compute_date_deadline(self):
        for rec in self:
            if rec.validity:
                rec.date_deadline = (rec.create_date or date.today()) + relativedelta.relativedelta(
                    days=rec.validity)

    @api.onchange('date_deadline')
    def _inverse_compute_date_deadline(self):
        for rec in self:
            if rec.date_deadline:
                rec.validity = (rec.date_deadline - (rec.create_date.date() or date.today())).days
