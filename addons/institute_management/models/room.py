from odoo import models, fields, api


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

    floorplan_status = fields.Selection([
        ('green', 'Active Session'),
        ('yellow', 'Starting Soon'),
        ('red', 'Conflict / Unassigned'),
        ('gray', 'No Session Today'),
    ], compute='_compute_floorplan_status', string='Status')

    def _compute_floorplan_status(self):
        Session = self.env['institute.class.session']
        now = fields.Datetime.now()
        soon_threshold = fields.Datetime.add(now, minutes=15)
        for room in self:
            sessions_today = Session.search([
                ('room_id', '=', room.id),
                ('state', 'not in', ['cancelled']),
                ('start_datetime', '<=', fields.Datetime.add(now, hours=23)),
                ('end_datetime', '>=', fields.Datetime.subtract(now, hours=23)),
            ])
            active = sessions_today.filtered(lambda s: s.start_datetime <= now <= s.end_datetime)
            starting_soon = sessions_today.filtered(lambda s: now < s.start_datetime <= soon_threshold)
            needs_substitute = sessions_today.filtered(lambda s: s.state == 'needs_substitute')

            if needs_substitute:
                room.floorplan_status = 'red'
            elif active:
                room.floorplan_status = 'green'
            elif starting_soon:
                room.floorplan_status = 'yellow'
            else:
                room.floorplan_status = 'gray'
                