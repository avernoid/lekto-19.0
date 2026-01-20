/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";

patch(OrderPaymentValidation.prototype, {
    shouldDownloadInvoice() {
        return this.pos.config.automatic_download_electronic_invoice && super.shouldDownloadInvoice();
    },
    async finalizeValidation() {
        const result = await super.finalizeValidation(...arguments);
        if (this.pos.config.automatic_print_electronic_invoice && this.order.isToInvoice()) {
            if (this.order.raw.account_move) {
                await this.pos.reportActionPrint(this.order.pos_reference, this.pos.getReportActionRef());
            }
        }
        return result;
    }
});
