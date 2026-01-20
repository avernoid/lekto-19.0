/** @odoo-module */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("pos_ticket_base_tour", {
    steps: () => [
        {
            content: "Wait for the POS to load",
            trigger: ".pos",
        },
        {
            content: "Verify that the custom config fields are loaded",
            trigger: ".pos",
            run: () => {
                const pos = window.posmodel;
                if (!pos || !pos.config) {
                    throw new Error("PosStore (posmodel) not found in window");
                }
                if (pos.config.automatic_print_electronic_invoice === undefined) {
                    throw new Error("automatic_print_electronic_invoice is not defined in pos.config");
                }
                if (pos.config.automatic_download_electronic_invoice === undefined) {
                    throw new Error("automatic_download_electronic_invoice is not defined in pos.config");
                }
            },
        },
        {
            content: "Complete tour",
            trigger: "body",
        }
    ],
});
