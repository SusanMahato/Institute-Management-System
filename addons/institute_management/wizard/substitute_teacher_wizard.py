from odoo import models, fields, api


class SubstituteTeacherWizard(models.TransientModel):
    _name = 'institute.substitute.teacher.wizard'
    _description = 'Assign Substitute Teacher'

    session_id = fields.Many2one('institute.class.session', required=True)
    candidate_ids = fields.Many2many('hr.employee', compute='_compute_candidates', string='Available Substitutes')
    substitute_teacher_id = fields.Many2one('hr.employee', string='Select Substitute', required=True)
    reason = fields.Char(string='Reason')

    @api.depends('session_id')
    def _compute_candidates(self):
        for wizard in self:
            wizard.candidate_ids = wizard.session_id.get_substitute_candidates() if wizard.session_id else False

    def action_confirm(self):
        self.ensure_one()
        session = self.session_id
        old_teacher = session.original_teacher_id or session.teacher_id

        session.write({
            'teacher_id': self.substitute_teacher_id.id,
            'state': 'substituted',
        })

        session.message_post(
            body=(
                f"Substitute assigned: {old_teacher.name} → {self.substitute_teacher_id.name}. "
                f"Reason: {self.reason or 'Not specified'}"
            )
        )

        self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'simple_notification',
            {
                'title': 'Substitute Assigned',
                'message': f"{self.substitute_teacher_id.name} assigned to {session.topic_id.name}",
            },
        )
        return {'type': 'ir.actions.act_window_close'}
    