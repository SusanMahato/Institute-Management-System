from datetime import datetime, timedelta

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestClassSession(TransactionCase):
    """Tests for institute.class.session overlap and qualification
    constraints (_check_teacher_overlap, _check_room_overlap,
    _check_teacher_qualified in models/class_session.py)."""

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

        cls.room_a = cls.env['institute.room'].create({'name': 'Room A'})
        cls.room_b = cls.env['institute.room'].create({'name': 'Room B'})

        cls.batch = cls.env['institute.batch'].create({
            'name': 'Physics Batch A',
            'course_id': cls.course.id,
        })

        # Qualified teachers (have the subject in subject_ids)
        cls.teacher_1 = cls.env['hr.employee'].create({
            'name': 'Teacher One',
            'subject_ids': [(6, 0, [cls.subject.id])],
        })
        cls.teacher_2 = cls.env['hr.employee'].create({
            'name': 'Teacher Two',
            'subject_ids': [(6, 0, [cls.subject.id])],
        })
        # Unqualified teacher (no subject_ids set)
        cls.teacher_unqualified = cls.env['hr.employee'].create({
            'name': 'Teacher Unqualified',
        })

        cls.start = datetime(2026, 8, 3, 10, 0, 0)
        cls.end = cls.start + timedelta(hours=1)

    def _create_session(self, teacher, room, start, end, batch=None):
        return self.env['institute.class.session'].create({
            'teacher_id': teacher.id,
            'room_id': room.id,
            'batch_id': (batch or self.batch).id,
            'topic_id': self.topic.id,
            'start_datetime': start,
            'end_datetime': end,
        })

    def test_baseline_session_creates_ok(self):
        """A single well-formed session should create without error."""
        session = self._create_session(self.teacher_1, self.room_a, self.start, self.end)
        self.assertEqual(session.state, 'scheduled')
        self.assertEqual(session.subject_id, self.subject)

    def test_teacher_overlap_rejected(self):
        """Same teacher, overlapping time, different rooms -> ValidationError."""
        self._create_session(self.teacher_1, self.room_a, self.start, self.end)
        overlapping_start = self.start + timedelta(minutes=30)
        overlapping_end = overlapping_start + timedelta(hours=1)
        with self.assertRaises(ValidationError):
            self._create_session(self.teacher_1, self.room_b, overlapping_start, overlapping_end)

    def test_room_overlap_rejected(self):
        """Same room, overlapping time, different (qualified) teachers -> ValidationError."""
        self._create_session(self.teacher_1, self.room_a, self.start, self.end)
        overlapping_start = self.start + timedelta(minutes=30)
        overlapping_end = overlapping_start + timedelta(hours=1)
        with self.assertRaises(ValidationError):
            self._create_session(self.teacher_2, self.room_a, overlapping_start, overlapping_end)

    def test_back_to_back_sessions_allowed(self):
        """Adjacent sessions (end == next start) are NOT an overlap
        (constraint uses strict < / > , not <=/>=), so this should succeed
        for both the same teacher and the same room."""
        self._create_session(self.teacher_1, self.room_a, self.start, self.end)
        next_start = self.end
        next_end = next_start + timedelta(hours=1)
        session2 = self._create_session(self.teacher_1, self.room_a, next_start, next_end)
        self.assertEqual(session2.state, 'scheduled')

    def test_cancelled_session_excluded_from_overlap_check(self):
        """A cancelled session must not block a new overlapping session
        for the same teacher/room."""
        session1 = self._create_session(self.teacher_1, self.room_a, self.start, self.end)
        session1.write({'state': 'cancelled'})

        overlapping_start = self.start + timedelta(minutes=15)
        overlapping_end = overlapping_start + timedelta(hours=1)
        # Should NOT raise, since session1 is now cancelled.
        session2 = self._create_session(self.teacher_1, self.room_a, overlapping_start, overlapping_end)
        self.assertEqual(session2.state, 'scheduled')

    def test_unqualified_teacher_rejected(self):
        """Teacher without the topic's subject in subject_ids -> ValidationError."""
        with self.assertRaises(ValidationError):
            self._create_session(self.teacher_unqualified, self.room_a, self.start, self.end)
