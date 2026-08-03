import logging
import requests
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


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

    def _send_sms(self, to_number, message):
        if not to_number:
            _logger.info("No phone number on file; skipping SMS.")
            return
        ICP = self.env['ir.config_parameter'].sudo()
        account_sid = ICP.get_param('institute_management.twilio_account_sid')
        auth_token = ICP.get_param('institute_management.twilio_auth_token')
        from_number = ICP.get_param('institute_management.twilio_from_number')
        if not (account_sid and auth_token and from_number):
            _logger.warning("Twilio credentials not configured; skipping SMS.")
            return
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        try:
            resp = requests.post(
                url,
                data={'To': to_number, 'From': from_number, 'Body': message},
                auth=(account_sid, auth_token),
                timeout=10,
            )
            _logger.info("Twilio SMS response: %s %s", resp.status_code, resp.text[:200])
        except Exception as e:
            _logger.error("Failed to send SMS via Twilio: %s", e)

    def _send_substitute_email(self, session):
        template = self.env.ref(
            'institute_management.mail_template_substitute_assignment', raise_if_not_found=False)
        if not template:
            _logger.warning("Substitute assignment email template not found; skipping email.")
            return
        if not self.substitute_teacher_id.work_email:
            _logger.info("No email on file for substitute teacher; skipping email.")
            return
        template.send_mail(
            session.id,
            email_values={'email_to': self.substitute_teacher_id.work_email},
            force_send=True,
        )

    def action_confirm(self):
        self.ensure_one()
        session = self.session_id
        old_teacher = session.original_teacher_id or session.teacher_id

        session.write({
            'teacher_id': self.substitute_teacher_id.id,
            'state': 'substituted',
            'acknowledged': False,
            'acknowledged_by_id': False,
            'acknowledged_at': False,
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

        self._send_sms(
            self.substitute_teacher_id.mobile_phone,
            f"You've been assigned to teach {session.topic_id.name} "
            f"on {session.start_datetime}. Check the portal for details."
        )

        self._send_substitute_email(session)

        return {'type': 'ir.actions.act_window_close'}
    