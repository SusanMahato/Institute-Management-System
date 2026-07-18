{
    'name': 'Institute Management',
    'version': '1.0',
    'summary': 'Coaching institute scheduling, emergency substitution, and syllabus tracking',
    'category': 'Education',
    'depends': ['base', 'mail', 'hr', 'calendar'],
    'data': [
        'security/institute_groups.xml',
        'security/ir.model.access.csv',
        'views/curriculum_views.xml',
        'views/room_views.xml',
        'views/teacher_views.xml',
        'views/batch_views.xml',
    ],
    'installable': True,
    'application': True,
}