/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add('fsm_quick_products_tour', {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: 'Open FSM app.',
            trigger: '.o_app[data-menu-xmlid="industry_fsm.fsm_menu_root"]',
            run: "click",
        },
        {
            content: 'Open All Tasks.',
            trigger: 'button[data-menu-xmlid="industry_fsm.fsm_menu_all_tasks_root"]',
            run: "click",
        },
        {
            content: 'Open All Tasks filter.',
            trigger: 'a[data-menu-xmlid="industry_fsm.fsm_menu_all_tasks_todo"]',
            run: "click",
        },
        {
            content: 'Open the first task form.',
            trigger: '.o_list_renderer .o_data_row .o_data_cell[name="name"]',
            run: "click",
        },
        {
            content: 'Check if the products quick button exists.',
            trigger: '.o_fsm_quick_products_container button[name="action_fsm_view_material"]',
        },
        {
            content: 'Check if the sales order quick button exists.',
            trigger: '.o_fsm_quick_products_container button[name="action_view_so"]',
        },
        {
            content: 'Click on the sales order quick button.',
            trigger: '.o_fsm_quick_products_container button[name="action_view_so"]',
            run: "click",
        },
        {
            content: 'Wait for the Sale Order form to load.',
            trigger: '.o_form_view_container .o_form_status_indicator:contains(Sales Order), .o_breadcrumb:contains(S00)',
            run: () => { }, // Just a check
        }
    ]
});
