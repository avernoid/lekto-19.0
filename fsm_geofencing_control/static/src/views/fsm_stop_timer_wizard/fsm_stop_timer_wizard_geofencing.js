/** @odoo-module **/

import { FsmStopTimerWizardFormController } from "@industry_fsm/views/fsm_stop_timer_wizard/fsm_stop_timer_wizard_view";
import { patch } from "@web/core/utils/patch";

patch(FsmStopTimerWizardFormController.prototype, {
    /**
     * @override
     * Extend to add server-side distance validation before saving timesheet
     */
    async beforeExecuteActionButton(clickParams) {
        // Call parent to get geolocation
        const result = await super.beforeExecuteActionButton(...arguments);

        // If this is the save timesheet action and geolocation is enabled
        if (clickParams.name === "action_save_timesheet" && this.model.root.data.allow_geolocation) {
            // Distance validation and lost reason validation will be done on server side
            // in action_save_timesheet method of the wizard
            // The geolocation is already in the context from parent call
            // If validation fails, server will raise UserError or ValidationError
            // No additional client-side validation needed
        }

        return result;
    },
});
