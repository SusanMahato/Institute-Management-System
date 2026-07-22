from odoo import models, fields, api
from odoo.exceptions import ValidationError


class InstituteClassSession(models.Model):
    _name = 'institute.class.session'
    _description = 'Class Session'

    teacher_id = fields.Many2one('hr.employee', required=True, string='Teacher')
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
    ], default='scheduled', required=True)

    original_teacher_id = fields.Many2one('hr.employee', string='Original Teacher', readonly=True)

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
                