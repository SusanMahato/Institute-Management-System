/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";

export class InstituteDashboard extends Component {
    static template = "institute_management.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ data: null, loading: true });

        this.syllabusChartRef = useRef("syllabusChart");
        this.workloadChartRef = useRef("workloadChart");
        this.syllabusChart = null;
        this.workloadChart = null;

        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");
            await this.loadData();
        });

        onMounted(() => this.renderCharts());
        onWillUnmount(() => {
            if (this.syllabusChart) this.syllabusChart.destroy();
            if (this.workloadChart) this.workloadChart.destroy();
        });
    }

    async loadData() {
        this.state.loading = true;
        this.state.data = await this.orm.call("institute.dashboard", "get_dashboard_data", []);
        this.state.loading = false;
    }

    renderCharts() {
        if (!this.state.data) {
            return;
        }
        this.renderSyllabusChart();
        this.renderWorkloadChart();
    }

    renderSyllabusChart() {
        const el = this.syllabusChartRef.el;
        if (!el) {
            return;
        }
        const rows = this.state.data.syllabus_progress;
        if (this.syllabusChart) {
            this.syllabusChart.destroy();
        }
        this.syllabusChart = new Chart(el, {
            type: "bar",
            data: {
                labels: rows.map((r) => r.name),
                datasets: [{
                    label: "Completion %",
                    data: rows.map((r) => r.completion_percent),
                    backgroundColor: rows.map((r) =>
                        r.completion_percent < 100 && r.completion_percent <= 60
                            ? "#dc3545"
                            : "#0d6efd"
                    ),
                }],
            },
            options: {
                indexAxis: "y",
                maintainAspectRatio: false,
                scales: { x: { min: 0, max: 100 } },
                plugins: { legend: { display: false } },
            },
        });
    }

    renderWorkloadChart() {
        const el = this.workloadChartRef.el;
        if (!el) {
            return;
        }
        const rows = this.state.data.teacher_workload;
        if (this.workloadChart) {
            this.workloadChart.destroy();
        }
        this.workloadChart = new Chart(el, {
            type: "bar",
            data: {
                labels: rows.map((r) => r.name),
                datasets: [{
                    label: "Active Sessions",
                    data: rows.map((r) => r.workload),
                    backgroundColor: "#6610f2",
                }],
            },
            options: {
                indexAxis: "y",
                maintainAspectRatio: false,
                scales: { x: { min: 0, ticks: { stepSize: 1 } } },
                plugins: { legend: { display: false } },
            },
        });
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

    openScheduleClass() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Schedule Class",
            res_model: "institute.class.session",
            views: [[false, "form"]],
            target: "current",
        });
    }

    openAssignSubstitute() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Pending Substitutions",
            res_model: "institute.class.session",
            domain: [["state", "=", "needs_substitute"]],
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openCreateBatch() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Create Batch",
            res_model: "institute.batch",
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("institute_management.dashboard", InstituteDashboard);
