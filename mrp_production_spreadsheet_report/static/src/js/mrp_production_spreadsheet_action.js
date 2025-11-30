/** @odoo-module */

import { registry } from "@web/core/registry";
import { AbstractSpreadsheetAction } from "@spreadsheet_edition/bundle/actions/abstract_spreadsheet_action";
import { SpreadsheetComponent } from "@spreadsheet/actions/spreadsheet_component";
import { SpreadsheetNavbar } from "@spreadsheet_edition/bundle/components/spreadsheet_navbar/spreadsheet_navbar";
import { load } from "@odoo/o-spreadsheet";

export class MrpProductionSpreadsheetAction extends AbstractSpreadsheetAction {
    static template = "mrp_production_spreadsheet_report.MrpProductionSpreadsheetAction";
    static path = "mrp-production-spreadsheet";
    resModel = "mrp.production.spreadsheet";

    _initializeWith(data) {
        super._initializeWith(data);
        this.productionId = data.production_id;

        // ensure the data is upgraded to the latest version
        this.spreadsheetData = load(this.spreadsheetData);

        // Update the filter directly in the raw data
        const productionFilter = this.spreadsheetData.globalFilters?.find(
            (filter) => filter.modelName === "mrp.production"
        );
        if (productionFilter && this.productionId) {
            productionFilter.defaultValue = {
                operator: "in",
                ids: [this.productionId],
            };
        }
    }
}

MrpProductionSpreadsheetAction.components = {
    SpreadsheetComponent,
    SpreadsheetNavbar,
};

registry.category("actions").add("action_mrp_production_spreadsheet", MrpProductionSpreadsheetAction, { force: true });
