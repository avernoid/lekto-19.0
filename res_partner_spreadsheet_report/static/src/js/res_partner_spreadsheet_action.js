/** @odoo-module */

import { registry } from "@web/core/registry";
import { AbstractSpreadsheetAction } from "@spreadsheet_edition/bundle/actions/abstract_spreadsheet_action";
import { SpreadsheetComponent } from "@spreadsheet/actions/spreadsheet_component";
import { SpreadsheetNavbar } from "@spreadsheet_edition/bundle/components/spreadsheet_navbar/spreadsheet_navbar";
import { load } from "@odoo/o-spreadsheet";

export class ResPartnerSpreadsheetAction extends AbstractSpreadsheetAction {
    static template = "res_partner_spreadsheet_report.ResPartnerSpreadsheetAction";
    static path = "res-partner-spreadsheet";
    resModel = "res.partner.spreadsheet";

    _initializeWith(data) {
        super._initializeWith(data);
        this.partnerId = data.partner_id;

        // ensure the data is upgraded to the latest version
        this.spreadsheetData = load(this.spreadsheetData);

        // Update the filter directly in the raw data
        const partnerFilter = this.spreadsheetData.globalFilters?.find(
            (filter) => filter.modelName === "res.partner"
        );
        if (partnerFilter && this.partnerId) {
            partnerFilter.defaultValue = {
                operator: "in",
                ids: [this.partnerId],
            };
        }
    }
}

ResPartnerSpreadsheetAction.components = {
    SpreadsheetComponent,
    SpreadsheetNavbar,
};

registry.category("actions").add("action_res_partner_spreadsheet", ResPartnerSpreadsheetAction, { force: true });
