from odoo import models, fields


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