from odoo import models, fields


class InstituteRoom(models.Model):
    _name = 'institute.room'
    _description = 'Room'

    name = fields.Char(required=True)
    building = fields.Char()
    floor = fields.Char()
    capacity = fields.Integer(default=0)
    active = fields.Boolean(default=True)
    is_virtual = fields.Boolean(string='Virtual Room', default=False)
    meeting_link = fields.Char(string='Meeting Link')