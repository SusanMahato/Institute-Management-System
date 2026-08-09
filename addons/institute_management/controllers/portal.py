import logging
from datetime import datetime

import pytz

from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)


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

    def _to_local_str(self, dt):
        """Convert a stored naive-UTC datetime to the current user's
        timezone for display. Direct field access (e.g. session.start_datetime)
        always returns raw UTC -- only the backend web client's own widgets
        convert automatically; portal QWeb templates need this done explicitly."""
        if not dt:
            return ''
        user_tz = pytz.timezone(request.env.user.tz or 'UTC')
        localized = pytz.UTC.localize(dt).astimezone(user_tz)
        return localized.strftime('%Y-%m-%d %H:%M')

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

        # Retrieve completed sessions lacking a syllabus log entry
        completed_sessions = Session.search([
            ('teacher_id', '=', employee.id),
            ('state', '=', 'completed'),
        ])
        unlogged_syllabus = completed_sessions
        if completed_sessions:
            SyllabusLog = request.env['institute.syllabus.log'].sudo()
            logged_session_ids = SyllabusLog.search([
                ('session_id', 'in', completed_sessions.ids),
            ]).mapped('session_id').ids
            unlogged_syllabus = completed_sessions.filtered(lambda s: s.id not in logged_session_ids)

        return request.render('institute_management.portal_teacher_timetable', {
            'employee': employee,
            'needs_acknowledgment': needs_acknowledgment,
            'upcoming_sessions': upcoming_sessions,
            'history_sessions': history_sessions,
            'unlogged_syllabus': unlogged_syllabus,
            'today': fields.Date.context_today(request.env.user),
            'to_local': self._to_local_str,
        })

    @http.route(['/my/timetable/acknowledge/<int:session_id>'],
                type='http', auth='user', methods=['POST'], website=True)
    def acknowledge_assignment(self, session_id, **kwargs):
        employee = self._get_current_teacher()
        session = request.env['institute.class.session'].sudo().browse(session_id)

        if employee and session.exists() and session.teacher_id.id == employee.id:
            session.action_acknowledge()

        return request.redirect('/my/timetable')

    @http.route(['/my/availability'], type='http', auth='user', website=True)
    def teacher_availability(self, **kwargs):
        employee = self._get_current_teacher()
        if not employee:
            return request.render('institute_management.portal_teacher_not_linked', {})

        leaves = request.env['resource.calendar.leaves'].sudo().search([
            ('resource_id', '=', employee.resource_id.id),
        ], order='date_from desc')

        return request.render('institute_management.portal_teacher_availability', {
            'employee': employee,
            'leaves': leaves,
            'to_local': self._to_local_str,
        })

    @http.route(['/my/availability/add'], type='http', auth='user', methods=['POST'], website=True)
    def add_availability(self, date_from=None, date_to=None, reason=None, **kwargs):
        _logger.debug("add_availability called: date_from=%r date_to=%r reason=%r user=%s",
                      date_from, date_to, reason, request.env.user.login)
        employee = self._get_current_teacher()
        if employee and date_from and date_to:
            try:
                # HTML datetime-local inputs are usually "YYYY-MM-DDTHH:MM",
                # but some browsers append seconds ("YYYY-MM-DDTHH:MM:SS") --
                # accept either. This is a naive wall-clock value in the
                # teacher's own timezone; Odoo's ORM stores Datetime fields
                # as naive UTC, so it must be localized and converted,
                # matching what Odoo's own datetime widgets do automatically.
                def _parse(value):
                    for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M'):
                        try:
                            return datetime.strptime(value, fmt)
                        except ValueError:
                            continue
                    raise ValueError(f"Unrecognized datetime format: {value!r}")

                start_naive = _parse(date_from)
                end_naive = _parse(date_to)
                user_tz = pytz.timezone(request.env.user.tz or 'UTC')
                start_utc = user_tz.localize(start_naive).astimezone(pytz.UTC).replace(tzinfo=None)
                end_utc = user_tz.localize(end_naive).astimezone(pytz.UTC).replace(tzinfo=None)
                if end_utc > start_utc:
                    request.env['resource.calendar.leaves'].sudo().create({
                        'name': reason or 'Unavailable',
                        'resource_id': employee.resource_id.id,
                        'date_from': start_utc,
                        'date_to': end_utc,
                    })
            except Exception:
                _logger.exception("Failed to create availability leave from portal form")
        return request.redirect('/my/availability')
    