from odoo import models, fields, api
from odoo.exceptions import ValidationError


class InstituteSyllabusExtensionRequest(models.Model):
    _name = 'institute.syllabus.extension.request'
    _inherit = ['mail.thread']
    _description = 'Syllabus Extension Request'

    teacher_id = fields.Many2one('hr.employee', required=True, string='Teacher', tracking=True)
    batch_id = fields.Many2one('institute.batch', required=True, tracking=True)
    topic_id = fields.Many2one('institute.topic', required=True, tracking=True)
    extra_classes = fields.Integer(required=True, default=1, string='Extra Classes Needed')
    reason = fields.Selection([
        ('slower_comprehension', 'Slower batch comprehension'),
        ('extended_qa', 'Extended Q&A session'),
        ('technical_delay', 'Technical delay'),
    ], required=True)
    state = fields.Selection([
        ('draft', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='draft', required=True, tracking=True)
    requested_date = fields.Datetime(default=fields.Datetime.now, readonly=True)

    def action_approve(self):
        self.ensure_one()
        if self.state != 'draft':
            raise ValidationError("Only a pending request can be approved.")
        self.write({'state': 'approved'})
        self._send_approval_email()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Schedule Extra Class',
            'res_model': 'institute.class.session',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_teacher_id': self.teacher_id.id,
                'default_batch_id': self.batch_id.id,
                'default_topic_id': self.topic_id.id,
            },
        }

    def action_reject(self):
        for req in self:
            if req.state != 'draft':
                raise ValidationError("Only a pending request can be rejected.")
            req.write({'state': 'rejected'})

    def _send_approval_email(self):
        self.ensure_one()
        template = self.env.ref(
            'institute_management.mail_template_extension_approved', raise_if_not_found=False)
        if not template:
            return
        if not self.teacher_id.work_email:
            return
        template.send_mail(
            self.id,
            email_values={'email_to': self.teacher_id.work_email},
            force_send=True,
        )
        