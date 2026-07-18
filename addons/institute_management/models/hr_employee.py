from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    subject_ids = fields.Many2many('institute.subject', string='Qualified Subjects')
    preferred_mode = fields.Selection([
        ('on_site', 'On-site'),
        ('online', 'Online'),
        ('both', 'Both'),
    ], string='Preferred Teaching Mode', default='both')
    maximum_weekly_workload = fields.Integer(
        string='Maximum Weekly Workload', default=20,
        help='Maximum number of class sessions this teacher can be assigned per week'
    )