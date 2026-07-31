/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class InstituteDashboard extends Component {
    static template = "institute_management.Dashboard";

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
        this.state.data = await this.orm.call("institute.dashboard", "get_dashboard_data", []);
        this.state.loading = false;
    }

    openSession(sessionId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "institute.class.session",
            res_id: sessionId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openBatch(batchId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "institute.batch",
            res_id: batchId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("institute_management.dashboard", InstituteDashboard);
