from datetime import datetime, timedelta

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSosWorkflow(TransactionCase):
    """Tests for the SOS substitute-teacher workflow:
    action_mark_unavailable, find_available_substitutes (ranking),
    the substitute_teacher_wizard's action_confirm, and the
    acknowledgment flow (models/class_session.py, models/hr_employee.py,
    wizard/substitute_teacher_wizard.py)."""

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
        cls.batch = cls.env['institute.batch'].create({
            'name': 'Physics Batch A',
            'course_id': cls.course.id,
        })

        cls.original_teacher = cls.env['hr.employee'].create({
            'name': 'Original Teacher',
            'subject_ids': [(6, 0, [cls.subject.id])],
        })
        # Two qualified substitute candidates with different existing
        # workloads, so ranking is deterministic and testable.
        cls.teacher_busy = cls.env['hr.employee'].create({
            'name': 'Busy Teacher',
            'subject_ids': [(6, 0, [cls.subject.id])],
        })
        cls.teacher_free = cls.env['hr.employee'].create({
            'name': 'Free Teacher',
            'subject_ids': [(6, 0, [cls.subject.id])],
        })
        # Unqualified teacher must never show up as a candidate.
        cls.teacher_unqualified = cls.env['hr.employee'].create({
            'name': 'Unqualified Teacher',
        })

        cls.start = datetime(2026, 8, 3, 10, 0, 0)
        cls.end = cls.start + timedelta(hours=1)

        # Give teacher_busy an extra, non-overlapping session elsewhere so
        # their workload count is higher than teacher_free's.
        other_room = cls.env['institute.room'].create({'name': 'Room B'})
        cls.env['institute.class.session'].create({
            'teacher_id': cls.teacher_busy.id,
            'room_id': other_room.id,
            'batch_id': cls.batch.id,
            'topic_id': cls.topic.id,
            'start_datetime': cls.start - timedelta(hours=3),
            'end_datetime': cls.start - timedelta(hours=2),
        })

        # The session that will need a substitute.
        cls.session = cls.env['institute.class.session'].create({
            'teacher_id': cls.original_teacher.id,
            'room_id': cls.room.id,
            'batch_id': cls.batch.id,
            'topic_id': cls.topic.id,
            'start_datetime': cls.start,
            'end_datetime': cls.end,
        })

    def test_mark_unavailable_sets_state_and_original_teacher(self):
        self.session.action_mark_unavailable()
        self.assertEqual(self.session.state, 'needs_substitute')
        self.assertEqual(self.session.original_teacher_id, self.original_teacher)

    def test_mark_unavailable_rejected_if_not_scheduled(self):
        """Only a 'scheduled' session can be marked as needing a substitute."""
        self.session.action_mark_unavailable()  # now needs_substitute
        with self.assertRaises(ValidationError):
            self.session.action_mark_unavailable()

    def test_find_available_substitutes_excludes_unqualified(self):
        self.session.action_mark_unavailable()
        candidates = self.session.get_substitute_candidates()
        self.assertNotIn(self.teacher_unqualified, candidates)
        self.assertIn(self.teacher_free, candidates)
        self.assertIn(self.teacher_busy, candidates)

    def test_find_available_substitutes_excludes_original_teacher(self):
        self.session.action_mark_unavailable()
        candidates = self.session.get_substitute_candidates()
        self.assertNotIn(self.original_teacher, candidates)

    def test_find_available_substitutes_ranking_by_workload(self):
        """Lower current workload should be ranked first."""
        self.session.action_mark_unavailable()
        candidates = self.session.get_substitute_candidates()
        self.assertEqual(candidates[0], self.teacher_free)

    def test_wizard_confirm_reassigns_and_resets_acknowledgment(self):
        self.session.action_mark_unavailable()
        # Simulate a prior acknowledgment to prove action_confirm resets it.
        self.session.write({
            'acknowledged': True,
            'acknowledged_by_id': self.original_teacher.id,
            'acknowledged_at': self.start,
        })

        wizard = self.env['institute.substitute.teacher.wizard'].create({
            'session_id': self.session.id,
            'substitute_teacher_id': self.teacher_free.id,
            'reason': 'Sick leave',
        })
        wizard.action_confirm()

        self.assertEqual(self.session.teacher_id, self.teacher_free)
        self.assertEqual(self.session.state, 'substituted')
        self.assertFalse(self.session.acknowledged)
        self.assertFalse(self.session.acknowledged_by_id)
        self.assertFalse(self.session.acknowledged_at)

    def test_wizard_confirm_posts_chatter_message(self):
        self.session.action_mark_unavailable()
        wizard = self.env['institute.substitute.teacher.wizard'].create({
            'session_id': self.session.id,
            'substitute_teacher_id': self.teacher_free.id,
            'reason': 'Sick leave',
        })
        message_count_before = len(self.session.message_ids)
        wizard.action_confirm()
        self.assertGreater(len(self.session.message_ids), message_count_before)

    def test_acknowledge_sets_fields(self):
        self.session.action_mark_unavailable()
        wizard = self.env['institute.substitute.teacher.wizard'].create({
            'session_id': self.session.id,
            'substitute_teacher_id': self.teacher_free.id,
        })
        wizard.action_confirm()
        self.assertFalse(self.session.acknowledged)

        self.session.action_acknowledge()
        self.assertTrue(self.session.acknowledged)
        # acknowledged_by_id is set from the (now substitute) teacher_id
        # on the session, per action_acknowledge's implementation.
        self.assertEqual(self.session.acknowledged_by_id, self.teacher_free)
        self.assertTrue(self.session.acknowledged_at)
