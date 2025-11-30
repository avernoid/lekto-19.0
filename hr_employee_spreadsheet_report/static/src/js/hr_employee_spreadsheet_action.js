/** @odoo-module */

import { registry } from "@web/core/registry";
import { AbstractSpreadsheetAction } from "@spreadsheet_edition/bundle/actions/abstract_spreadsheet_action";
import { SpreadsheetComponent } from "@spreadsheet/actions/spreadsheet_component";
import { SpreadsheetNavbar } from "@spreadsheet_edition/bundle/components/spreadsheet_navbar/spreadsheet_navbar";
import { load } from "@odoo/o-spreadsheet";

export class HrEmployeeSpreadsheetAction extends AbstractSpreadsheetAction {
    static template = "hr_employee_spreadsheet_report.HrEmployeeSpreadsheetAction";
    static path = "hr-employee-spreadsheet";
    resModel = "hr.employee.spreadsheet";

    _initializeWith(data) {
        super._initializeWith(data);
        this.employeeId = data.employee_id;

        // ensure the data is upgraded to the latest version
        this.spreadsheetData = load(this.spreadsheetData);

        // Update the filter directly in the raw data
        const employeeFilter = this.spreadsheetData.globalFilters?.find(
            (filter) => filter.modelName === "hr.employee"
        );
        if (employeeFilter && this.employeeId) {
            employeeFilter.defaultValue = {
                operator: "in",
                ids: [this.employeeId],
            };
        }
    }
}

HrEmployeeSpreadsheetAction.components = {
    SpreadsheetComponent,
    SpreadsheetNavbar,
};

registry.category("actions").add("action_hr_employee_spreadsheet", HrEmployeeSpreadsheetAction, { force: true });
