# Institute Management System

A custom Odoo 19 module for coaching institutes, built to solve three concrete
operational problems: **conflict-free class scheduling**, **emergency teacher
substitution (SOS)**, and **syllabus pace tracking** — with role-based portals
for coordinators, teachers, and students.

Built as a 4-week MVP internship project on top of Odoo instead of a custom
stack, to leverage the supervising team's existing Odoo expertise.

---

## Features

- **Curriculum hierarchy** — Course → Subject → Chapter → Topic, with full
  CRUD views at every level.
- **Conflict-free scheduling** — class sessions are validated against both
  teacher and room double-booking, with strict overlap detection (not just
  exact-time clashes).
- **Emergency substitution (SOS) workflow** — a teacher can be marked
  unavailable for a session; the system ranks qualified, available
  substitutes by current workload, then by sessions scheduled that day, then
  alphabetically; a coordinator confirms the reassignment in one click.
- **Substitution acknowledgment** — the newly assigned substitute sees a
  persistent banner on the session until they acknowledge it, recording who
  acknowledged and when.
- **Syllabus pace tracking** — teachers log topic completion after each
  class; each topic tracks a completion percentage and flags itself as
  "lagging" if its planned sessions have run out but coverage isn't at 100%.
- **Batch progress & projected finish date** — average completion percentage
  across a batch's curriculum, with a simple linear projection of the
  batch's finish date based on progress so far.
- **Live Floorplan** — a kanban view of rooms showing real-time status
  (active / starting soon / needs substitute / free), color-coded.
- **SMS notifications** — a newly assigned substitute is notified by SMS
  (via Twilio) in addition to an in-app chatter message and bus
  notification.
- **Role-based access control** — Coordinator (full access), Teacher
  (scoped, mostly read-only with syllabus logging rights), and Student
  groups, enforced at the model level.

## Tech stack

- **Odoo 19.0**, custom module `institute_management`
- **PostgreSQL 16**
- **Docker Compose** for local development
- **Twilio REST API** for SMS (called directly via `requests`, not Odoo's
  IAP-based SMS framework)

## Repository structure

```
institute_management/
├── models/
│   ├── curriculum.py       # Course, Subject, Chapter, Topic
│   ├── room.py              # Room + live floorplan status
│   ├── hr_employee.py       # Teacher fields, availability, substitute ranking
│   ├── batch.py              # Batch progress/lag tracking
│   ├── class_session.py     # Core scheduling model, constraints, SOS actions
│   └── syllabus.py           # Syllabus Log
├── wizard/
│   └── substitute_teacher_wizard.py
├── views/
├── security/
│   ├── institute_groups.xml
│   └── ir.model.access.csv
├── data/
│   ├── demo.xml
│   └── cron.xml
├── tests/
│   ├── test_class_session.py
│   ├── test_sos_workflow.py
│   ├── test_sos_edge_cases.py
│   ├── test_syllabus_lag.py
│   └── test_rbac.py
└── __manifest__.py
```

## Setup

This project runs via Docker Compose: `postgres:16` + `odoo:19.0`, with
addons mounted at `./addons:/mnt/extra-addons`.

```powershell
docker compose up -d
```

The Odoo web interface will be available at `http://localhost:8069`. On
first run, create the `institute_db` database and install the
**Institute Management** module from Apps.

### Upgrading after a model/field/view change

```powershell
docker compose exec odoo odoo -d institute_db -u institute_management --stop-after-init --db_host=postgres --db_port=5432 --db_user=odoo --db_password=odoo
docker compose restart odoo
```

The restart is required for new models — an upgrade (`-u`) alone updates the
database schema, but the running server process doesn't reliably pick up
brand-new models until it's restarted.

### Odoo shell (for debugging)

```powershell
docker compose exec odoo odoo shell -d institute_db --db_host=postgres --db_port=5432 --db_user=odoo --db_password=odoo
```

## Running the automated tests

The test suite (47 tests) covers scheduling constraints, the SOS workflow
(including edge cases), syllabus lag detection, and RBAC. Run it with:

```powershell
docker compose run --rm odoo odoo -d institute_db -u institute_management --test-enable --test-tags institute_management --stop-after-init --db_host=postgres --db_port=5432 --db_user=odoo --db_password=odoo
```

`docker compose run --rm` is used instead of `exec` so the test run gets its
own container and doesn't conflict with the already-running Odoo web
server's port.

## Configuration

### Twilio SMS

SMS credentials are stored via `ir.config_parameter`:

- `institute_management.twilio_account_sid`
- `institute_management.twilio_auth_token`
- `institute_management.twilio_from_number`

**Note:** these are currently stored as plain config parameters for
development convenience. For production, move them to environment variables
or a secrets manager.

## Role-based access

| Model | Coordinator | Teacher | Student |
|---|---|---|---|
| Course / Subject | Full CRUD | Read-only | No access |
| Chapter / Topic | Full CRUD | No access | No access |
| Room | Full CRUD | No access | No access |
| Batch | Full CRUD | Read-only | No access |
| Class Session | Full CRUD | Read-only | No access |
| Syllabus Log | Full CRUD | Read/Write/Create (no delete) | No access |

`institute_management.group_institute_coordinator` implies
`group_institute_teacher`, so coordinators automatically have everything
teachers have, plus full CRUD.

## Known limitations (out of scope for this MVP)

Per the original design proposal, the following are explicitly deferred to
a later phase:

- Teacher/Student mobile apps
- Full immutable audit logs (only Odoo's chatter-based logging exists today)
- Syllabus extension request workflow
- Payroll integration
- Advanced analytics
- Printable/exportable timetable reports

## Status

19 of 20 planned development days complete. Day 20 (final): automated
tests, bug fixing, documentation, and demo preparation.
