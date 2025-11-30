/** @odoo-module */

import { registry } from "@web/core/registry";
import { AbstractSpreadsheetAction } from "@spreadsheet_edition/bundle/actions/abstract_spreadsheet_action";
import { SpreadsheetComponent } from "@spreadsheet/actions/spreadsheet_component";
import { SpreadsheetNavbar } from "@spreadsheet_edition/bundle/components/spreadsheet_navbar/spreadsheet_navbar";
import { load } from "@odoo/o-spreadsheet";

export class ProjectTaskSpreadsheetAction extends AbstractSpreadsheetAction {
    static template = "project_task_spreadsheet_report.ProjectTaskSpreadsheetAction";
    static path = "project-task-spreadsheet";
    resModel = "project.task.spreadsheet";

    _initializeWith(data) {
        super._initializeWith(data);
        this.taskId = data.task_id;

        // ensure the data is upgraded to the latest version
        this.spreadsheetData = load(this.spreadsheetData);

        // Update the filter directly in the raw data
        const taskFilter = this.spreadsheetData.globalFilters?.find(
            (filter) => filter.modelName === "project.task"
        );
        if (taskFilter && this.taskId) {
            taskFilter.defaultValue = {
                operator: "in",
                ids: [this.taskId],
            };
        }
    }
}

ProjectTaskSpreadsheetAction.components = {
    SpreadsheetComponent,
    SpreadsheetNavbar,
};

registry.category("actions").add("action_project_task_spreadsheet", ProjectTaskSpreadsheetAction, { force: true });
