from datetime import timedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class InstituteClassSession(models.Model):
    _name = 'institute.class.session'
    _inherit = ['mail.thread']
    _description = 'Class Session'

    teacher_id = fields.Many2one('hr.employee', required=True, string='Teacher', tracking=True)
    room_id = fields.Many2one('institute.room', required=True)
    batch_id = fields.Many2one('institute.batch', required=True)
    topic_id = fields.Many2one('institute.topic', required=True)

    course_id = fields.Many2one(related='topic_id.chapter_id.subject_id.course_id', store=True, string='Course')
    subject_id = fields.Many2one(related='topic_id.chapter_id.subject_id', store=True, string='Subject')

    start_datetime = fields.Datetime(required=True)
    end_datetime = fields.Datetime(required=True)

    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('needs_substitute', 'Needs Substitute'),
        ('substituted', 'Substituted'),
        ('cancelled', 'Cancelled'),
    ], default='scheduled', required=True, tracking=True)

    original_teacher_id = fields.Many2one('hr.employee', string='Original Teacher', readonly=True)

    acknowledged = fields.Boolean(default=False, readonly=True)
    acknowledged_by_id = fields.Many2one('hr.employee', readonly=True, string='Acknowledged By')
    acknowledged_at = fields.Datetime(readonly=True)
    viewed_at = fields.Datetime(readonly=True, string='First Viewed At')

    is_history = fields.Boolean(compute='_compute_is_history', store=True)
    is_joinable_now = fields.Boolean(compute='_compute_is_joinable_now', string='Joinable Now')

    teacher_suggestion_source = fields.Selection([
        ('auto', 'Automatic'),
        ('manual', 'Manual'),
    ], default='manual', readonly=True)

    @api.depends('room_id.is_virtual', 'room_id.meeting_link', 'start_datetime', 'end_datetime')
    def _compute_is_joinable_now(self):
        now = fields.Datetime.now()
        for session in self:
            if not session.room_id.is_virtual or not session.room_id.meeting_link:
                session.is_joinable_now = False
                continue

            # Allow joining 10 minutes prior to start time up until end time
            join_opens_at = session.start_datetime - timedelta(minutes=10)
            session.is_joinable_now = join_opens_at <= now <= session.end_datetime

    def write(self, vals):
        rooms_changed = self.env['institute.class.session']
        if 'room_id' in vals:
            for session in self:
                if session.state not in ('cancelled', 'completed') and session.room_id.id != vals['room_id']:
                    rooms_changed |= session
        result = super().write(vals)
        for session in rooms_changed:
            session._send_room_reallocation_email()
        return result

    def _send_room_reallocation_email(self):
        self.ensure_one()
        template = self.env.ref(
            'institute_management.mail_template_room_reallocation', raise_if_not_found=False)
        if not template:
            return
        recipients = []
        if self.teacher_id.work_email:
            recipients.append(self.teacher_id.work_email)
        recipients += [p.email for p in self.batch_id.student_ids if p.email]
        if not recipients:
            return
        template.send_mail(
            self.id,
            email_values={'email_to': ','.join(recipients)},
            force_send=True,
        )

    def action_acknowledge(self):
        for session in self:
            session.write({
                'acknowledged': True,
                'acknowledged_by_id': session.teacher_id.id,
                'acknowledged_at': fields.Datetime.now(),
            })

    def action_mark_unavailable(self):
        for session in self:
            if session.state != 'scheduled':
                raise ValidationError(
                    "Only a scheduled session can be marked as needing a substitute."
                )
            session.write({
                'state': 'needs_substitute',
                'original_teacher_id': session.teacher_id.id,
            })

    def action_mark_completed(self):
        for session in self:
            if session.state != 'scheduled':
                raise ValidationError(
                    "Only a scheduled session can be marked as completed."
                )
            session.write({'state': 'completed'})

    def action_open_substitute_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Assign Substitute',
            'res_model': 'institute.substitute.teacher.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_session_id': self.id},
        }

    def get_substitute_candidates(self):
        """Return ranked, qualified, available substitute teachers for this
        session, excluding the currently/originally assigned teacher."""
        self.ensure_one()
        Employee = self.env['hr.employee']
        exclude_id = self.original_teacher_id.id or self.teacher_id.id
        return Employee.find_available_substitutes(
            self.subject_id.id,
            self.start_datetime,
            self.end_datetime,
            exclude_teacher_id=exclude_id,
            room_id=self.room_id.id,
        )

    @api.depends('state')
    def _compute_is_history(self):
        for session in self:
            session.is_history = session.state in ('completed', 'substituted')

    @api.constrains('teacher_id', 'start_datetime', 'end_datetime', 'state')
    def _check_teacher_overlap(self):
        for session in self:
            if session.state == 'cancelled':
                continue
            domain = [
                ('id', '!=', session.id),
                ('teacher_id', '=', session.teacher_id.id),
                ('state', '!=', 'cancelled'),
                ('start_datetime', '<', session.end_datetime),
                ('end_datetime', '>', session.start_datetime),
            ]
            if self.search_count(domain):
                raise ValidationError(
                    f"Teacher {session.teacher_id.name} is already assigned to another "
                    f"session that overlaps this time slot."
                )

    @api.constrains('room_id', 'start_datetime', 'end_datetime', 'state')
    def _check_room_overlap(self):
        for session in self:
            if session.state == 'cancelled':
                continue
            domain = [
                ('id', '!=', session.id),
                ('room_id', '=', session.room_id.id),
                ('state', '!=', 'cancelled'),
                ('start_datetime', '<', session.end_datetime),
                ('end_datetime', '>', session.start_datetime),
            ]
            if self.search_count(domain):
                raise ValidationError(
                    f"Room {session.room_id.name} is already booked for another "
                    f"session that overlaps this time slot."
                )

    @api.constrains('teacher_id', 'subject_id')
    def _check_teacher_qualified(self):
        for session in self:
            if session.subject_id and session.subject_id not in session.teacher_id.subject_ids:
                raise ValidationError(
                    f"Teacher {session.teacher_id.name} is not qualified to teach "
                    f"{session.subject_id.name}."
                )

    @api.onchange('topic_id')
    def _onchange_topic_id_suggest_teacher(self):
        if not self.topic_id or not self.subject_id:
            return
        if self.teacher_id and self.teacher_suggestion_source == 'manual':
            return
        candidates = self.env['hr.employee'].find_available_substitutes(
            self.subject_id.id,
            self.start_datetime or fields.Datetime.now(),
            self.end_datetime or fields.Datetime.now(),
            room_id=self.room_id.id if self.room_id else None,
        )
        if candidates:
            self.teacher_id = candidates[0]
            self.teacher_suggestion_source = 'auto'
            return {
                'warning': {
                    'title': 'Suggested Teacher',
                    'message': f"Suggested: {candidates[0].name} (based on availability and workload). You can change this if needed.",
                }
            }
        else:
            self.teacher_id = False
            self.teacher_suggestion_source = 'auto'
            return {
                'warning': {
                    'title': 'No Suitable Teacher Found',
                    'message': "No qualified, available teacher was found for this topic. Please assign one manually.",
                }
            }

    @api.onchange('topic_id')
    def _onchange_topic_id_check_standard_count(self):
        if self.topic_id and self.topic_id.standard_class_count:
            if self.topic_id.session_count >= self.topic_id.standard_class_count:
                return {
                    'warning': {
                        'title': 'Topic Already at Planned Class Count',
                        'message': (
                            f"'{self.topic_id.name}' has already reached its planned "
                            f"{self.topic_id.standard_class_count} class(es). "
                            f"Scheduling another is allowed but may indicate falling behind schedule."
                        ),
                    }
                }

    @api.onchange('teacher_id')
    def _onchange_teacher_id_mark_manual(self):
        if self.teacher_id:
            self.teacher_suggestion_source = 'manual'

    def action_log_syllabus(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Log Syllabus Progress',
            'res_model': 'institute.syllabus.log',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_session_id': self.id,
            },
        }
        