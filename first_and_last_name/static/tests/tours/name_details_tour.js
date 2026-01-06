/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add('name_details_tour', {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: 'Open Contacts app.',
            trigger: '.o_app[data-menu-xmlid="contacts.menu_contacts"]',
            run: "click",
        },
        {
            content: 'Click on Create.',
            trigger: '.o_list_button_add',
            run: "click",
        },
        {
            content: 'Check "Individual" is selected (default).',
            trigger: 'input#radio_field_0_person',
        },
        {
            content: 'Verify "Detalle del Nombre" label is visible.',
            trigger: 'label:contains("Detalle del Nombre")',
        },
        {
            content: 'Verify Nombres field is visible.',
            trigger: 'input[name="partner_name"]',
        },
        {
            content: 'Select "Company".',
            trigger: 'input#radio_field_0_company',
            run: "click",
        },
        {
            content: 'Verify "Detalle del Nombre" label is hidden.',
            trigger: 'body:not(:has(label:contains("Detalle del Nombre")))',
        },
        {
            content: 'Verify Nombres field is hidden.',
            trigger: 'body:not(:has(input[name="partner_name"]))',
        }
    ]
});
