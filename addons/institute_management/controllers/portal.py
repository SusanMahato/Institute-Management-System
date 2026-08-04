from odoo import http, fields
from odoo.http import request


class InstituteTeacherPortal(http.Controller):
    """Lightweight portal pages for teachers, additional to their existing
    backend access -- not a replacement for it. Any logged-in user (internal
    or portal) can reach these routes; access to a specific teacher's own
    data is enforced in Python below by matching hr.employee.user_id to the
    current user, since there are no record rules on institute.class.session
    restricting it by owning teacher today.
    """

    def _get_current_teacher(self):
        return request.env['hr.employee'].sudo().search(
            [('user_id', '=', request.env.user.id)], limit=1)

    @http.route(['/my/timetable'], type='http', auth='user', website=True)
    def teacher_timetable(self, **kwargs):
        employee = self._get_current_teacher()
        if not employee:
            return request.render('institute_management.portal_teacher_not_linked', {})

        Session = request.env['institute.class.session'].sudo()
        needs_acknowledgment = Session.search([
            ('teacher_id', '=', employee.id),
            ('state', '=', 'substituted'),
            ('acknowledged', '=', False),
        ], order='start_datetime asc')
        upcoming_sessions = Session.search([
            ('teacher_id', '=', employee.id),
            ('state', '!=', 'cancelled'),
            ('is_history', '=', False),
        ], order='start_datetime asc')
        history_sessions = Session.search([
            ('teacher_id', '=', employee.id),
            ('is_history', '=', True),
        ], order='start_datetime desc', limit=20)

        return request.render('institute_management.portal_teacher_timetable', {
            'employee': employee,
            'needs_acknowledgment': needs_acknowledgment,
            'upcoming_sessions': upcoming_sessions,
            'history_sessions': history_sessions,
            'today': fields.Date.context_today(request.env.user),
        })

    @http.route(['/my/timetable/acknowledge/<int:session_id>'],
                type='http', auth='user', methods=['POST'], website=True)
    def acknowledge_assignment(self, session_id, **kwargs):
        employee = self._get_current_teacher()
        session = request.env['institute.class.session'].sudo().browse(session_id)

        if employee and session.exists() and session.teacher_id.id == employee.id:
            session.action_acknowledge()

        return request.redirect('/my/timetable')
    