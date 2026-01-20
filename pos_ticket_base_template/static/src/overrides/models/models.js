/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    getReportActionRef() {
        return "account.account_invoices";
    },
    async getReportActionValue(order_reference) {
        try {
            const reportActionRef = this.getReportActionRef();
            const reportActionValue = await this.data.call(
                "pos.order",
                "generate_pos_ui_report_action_value",
                [order_reference, reportActionRef]
            );
            if (!reportActionValue.error) {
                return reportActionValue.report;
            } else {
                console.warn("Error in report generation:", reportActionValue.error);
                return false;
            }
        } catch (error) {
            console.error("Error during RPC call:", error);
            return false;
        }
    },
    async reportActionPrint(order_reference) {
        const reportActionValue = await this.getReportActionValue(order_reference);
        if (reportActionValue) {
            try {
                printJS({
                    printable: reportActionValue,
                    type: 'pdf',
                    base64: true,
                    showModal: false
                });
            } catch (error) {
                console.error(error);
            }
        } else {
            console.warn("Error printing report, consult your administrator.");
        }
    },
});
