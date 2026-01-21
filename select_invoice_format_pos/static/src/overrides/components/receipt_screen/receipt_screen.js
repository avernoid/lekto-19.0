/** @odoo-module */

import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { useAsyncLockedMethod } from "@point_of_sale/app/hooks/hooks";
import { patch } from "@web/core/utils/patch";
import { useRef } from "@odoo/owl";

patch(ReceiptScreen.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup(...arguments);
        this.buttonPrintElectronicReceipt = useRef("order-print-electronic-receipt-button");
        this.printElectronicReceipt = useAsyncLockedMethod(this.printElectronicReceipt);
    },
    async printElectronicReceipt() {
        this.buttonPrintElectronicReceipt.el.className = "fa fa-fw fa-spin fa-circle-o-notch";
        await this.pos.reportActionPrint(this.currentOrder.pos_reference);
        if (this.buttonPrintElectronicReceipt.el) {
            this.buttonPrintElectronicReceipt.el.className = "fa fa-print";
        }
    },
});
