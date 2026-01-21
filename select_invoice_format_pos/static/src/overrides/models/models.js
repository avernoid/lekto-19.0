/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    /**
     * @override
     */
    getReportActionRef() {
        if (this.config.invoice_report_id) {
            return this.config.invoice_report_id.id;
        }
        return super.getReportActionRef();
    },
});
