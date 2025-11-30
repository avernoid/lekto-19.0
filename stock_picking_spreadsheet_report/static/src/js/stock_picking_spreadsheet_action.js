/** @odoo-module */

import { registry } from "@web/core/registry";
import { AbstractSpreadsheetAction } from "@spreadsheet_edition/bundle/actions/abstract_spreadsheet_action";
import { SpreadsheetComponent } from "@spreadsheet/actions/spreadsheet_component";
import { SpreadsheetNavbar } from "@spreadsheet_edition/bundle/components/spreadsheet_navbar/spreadsheet_navbar";
import { load } from "@odoo/o-spreadsheet";

export class StockPickingSpreadsheetAction extends AbstractSpreadsheetAction {
    static template = "stock_picking_spreadsheet_report.StockPickingSpreadsheetAction";
    static path = "stock-picking-spreadsheet";
    resModel = "stock.picking.spreadsheet";

    _initializeWith(data) {
        super._initializeWith(data);
        this.pickingId = data.picking_id;

        // ensure the data is upgraded to the latest version
        this.spreadsheetData = load(this.spreadsheetData);

        // Update the filter directly in the raw data
        const pickingFilter = this.spreadsheetData.globalFilters?.find(
            (filter) => filter.modelName === "stock.picking"
        );
        if (pickingFilter && this.pickingId) {
            pickingFilter.defaultValue = {
                operator: "in",
                ids: [this.pickingId],
            };
        }
    }
}

StockPickingSpreadsheetAction.components = {
    SpreadsheetComponent,
    SpreadsheetNavbar,
};

registry.category("actions").add("action_stock_picking_spreadsheet", StockPickingSpreadsheetAction, { force: true });
