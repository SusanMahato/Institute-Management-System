/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class InstitutePendingQueue extends Component {
    static template = "institute_management.PendingQueue";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ data: null, loading: true });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        this.state.data = await this.orm.call("institute.pending.queue", "get_pending_queue_data", []);
        this.state.loading = false;
    }

    openTopic(topicId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "institute.topic",
            res_id: topicId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openExtensionRequest(requestId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "institute.syllabus.extension.request",
            res_id: requestId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("institute_management.pending_queue", InstitutePendingQueue);
