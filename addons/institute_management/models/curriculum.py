from odoo import models, fields


class InstituteCourse(models.Model):
    _name = 'institute.course'
    _description = 'Course'

    name = fields.Char(required=True)
    subject_ids = fields.One2many('institute.subject', 'course_id', string='Subjects')
    active = fields.Boolean(default=True)


class InstituteSubject(models.Model):
    _name = 'institute.subject'
    _description = 'Subject'

    name = fields.Char(required=True)
    course_id = fields.Many2one('institute.course', required=True, ondelete='cascade')
    chapter_ids = fields.One2many('institute.chapter', 'subject_id', string='Chapters')


class InstituteChapter(models.Model):
    _name = 'institute.chapter'
    _description = 'Chapter'

    name = fields.Char(required=True)
    subject_id = fields.Many2one('institute.subject', required=True, ondelete='cascade')
    topic_ids = fields.One2many('institute.topic', 'chapter_id', string='Topics')


class InstituteTopic(models.Model):
    _name = 'institute.topic'
    _description = 'Topic'

    name = fields.Char(required=True)
    chapter_id = fields.Many2one('institute.chapter', required=True, ondelete='cascade')
    standard_class_count = fields.Integer(
        string='Standard Class Count', default=1,
        help='Number of class sessions this topic normally requires'
    )