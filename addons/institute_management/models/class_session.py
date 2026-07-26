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
    
    is_history = fields.Boolean(compute='_compute_is_history', store=True)

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