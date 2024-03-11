from odoo import fields, models


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
    partner_id = fields.Many2one('res.partner', raquired=True)
    property_id = fields.Many2one('estate.property', raquired=True)
