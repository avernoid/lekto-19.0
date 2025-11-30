/** @odoo-module */

import { registry } from "@web/core/registry";
import { AbstractSpreadsheetAction } from "@spreadsheet_edition/bundle/actions/abstract_spreadsheet_action";
import { SpreadsheetComponent } from "@spreadsheet/actions/spreadsheet_component";
import { SpreadsheetNavbar } from "@spreadsheet_edition/bundle/components/spreadsheet_navbar/spreadsheet_navbar";
import { load } from "@odoo/o-spreadsheet";

export class SaleOrderReportSpreadsheetAction extends AbstractSpreadsheetAction {
    static template = "sale_order_spreadsheet_report.SaleOrderReportSpreadsheetAction";
    static path = "sale-order-report-spreadsheet";
    resModel = "sale.order.report.spreadsheet";

    _initializeWith(data) {
        super._initializeWith(data);
        this.orderId = data.order_id;

        // ensure the data is upgraded to the latest version
        this.spreadsheetData = load(this.spreadsheetData);

        // Update the filter directly in the raw data
        const orderFilter = this.spreadsheetData.globalFilters?.find(
            (filter) => filter.modelName === "sale.order"
        );
        if (orderFilter && this.orderId) {
            orderFilter.defaultValue = {
                operator: "in",
                ids: [this.orderId],
            };
        }
    }
}

SaleOrderReportSpreadsheetAction.components = {
    SpreadsheetComponent,
    SpreadsheetNavbar,
};

registry.category("actions").add("action_sale_order_report_spreadsheet", SaleOrderReportSpreadsheetAction, { force: true });
