from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestRbac(TransactionCase):
    """Tests for security/institute_groups.xml and
    security/ir.model.access.csv.

    Ground truth taken directly from ir.model.access.csv (not from
    project notes): the Teacher group has NO access rows at all for
    institute.chapter, institute.topic, or institute.room -- only
    read-only access to institute.course, institute.subject,
    institute.batch, and institute.class.session, plus read/write/create
    (no unlink) on institute.syllabus.log. The Student group has no
    access rows on any institute.* model. Coordinator has full CRUD on
    everything and implies the Teacher group."""

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
        })
        cls.room = cls.env['institute.room'].create({'name': 'Room A'})
        cls.batch = cls.env['institute.batch'].create({
            'name': 'Physics Batch A',
            'course_id': cls.course.id,
        })

        Users = cls.env['res.users'].with_context(no_reset_password=True)

        cls.teacher_user = Users.create({
            'name': 'RBAC Teacher',
            'login': 'rbac_teacher@example.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('institute_management.group_institute_teacher').id,
            ])],
        })
        cls.coordinator_user = Users.create({
            'name': 'RBAC Coordinator',
            'login': 'rbac_coordinator@example.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('institute_management.group_institute_coordinator').id,
            ])],
        })
        cls.student_user = Users.create({
            'name': 'RBAC Student',
            'login': 'rbac_student@example.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('institute_management.group_institute_student').id,
            ])],
        })

    # --- Teacher: read-only models (course, subject, batch, session) ---

    def test_teacher_can_read_course(self):
        self.course.with_user(self.teacher_user).read(['name'])

    def test_teacher_cannot_create_course(self):
        with self.assertRaises(AccessError):
            self.env['institute.course'].with_user(self.teacher_user).create({'name': 'New Course'})

    def test_teacher_cannot_write_course(self):
        with self.assertRaises(AccessError):
            self.course.with_user(self.teacher_user).write({'name': 'Changed'})

    def test_teacher_cannot_unlink_batch(self):
        with self.assertRaises(AccessError):
            self.batch.with_user(self.teacher_user).unlink()

    def test_teacher_can_read_session_model(self):
        # No session record needed for a pure model-access read check.
        self.env['institute.class.session'].with_user(self.teacher_user).search([])

    def test_teacher_cannot_create_session(self):
        with self.assertRaises(AccessError):
            self.env['institute.class.session'].with_user(self.teacher_user).create({
                'teacher_id': self.teacher_user.employee_id.id or self.env['hr.employee'].create({'name': 'x'}).id,
                'room_id': self.room.id,
                'batch_id': self.batch.id,
                'topic_id': self.topic.id,
                'start_datetime': '2026-08-03 10:00:00',
                'end_datetime': '2026-08-03 11:00:00',
            })

    # --- Teacher: zero access (chapter, topic, room) ---

    def test_teacher_has_no_access_to_chapter(self):
        with self.assertRaises(AccessError):
            self.chapter.with_user(self.teacher_user).read(['name'])

    def test_teacher_has_no_access_to_topic(self):
        with self.assertRaises(AccessError):
            self.topic.with_user(self.teacher_user).read(['name'])

    def test_teacher_has_no_access_to_room(self):
        with self.assertRaises(AccessError):
            self.room.with_user(self.teacher_user).read(['name'])

    # --- Teacher: syllabus log (read/write/create yes, unlink no) ---

    def test_teacher_can_create_and_write_syllabus_log(self):
        session = self.env['institute.class.session'].create({
            'teacher_id': self.env['hr.employee'].create({
                'name': 'Qualified Teacher',
                'subject_ids': [(6, 0, [self.subject.id])],
            }).id,
            'room_id': self.room.id,
            'batch_id': self.batch.id,
            'topic_id': self.topic.id,
            'start_datetime': '2026-08-03 10:00:00',
            'end_datetime': '2026-08-03 11:00:00',
        })
        log = self.env['institute.syllabus.log'].with_user(self.teacher_user).create({
            'session_id': session.id,
            'completed': True,
        })
        log.with_user(self.teacher_user).write({'notes': 'Covered in class'})

    def test_teacher_cannot_unlink_syllabus_log(self):
        session = self.env['institute.class.session'].create({
            'teacher_id': self.env['hr.employee'].create({
                'name': 'Qualified Teacher',
                'subject_ids': [(6, 0, [self.subject.id])],
            }).id,
            'room_id': self.room.id,
            'batch_id': self.batch.id,
            'topic_id': self.topic.id,
            'start_datetime': '2026-08-03 10:00:00',
            'end_datetime': '2026-08-03 11:00:00',
        })
        log = self.env['institute.syllabus.log'].create({
            'session_id': session.id,
            'completed': True,
        })
        with self.assertRaises(AccessError):
            log.with_user(self.teacher_user).unlink()

    # --- Coordinator: full CRUD everywhere, including teacher-only-blocked models ---

    def test_coordinator_full_crud_on_course(self):
        course = self.env['institute.course'].with_user(self.coordinator_user).create({'name': 'Chemistry'})
        course.with_user(self.coordinator_user).write({'name': 'Chemistry Updated'})
        course.with_user(self.coordinator_user).read(['name'])
        course.with_user(self.coordinator_user).unlink()

    def test_coordinator_full_crud_on_room(self):
        room = self.env['institute.room'].with_user(self.coordinator_user).create({'name': 'Room Z'})
        room.with_user(self.coordinator_user).write({'name': 'Room Z Updated'})
        room.with_user(self.coordinator_user).unlink()

    def test_coordinator_full_crud_on_chapter(self):
        chapter = self.env['institute.chapter'].with_user(self.coordinator_user).create({
            'name': 'New Chapter',
            'subject_id': self.subject.id,
        })
        chapter.with_user(self.coordinator_user).write({'name': 'Updated Chapter'})
        chapter.with_user(self.coordinator_user).unlink()

    # --- Student: no access to any institute model ---

    def test_student_has_no_access_to_course(self):
        with self.assertRaises(AccessError):
            self.course.with_user(self.student_user).read(['name'])

    def test_student_has_no_access_to_session(self):
        with self.assertRaises(AccessError):
            self.env['institute.class.session'].with_user(self.student_user).search([])
