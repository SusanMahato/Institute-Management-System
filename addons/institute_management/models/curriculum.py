from odoo import models, fields, api


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
    session_ids = fields.One2many('institute.class.session', 'topic_id', string='Sessions')
    session_count = fields.Integer(
        compute='_compute_session_count', store=True, string='Scheduled Sessions'
    )
    syllabus_log_ids = fields.One2many('institute.syllabus.log', 'topic_id', string='Syllabus Logs')
    logged_count = fields.Integer(compute='_compute_progress', store=True, string='Sessions Logged')
    completion_percent = fields.Float(compute='_compute_progress', store=True, string='Completion %')
    progress_label = fields.Char(compute='_compute_progress', store=True, string='Progress')
    is_lagging = fields.Boolean(compute='_compute_is_lagging', store=True)

    @api.depends('session_ids.state')
    def _compute_session_count(self):
        for topic in self:
            topic.session_count = len(topic.session_ids.filtered(lambda s: s.state != 'cancelled'))

    @api.depends('syllabus_log_ids.completed', 'standard_class_count')
    def _compute_progress(self):
        for topic in self:
            logged = len(topic.syllabus_log_ids.filtered('completed'))
            planned = topic.standard_class_count or 1
            topic.logged_count = logged
            topic.completion_percent = min(100.0, (logged / planned) * 100)
            topic.progress_label = f"{logged}/{topic.standard_class_count} — {round(topic.completion_percent)}%"

    @api.depends('session_count', 'standard_class_count', 'completion_percent')
    def _compute_is_lagging(self):
        for topic in self:
            topic.is_lagging = (
                topic.session_count >= topic.standard_class_count
                and topic.completion_percent < 100
            )
            