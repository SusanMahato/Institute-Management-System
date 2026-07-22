from odoo import models, fields


class InstituteBatch(models.Model):
    _name = 'institute.batch'
    _description = 'Batch'

    name = fields.Char(required=True)
    course_id = fields.Many2one('institute.course', required=True)
    student_ids = fields.Many2many('res.partner', string='Students')
    active = fields.Boolean(default=True)
    