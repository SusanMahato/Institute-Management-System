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
        today_sessions = Session.search([
            ('state', '!=', 'cancelled'),
            ('start_datetime', '>=', today_str + ' 00:00:00'),
            ('start_datetime', '<=', today_str + ' 23:59:59'),
        ], order='start_datetime')
        today_classes_count = len(today_sessions)
        today_schedule = [{
            'id': s.id,
            'start_datetime': fields.Datetime.to_string(s.start_datetime),
            'topic_name': s.topic_id.name,
            'room_name': s.room_id.name,
            'batch_name': s.batch_id.name,
        } for s in today_sessions]

        pending_sos_sessions = Session.search([('state', '=', 'needs_substitute')])
        pending_sos = [{
            'id': s.id,
            'batch_name': s.batch_id.name,
            'topic_name': s.topic_id.name,
            'start_datetime': fields.Datetime.to_string(s.start_datetime),
        } for s in pending_sos_sessions]

        unlogged_syllabus_sessions = Session.search([('state', '=', 'completed')])
        if unlogged_syllabus_sessions:
            SyllabusLog = self.env['institute.syllabus.log']
            logged_session_ids = SyllabusLog.search([
                ('session_id', 'in', unlogged_syllabus_sessions.ids),
            ]).mapped('session_id').ids
            unlogged_syllabus_sessions = unlogged_syllabus_sessions.filtered(
                lambda s: s.id not in logged_session_ids)

        unlogged_syllabus = [{
            'id': s.id,
            'teacher_name': s.teacher_id.name,
            'batch_name': s.batch_id.name,
            'topic_name': s.topic_id.name,
            'start_datetime': fields.Datetime.to_string(s.start_datetime),
        } for s in unlogged_syllabus_sessions]

        lagging = Batch.search([('lagging_flag', '=', True)])
        lagging_batches = [{
            'id': b.id,
            'name': b.name,
            'completion_percent': round(b.batch_completion_percent, 1),
        } for b in lagging]

        # Syllabus Progress chart: every batch, worst-progress first so
        # lagging batches are visually obvious. Reuses the existing
        # batch_completion_percent compute field directly -- no new logic.
        all_batches = Batch.search([], order='name')
        syllabus_progress = sorted([{
            'id': b.id,
            'name': b.name,
            'completion_percent': round(b.batch_completion_percent, 1),
        } for b in all_batches], key=lambda x: x['completion_percent'])

        # Teacher Workload chart: reuses the existing
        # _current_weekly_workload() helper (already used for SOS ranking)
        # directly. Busiest teacher first, since that's what a coordinator
        # needs to see first when deciding who NOT to overload further.
        teachers = Employee.search([('subject_ids', '!=', False)])
        teacher_workload = sorted([{
            'id': t.id,
            'name': t.name,
            'workload': t._current_weekly_workload(),
        } for t in teachers], key=lambda x: x['workload'], reverse=True)

        return {
            'teacher_count': teacher_count,
            'batch_count': batch_count,
            'today_classes_count': today_classes_count,
            'pending_sos_count': len(pending_sos),
            'pending_sos': pending_sos,
            'unlogged_syllabus_count': len(unlogged_syllabus),
            'unlogged_syllabus': unlogged_syllabus,
            'lagging_batches': lagging_batches,
            'syllabus_progress': syllabus_progress,
            'teacher_workload': teacher_workload,
            'today_schedule': today_schedule,
        }
        