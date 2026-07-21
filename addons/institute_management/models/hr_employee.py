from odoo import models, fields, api


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
        the given datetime range."""
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

    def _current_weekly_workload(self):
        """Count this teacher's active sessions (used as a workload ranking signal)."""
        self.ensure_one()
        Session = self.env['institute.class.session']
        return Session.search_count([
            ('teacher_id', '=', self.id),
            ('state', 'not in', ['cancelled']),
        ])

    def _sessions_today_count(self):
        """Count this teacher's active sessions scheduled for today."""
        self.ensure_one()
        today_str = fields.Date.context_today(self).strftime('%Y-%m-%d')
        Session = self.env['institute.class.session']
        return Session.search_count([
            ('teacher_id', '=', self.id),
            ('state', 'not in', ['cancelled']),
            ('start_datetime', '>=', today_str + ' 00:00:00'),
            ('start_datetime', '<=', today_str + ' 23:59:59'),
        ])

    @api.model
    def find_available_substitutes(self, subject_id, start_dt, end_dt, exclude_teacher_id=None):
        """Filter: qualified for the subject, available (no leave conflict),
        not already assigned to an overlapping session.
        Rank: lowest current workload, then fewest sessions today,
        then alphabetical as a final tie-breaker."""
        domain = [('subject_ids', 'in', [subject_id])]
        if exclude_teacher_id:
            domain.append(('id', '!=', exclude_teacher_id))
        candidates = self.search(domain)

        Session = self.env['institute.class.session']
        qualified_available = self.browse()
        for teacher in candidates:
            if not teacher.is_available(start_dt, end_dt):
                continue
            overlapping = Session.search_count([
                ('teacher_id', '=', teacher.id),
                ('state', '!=', 'cancelled'),
                ('start_datetime', '<', end_dt),
                ('end_datetime', '>', start_dt),
            ])
            if overlapping:
                continue
            qualified_available |= teacher

        ranked = sorted(
            qualified_available,
            key=lambda t: (t._current_weekly_workload(), t._sessions_today_count(), t.name or '')
        )
        return ranked