import logging

import pytz

from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)


class InstituteStudentPortal(http.Controller):
    """Read-only portal page for students, showing their own batch's
    upcoming and past class sessions. Students are res.partner records
    linked via institute.batch's student_ids Many2many -- assumed to
    belong to exactly one batch."""

    def _to_local_str(self, dt):
        if not dt:
            return ''
        user_tz = pytz.timezone(request.env.user.tz or 'UTC')
        localized = pytz.UTC.localize(dt).astimezone(user_tz)
        return localized.strftime('%Y-%m-%d %H:%M')

    @http.route(['/my/batch'], type='http', auth='user', website=True)
    def student_batch(self, **kwargs):
        partner = request.env.user.partner_id
        Batch = request.env['institute.batch'].sudo()
        batch = Batch.search([('student_ids', 'in', partner.id)], limit=1)

        if not batch:
            return request.render('institute_management.portal_student_not_linked', {})

        Session = request.env['institute.class.session'].sudo()
        upcoming_sessions = Session.search([
            ('batch_id', '=', batch.id),
            ('state', 'in', ['scheduled', 'substituted']),
            ('is_history', '=', False),
        ], order='start_datetime asc')
        history_sessions = Session.search([
            ('batch_id', '=', batch.id),
            ('is_history', '=', True),
        ], order='start_datetime desc', limit=20)

        return request.render('institute_management.portal_student_batch', {
            'batch': batch,
            'upcoming_sessions': upcoming_sessions,
            'history_sessions': history_sessions,
            'today': fields.Date.context_today(request.env.user),
            'to_local': self._to_local_str,
        })
        