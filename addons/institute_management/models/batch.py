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
        template = self.env.ref(
            'institute_management.mail_template_syllabus_lag_alert', raise_if_not_found=False)
        coordinator_group = self.env.ref(
            'institute_management.group_institute_coordinator', raise_if_not_found=False)
        coordinator_users = self.env['res.users'].search(
            [('group_ids', 'in', coordinator_group.id)]) if coordinator_group else self.env['res.users']
        coordinator_emails = [u.email for u in coordinator_users if u.email]
        for batch in self.search([]):
            topics = batch._get_course_topics()
            was_lagging = batch.lagging_flag
            is_lagging = bool(topics.filtered('is_lagging'))
            batch.lagging_flag = is_lagging
            # Only alert on the transition into lagging, not every day it
            # stays lagging -- avoids spamming coordinators with repeats.
            if is_lagging and not was_lagging and template and coordinator_emails:
                template.send_mail(
                    batch.id,
                    email_values={'email_to': ','.join(coordinator_emails)},
                    force_send=True,
                )
                