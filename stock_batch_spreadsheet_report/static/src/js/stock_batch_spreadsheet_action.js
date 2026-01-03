import { registry } from "@web/core/registry";
import { AbstractSpreadsheetAction } from "@spreadsheet_edition/bundle/actions/abstract_spreadsheet_action";
import { SpreadsheetComponent } from "@spreadsheet/actions/spreadsheet_component";
import { SpreadsheetNavbar } from "@spreadsheet_edition/bundle/components/spreadsheet_navbar/spreadsheet_navbar";


export class StockBatchSpreadsheetAction extends AbstractSpreadsheetAction {
    static template = "stock_batch_spreadsheet_report.StockBatchSpreadsheetAction";
    static path = "stock-batch-spreadsheet";
    resModel = "stock.batch.spreadsheet";

    _initializeWith(data) {
        super._initializeWith(data);
        this.batchId = data.batch_id;



        // Update the filter directly in the raw data
        const batchFilter = this.spreadsheetData.globalFilters?.find(
            (filter) => filter.modelName === "stock.picking.batch"
        );
        if (batchFilter && this.batchId) {
            batchFilter.defaultValue = {
                operator: "in",
                ids: [this.batchId],
            };
        }
    }
}

StockBatchSpreadsheetAction.components = {
    SpreadsheetComponent,
    SpreadsheetNavbar,
};

registry.category("actions").add("action_stock_batch_spreadsheet", StockBatchSpreadsheetAction, { force: true });
