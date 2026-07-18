from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    subject_ids = fields.Many2many('institute.subject', string='Qualified Subjects')
    preferred_mode = fields.Selection([
        ('on_site', 'On-site'),
        ('online', 'Online'),
        ('both', 'Both'),
    ], string='Preferred Teaching Mode', default='both')
    maximum_weekly_workload = fields.Integer(
        string='Maximum Weekly Workload', default=20,
        help='Maximum number of class sessions this teacher can be assigned per week'
    )

    def is_available(self, start_dt, end_dt):
        """Check whether this teacher has no approved leave overlapping
        the given datetime range. Working-hours matching against
        resource_calendar_id can be layered in later if needed."""
        self.ensure_one()
        if not self.resource_id:
            return True
        Leaves = self.env['resource.calendar.leaves']
        conflicting_leaves = Leaves.search([
            ('resource_id', '=', self.resource_id.id),
            ('date_from', '<', end_dt),
            ('date_to', '>', start_dt),
        ], limit=1)
        return not conflicting_leaves