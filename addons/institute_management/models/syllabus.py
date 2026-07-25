from odoo import models, fields, api


class InstituteSyllabusLog(models.Model):
    _name = 'institute.syllabus.log'
    _description = 'Syllabus Log'

    session_id = fields.Many2one('institute.class.session', required=True, ondelete='cascade')
    topic_id = fields.Many2one(related='session_id.topic_id', store=True, string='Topic')
    completed = fields.Boolean(default=True, string='Topic Covered')
    notes = fields.Char()
    log_date = fields.Datetime(default=fields.Datetime.now, readonly=True)
    