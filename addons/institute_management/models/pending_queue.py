from odoo import api, models


class InstitutePendingQueue(models.AbstractModel):
    """Aggregation layer for the Pending Queue client action. Combines
    unallocated syllabus topics and pending teacher extension requests
    into one unified view, per the BRD's 'dedicated section' framing --
    kept separate from institute.dashboard since it's a distinct concern
    (scheduling backlog, not the coordinator's daily operating picture)."""
    _name = 'institute.pending.queue'
    _description = 'Pending Queue Aggregation'

    @api.model
    def get_pending_queue_data(self):
        Topic = self.env['institute.topic']
        unallocated_topics = Topic.search([('session_count', '=', 0)])
        topics_data = [{
            'id': t.id,
            'name': t.name,
            'chapter_name': t.chapter_id.name,
            'standard_class_count': t.standard_class_count,
        } for t in unallocated_topics]

        ExtensionRequest = self.env['institute.syllabus.extension.request']
        pending_requests = ExtensionRequest.search([('state', '=', 'draft')])
        requests_data = [{
            'id': r.id,
            'teacher_name': r.teacher_id.name,
            'batch_name': r.batch_id.name,
            'topic_name': r.topic_id.name,
            'extra_classes': r.extra_classes,
        } for r in pending_requests]

        return {
            'unallocated_topics': topics_data,
            'pending_extensions': requests_data,
        }
        