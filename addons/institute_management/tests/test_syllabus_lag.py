from datetime import datetime, timedelta

from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSyllabusLag(TransactionCase):
    """Tests for Topic progress/lag computation (models/curriculum.py),
    Batch progress + projected finish date (models/batch.py), and the
    daily _cron_check_syllabus_lag cron (data/cron.xml)."""

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
        # standard_class_count=2 so we can test partial completion / lag.
        cls.topic = cls.env['institute.topic'].create({
            'name': "Newton's First Law",
            'chapter_id': cls.chapter.id,
            'standard_class_count': 2,
        })

        cls.room_a = cls.env['institute.room'].create({'name': 'Room A'})
        cls.room_b = cls.env['institute.room'].create({'name': 'Room B'})

        cls.batch = cls.env['institute.batch'].create({
            'name': 'Physics Batch A',
            'course_id': cls.course.id,
            'start_date': datetime(2026, 7, 1).date(),
        })

        cls.teacher = cls.env['hr.employee'].create({
            'name': 'Teacher One',
            'subject_ids': [(6, 0, [cls.subject.id])],
        })

    def _create_session(self, room, start, state='scheduled'):
        session = self.env['institute.class.session'].create({
            'teacher_id': self.teacher.id,
            'room_id': room.id,
            'batch_id': self.batch.id,
            'topic_id': self.topic.id,
            'start_datetime': start,
            'end_datetime': start + timedelta(hours=1),
        })
        if state != 'scheduled':
            session.write({'state': state})
        return session

    def test_progress_with_no_logs(self):
        self.assertEqual(self.topic.logged_count, 0)
        self.assertEqual(self.topic.completion_percent, 0.0)
        self.assertIn('0/2', self.topic.progress_label)

    def test_completion_percent_with_one_of_two_logged(self):
        session = self._create_session(self.room_a, datetime(2026, 8, 3, 10, 0))
        self.env['institute.syllabus.log'].create({
            'session_id': session.id,
            'completed': True,
        })
        self.assertEqual(self.topic.logged_count, 1)
        self.assertEqual(self.topic.completion_percent, 50.0)
        self.assertIn('1/2', self.topic.progress_label)

    def test_completion_percent_ignores_uncompleted_logs(self):
        session = self._create_session(self.room_a, datetime(2026, 8, 3, 10, 0))
        self.env['institute.syllabus.log'].create({
            'session_id': session.id,
            'completed': False,
        })
        self.assertEqual(self.topic.logged_count, 0)
        self.assertEqual(self.topic.completion_percent, 0.0)

    def test_completion_percent_caps_at_100(self):
        # standard_class_count is 2; log 3 completed entries across
        # separate sessions to confirm the percent is capped, not 150%.
        for i, start in enumerate([
            datetime(2026, 8, 3, 9, 0),
            datetime(2026, 8, 3, 11, 0),
            datetime(2026, 8, 3, 13, 0),
        ]):
            room = self.room_a if i % 2 == 0 else self.room_b
            session = self._create_session(room, start)
            self.env['institute.syllabus.log'].create({
                'session_id': session.id,
                'completed': True,
            })
        self.assertEqual(self.topic.completion_percent, 100.0)

    def test_session_count_excludes_cancelled(self):
        self._create_session(self.room_a, datetime(2026, 8, 3, 9, 0))
        s2 = self._create_session(self.room_b, datetime(2026, 8, 3, 11, 0))
        s2.write({'state': 'cancelled'})
        self.assertEqual(self.topic.session_count, 1)

    def test_is_lagging_false_when_under_session_count(self):
        """Only 1 of 2 required sessions scheduled -> not lagging yet,
        even with 0% completion."""
        self._create_session(self.room_a, datetime(2026, 8, 3, 9, 0))
        self.assertFalse(self.topic.is_lagging)

    def test_is_lagging_true_when_sessions_done_but_incomplete(self):
        """Both required sessions have happened (session_count >=
        standard_class_count) but only one syllabus log was completed,
        so completion is under 100% -> lagging."""
        s1 = self._create_session(self.room_a, datetime(2026, 8, 3, 9, 0))
        self._create_session(self.room_b, datetime(2026, 8, 3, 11, 0))
        self.env['institute.syllabus.log'].create({
            'session_id': s1.id,
            'completed': True,
        })
        self.assertEqual(self.topic.session_count, 2)
        self.assertEqual(self.topic.completion_percent, 50.0)
        self.assertTrue(self.topic.is_lagging)

    def test_is_lagging_false_when_fully_completed(self):
        s1 = self._create_session(self.room_a, datetime(2026, 8, 3, 9, 0))
        s2 = self._create_session(self.room_b, datetime(2026, 8, 3, 11, 0))
        for s in (s1, s2):
            self.env['institute.syllabus.log'].create({
                'session_id': s.id,
                'completed': True,
            })
        self.assertEqual(self.topic.completion_percent, 100.0)
        self.assertFalse(self.topic.is_lagging)

    def test_batch_completion_percent_matches_topic_average(self):
        # Single topic under this course/batch, so batch % should equal
        # the topic's own completion_percent.
        session = self._create_session(self.room_a, datetime(2026, 8, 3, 9, 0))
        self.env['institute.syllabus.log'].create({
            'session_id': session.id,
            'completed': True,
        })
        self.assertEqual(self.batch.batch_completion_percent, self.topic.completion_percent)

    def test_batch_projected_finish_date_set_once_progress_started(self):
        session = self._create_session(self.room_a, datetime(2026, 8, 3, 9, 0))
        self.env['institute.syllabus.log'].create({
            'session_id': session.id,
            'completed': True,
        })
        self.assertTrue(self.batch.batch_completion_percent > 0)
        self.assertTrue(self.batch.projected_finish_date)

    def test_batch_projected_finish_date_false_when_no_progress(self):
        # No sessions/logs at all yet -> 0% progress -> no projection.
        self.assertEqual(self.batch.batch_completion_percent, 0.0)
        self.assertFalse(self.batch.projected_finish_date)

    def test_cron_sets_lagging_flag_true(self):
        s1 = self._create_session(self.room_a, datetime(2026, 8, 3, 9, 0))
        self._create_session(self.room_b, datetime(2026, 8, 3, 11, 0))
        self.env['institute.syllabus.log'].create({
            'session_id': s1.id,
            'completed': True,
        })
        self.assertFalse(self.batch.lagging_flag)  # not yet run
        self.batch._cron_check_syllabus_lag()
        self.assertTrue(self.batch.lagging_flag)

    def test_cron_sets_lagging_flag_false_when_on_track(self):
        s1 = self._create_session(self.room_a, datetime(2026, 8, 3, 9, 0))
        s2 = self._create_session(self.room_b, datetime(2026, 8, 3, 11, 0))
        for s in (s1, s2):
            self.env['institute.syllabus.log'].create({
                'session_id': s.id,
                'completed': True,
            })
        self.batch.lagging_flag = True  # simulate a previously-set flag
        self.batch._cron_check_syllabus_lag()
        self.assertFalse(self.batch.lagging_flag)
