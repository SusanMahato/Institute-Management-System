from datetime import datetime, timedelta

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSosEdgeCases(TransactionCase):
    """Edge cases for the SOS substitute workflow that the main
    test_sos_workflow.py suite doesn't cover: teacher on leave,
    overlapping-session exclusion, zero-candidate scenarios, and the
    model's constraint acting as a safety net if a wizard is ever
    misused to assign an unfit substitute directly."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.course = cls.env['institute.course'].create({'name': 'Physics'})
        cls.subject = cls.env['institute.subject'].create({
            'name': 'Mechanics',
            'course_id': cls.course.id,
        })
        cls.chapter = cls.env['institute.chapter'].create({
            'name': 'Laws of Motion',
            'subject_id': cls.subject.id,
        })
        cls.topic = cls.env['institute.topic'].create({
            'name': "Newton's First Law",
            'chapter_id': cls.chapter.id,
            'standard_class_count': 1,
        })

        cls.room = cls.env['institute.room'].create({'name': 'Room A'})
        cls.other_room = cls.env['institute.room'].create({'name': 'Room B'})
        cls.batch = cls.env['institute.batch'].create({
            'name': 'Physics Batch A',
            'course_id': cls.course.id,
        })

        cls.original_teacher = cls.env['hr.employee'].create({
            'name': 'Original Teacher',
            'subject_ids': [(6, 0, [cls.subject.id])],
        })

        cls.start = datetime(2026, 8, 3, 10, 0, 0)
        cls.end = cls.start + timedelta(hours=1)

        cls.session = cls.env['institute.class.session'].create({
            'teacher_id': cls.original_teacher.id,
            'room_id': cls.room.id,
            'batch_id': cls.batch.id,
            'topic_id': cls.topic.id,
            'start_datetime': cls.start,
            'end_datetime': cls.end,
        })

    def test_no_qualified_teachers_returns_empty_recordset_not_error(self):
        """With zero other qualified teachers in the system, both
        get_substitute_candidates() and the wizard's computed
        candidate_ids should resolve to an empty recordset, not raise."""
        self.session.action_mark_unavailable()
        candidates = self.session.get_substitute_candidates()
        self.assertEqual(len(candidates), 0)

        wizard = self.env['institute.substitute.teacher.wizard'].new({
            'session_id': self.session.id,
        })
        # Should not raise even though there is nothing to select.
        self.assertFalse(wizard.candidate_ids)

    def test_teacher_on_leave_excluded_from_candidates(self):
        """A qualified, otherwise-free teacher who has an approved leave
        overlapping the session's time should NOT be offered as a
        substitute candidate."""
        teacher_on_leave = self.env['hr.employee'].create({
            'name': 'On Leave Teacher',
            'subject_ids': [(6, 0, [self.subject.id])],
        })
        self.env['resource.calendar.leaves'].create({
            'name': 'Sick leave',
            'resource_id': teacher_on_leave.resource_id.id,
            'date_from': self.start - timedelta(hours=1),
            'date_to': self.end + timedelta(hours=1),
        })

        self.session.action_mark_unavailable()
        candidates = self.session.get_substitute_candidates()
        self.assertNotIn(teacher_on_leave, candidates)

    def test_teacher_with_overlapping_session_elsewhere_excluded(self):
        """A qualified, non-leave teacher who is already teaching another
        session that overlaps this time slot must not be offered as a
        candidate, even though they're otherwise free and qualified."""
        busy_teacher = self.env['hr.employee'].create({
            'name': 'Busy Elsewhere Teacher',
            'subject_ids': [(6, 0, [self.subject.id])],
        })
        self.env['institute.class.session'].create({
            'teacher_id': busy_teacher.id,
            'room_id': self.other_room.id,
            'batch_id': self.batch.id,
            'topic_id': self.topic.id,
            'start_datetime': self.start + timedelta(minutes=15),
            'end_datetime': self.end + timedelta(minutes=15),
        })

        self.session.action_mark_unavailable()
        candidates = self.session.get_substitute_candidates()
        self.assertNotIn(busy_teacher, candidates)

    def test_wizard_confirm_still_blocked_if_substitute_would_overlap(self):
        """Defense-in-depth: even if a wizard were ever misused (e.g. via
        a direct write, bypassing the computed candidate_ids) to assign a
        substitute who has a conflicting session, the class_session
        model's own overlap constraint must still reject it."""
        conflicted_teacher = self.env['hr.employee'].create({
            'name': 'Conflicted Teacher',
            'subject_ids': [(6, 0, [self.subject.id])],
        })
        self.env['institute.class.session'].create({
            'teacher_id': conflicted_teacher.id,
            'room_id': self.other_room.id,
            'batch_id': self.batch.id,
            'topic_id': self.topic.id,
            'start_datetime': self.start,
            'end_datetime': self.end,
        })

        self.session.action_mark_unavailable()
        wizard = self.env['institute.substitute.teacher.wizard'].create({
            'session_id': self.session.id,
            'substitute_teacher_id': conflicted_teacher.id,
        })
        with self.assertRaises(ValidationError):
            wizard.action_confirm()
