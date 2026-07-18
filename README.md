# Institute Management System

Coaching institute management platform built on Odoo 19.
See `addons/institute_management/` for the custom module.

## Setup
1. `docker compose up -d`
2. Visit `localhost:8069`, create a database
3. Enable Developer Mode, Apps > Update Apps List
4. Install "Institute Management"

## Current Status

**Completed:**
- Curriculum hierarchy — Course, Subject, Chapter, Topic models (Course/Subject exposed in UI)
- Room model (name, building, floor, capacity, virtual room support)
- Teacher profile — extends `hr.employee` with qualified subjects, preferred teaching mode, maximum weekly workload
- Teacher availability check (`is_available()` method on `hr.employee`, using `resource.calendar.leaves`)

**In progress / upcoming:**
- Chapter & Topic UI exposure
- RBAC groups (Coordinator, Teacher, Student) and batch model
- Scheduling engine, conflict detection
- Emergency substitution (SOS) workflow
- Syllabus tracking

See the full roadmap in the project's design proposal documentation.

## Development Notes
- After adding/changing model fields, run a module upgrade (not just restart):
```
  docker compose exec odoo odoo -d institute_db -u institute_management --stop-after-init --db_host=postgres --db_port=5432 --db_user=odoo --db_password=odoo
```