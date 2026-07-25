from odoo import models, fields, api
from datetime import timedelta


class InstituteBatch(models.Model):
    _name = 'institute.batch'
    _description = 'Batch'

    name = fields.Char(required=True)
    course_id = fields.Many2one('institute.course', required=True)
    student_ids = fields.Many2many('res.partner', string='Students')
    active = fields.Boolean(default=True)

    start_date = fields.Date(default=fields.Date.context_today)
    batch_completion_percent = fields.Float(compute='_compute_batch_progress', string='Completion %')
    projected_finish_date = fields.Date(compute='_compute_batch_progress', string='Projected Finish')
    lagging_flag = fields.Boolean(default=False, readonly=True, string='Behind Schedule')

    def _get_course_topics(self):
        self.ensure_one()
        return self.course_id.subject_ids.chapter_ids.topic_ids

    @api.depends('course_id.subject_ids.chapter_ids.topic_ids.completion_percent')
    def _compute_batch_progress(self):
        today = fields.Date.context_today(self)
        for batch in self:
            topics = batch._get_course_topics()
            avg = sum(topics.mapped('completion_percent')) / len(topics) if topics else 0.0
            batch.batch_completion_percent = avg
            if avg > 0 and batch.start_date:
                days_elapsed = max((today - batch.start_date).days, 1)
                total_days_needed = days_elapsed / avg * 100
                remaining_days = max(total_days_needed - days_elapsed, 0)
                batch.projected_finish_date = today + timedelta(days=remaining_days)
            else:
                batch.projected_finish_date = False

    def _cron_check_syllabus_lag(self):
        for batch in self.search([]):
            topics = batch._get_course_topics()
            batch.lagging_flag = bool(topics.filtered('is_lagging'))
            