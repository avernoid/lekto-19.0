/** @odoo-module */

import { registry } from "@web/core/registry";
import { AbstractSpreadsheetAction } from "@spreadsheet_edition/bundle/actions/abstract_spreadsheet_action";
import { SpreadsheetComponent } from "@spreadsheet/actions/spreadsheet_component";
import { SpreadsheetNavbar } from "@spreadsheet_edition/bundle/components/spreadsheet_navbar/spreadsheet_navbar";
import { load } from "@odoo/o-spreadsheet";

export class AccountInvoiceSpreadsheetAction extends AbstractSpreadsheetAction {
    static template = "account_invoice_spreadsheet_report.AccountInvoiceSpreadsheetAction";
    static path = "account-invoice-spreadsheet";
    resModel = "account.invoice.spreadsheet";

    _initializeWith(data) {
        super._initializeWith(data);
        this.invoiceId = data.invoice_id;

        // ensure the data is upgraded to the latest version
        this.spreadsheetData = load(this.spreadsheetData);

        // Update the filter directly in the raw data
        const invoiceFilter = this.spreadsheetData.globalFilters?.find(
            (filter) => filter.modelName === "account.move"
        );
        if (invoiceFilter && this.invoiceId) {
            invoiceFilter.defaultValue = {
                operator: "in",
                ids: [this.invoiceId],
            };
        }
    }
}

AccountInvoiceSpreadsheetAction.components = {
    SpreadsheetComponent,
    SpreadsheetNavbar,
};

registry.category("actions").add("action_account_invoice_spreadsheet", AccountInvoiceSpreadsheetAction, { force: true });
