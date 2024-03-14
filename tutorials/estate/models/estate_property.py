from odoo import fields, models, api, exceptions
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_compare, float_is_zero, float_repr, float_round, float_split, float_split_str


class EstateProperty(models.Model):
    _name = "estate.property"
    _description = "Estate Property"
    _order = "id desc"

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
    state = fields.Selection(required=True, copy=False, string='Status', default='new',
                             selection=[
                                 ('new', 'New'),
                                 ('offer received', 'Offer Received'),
                                 ('offer accepted', 'Offer Accepted'),
                                 ('sold', 'Sold'),
                                 ('canceled', 'Canceled')])
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
        self.selling_price = 0
        self.buyer_id = False
        for rec in self.offer_ids:
            rec.action_refused()
        return

    @api.constrains('expected_price', 'selling_price')
    def _check_selling_price(self):
        for rec in self:
            if float_is_zero(rec.selling_price, precision_digits=2):
                continue
            if float_compare(rec.selling_price, rec.expected_price * 0.9, 2) < 0:
                raise ValidationError(
                    "The selling price must be at least 90% of the expected price! You must reduce the expected price if you want to accept this offer.")

    @api.ondelete(at_uninstall=False)
    def unlink(self):
        for rec in self:
            if rec.state not in ('canceled', 'new'):
                raise ValidationError("Only new and canceled properties can be deleted")
        return super(EstateProperty, self).unlink()
