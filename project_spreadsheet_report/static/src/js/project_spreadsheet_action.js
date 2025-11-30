/** @odoo-module */

import { registry } from "@web/core/registry";
import { AbstractSpreadsheetAction } from "@spreadsheet_edition/bundle/actions/abstract_spreadsheet_action";
import { SpreadsheetComponent } from "@spreadsheet/actions/spreadsheet_component";
import { SpreadsheetNavbar } from "@spreadsheet_edition/bundle/components/spreadsheet_navbar/spreadsheet_navbar";
import { load } from "@odoo/o-spreadsheet";

export class ProjectSpreadsheetAction extends AbstractSpreadsheetAction {
    static template = "project_spreadsheet_report.ProjectSpreadsheetAction";
    static path = "project-spreadsheet";
    resModel = "project.spreadsheet";

    _initializeWith(data) {
        super._initializeWith(data);
        this.projectId = data.project_id;

        // ensure the data is upgraded to the latest version
        this.spreadsheetData = load(this.spreadsheetData);

        // Update the filter directly in the raw data
        const projectFilter = this.spreadsheetData.globalFilters?.find(
            (filter) => filter.modelName === "project.project"
        );
        if (projectFilter && this.projectId) {
            projectFilter.defaultValue = {
                operator: "in",
                ids: [this.projectId],
            };
        }
    }
}

ProjectSpreadsheetAction.components = {
    SpreadsheetComponent,
    SpreadsheetNavbar,
};

registry.category("actions").add("action_project_spreadsheet", ProjectSpreadsheetAction, { force: true });
