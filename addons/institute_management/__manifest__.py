{
    'name': 'Institute Management',
    'version': '1.0',
    'summary': 'Coaching institute scheduling, emergency substitution, and syllabus tracking',
    'description': """
Institute Management System
============================
Conflict-free class scheduling, emergency teacher substitution (SOS) with
ranked candidate suggestions, syllabus pace tracking with lag detection,
batch progress projection, and role-based portals for coordinators,
teachers, and students.
""",
    'author': 'Susan Mahato',
    'license': 'OPL-1',
    'category': 'Education',
    'depends': ['base', 'mail', 'hr', 'calendar'],
    'data': [
        'security/institute_groups.xml',
        'security/ir.model.access.csv',
        'views/curriculum_views.xml',
        'views/dashboard_views.xml',
        'views/room_views.xml',
        'views/teacher_views.xml',
        'views/batch_views.xml',
        'views/session_views.xml',
        'views/syllabus_views.xml',
        'data/cron.xml',
        'wizard/substitute_teacher_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'institute_management/static/src/dashboard/dashboard.js',
            'institute_management/static/src/dashboard/dashboard.xml',
            'institute_management/static/src/dashboard/dashboard.scss',
        ],
    },
    'demo': [
        'data/demo.xml',
    ],
    'installable': True,
    'application': True,
}
