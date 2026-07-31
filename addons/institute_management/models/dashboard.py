from odoo import models, fields, api


class InstituteDashboard(models.AbstractModel):
    """Aggregation layer for the Coordinator Dashboard client action.

    Deliberately kept separate from institute.batch / institute.class.session
    / hr.employee so those models stay focused on their own domain logic.
    This model owns no data of its own -- it only reads existing fields and
    reuses existing business logic (lagging_flag, batch_completion_percent,
    the session state machine) rather than recomputing anything.
    """
    _name = 'institute.dashboard'
    _description = 'Coordinator Dashboard Aggregation'

    @api.model
    def get_dashboard_data(self):
        Employee = self.env['hr.employee']
        Batch = self.env['institute.batch']
        Session = self.env['institute.class.session']

        # "Teacher" = an employee qualified for at least one subject.
        # (hr.employee has no dedicated is_teacher flag today; subject_ids
        # is the existing signal used everywhere else in this module, e.g.
        # the SOS qualification constraint.)
        teacher_count = Employee.search_count([('subject_ids', '!=', False)])
        batch_count = Batch.search_count([])

        today_str = fields.Date.context_today(self).strftime('%Y-%m-%d')
        today_classes_count = Session.search_count([
            ('state', '!=', 'cancelled'),
            ('start_datetime', '>=', today_str + ' 00:00:00'),
            ('start_datetime', '<=', today_str + ' 23:59:59'),
        ])

        pending_sos_sessions = Session.search([('state', '=', 'needs_substitute')])
        pending_sos = [{
            'id': s.id,
            'batch_name': s.batch_id.name,
            'topic_name': s.topic_id.name,
            'start_datetime': fields.Datetime.to_string(s.start_datetime),
        } for s in pending_sos_sessions]

        lagging = Batch.search([('lagging_flag', '=', True)])
        lagging_batches = [{
            'id': b.id,
            'name': b.name,
            'completion_percent': round(b.batch_completion_percent, 1),
        } for b in lagging]

        return {
            'teacher_count': teacher_count,
            'batch_count': batch_count,
            'today_classes_count': today_classes_count,
            'pending_sos_count': len(pending_sos),
            'pending_sos': pending_sos,
            'lagging_batches': lagging_batches,
        }
        