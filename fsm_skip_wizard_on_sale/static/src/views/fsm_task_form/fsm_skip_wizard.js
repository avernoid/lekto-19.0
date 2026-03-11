/** @odoo-module **/

import { FsmProjectTaskFormController } from "@industry_fsm/views/fsm_task_form/fsm_task_form_view";
import { patch } from "@web/core/utils/patch";

/**
 * Patch the FSM Task Form Controller to handle the Stop button bypass.
 *
 * When the server returns `false` from `action_timer_stop` (because
 * skip_wizard_on_sale is active and a confirmed sale exists), the Odoo
 * action service silently does nothing — the wizard never opens.
 * We need to reload the record so the timer state is reflected immediately.
 */
patch(FsmProjectTaskFormController.prototype, {
    /**
     * @override
     * After the Stop button executes, if no action was returned (bypass path),
     * reload the record to reflect the stopped timer and updated timesheet.
     */
    async executeActionButton(clickParams) {
        if (clickParams.name === "action_timer_stop") {
            const result = await super.executeActionButton(...arguments);
            // Whether bypassed (result is falsy) or wizard opened and closed,
            // reload to show updated timer state.
            await this.model.root.load();
            this.render();
            return result;
        }
        return super.executeActionButton(...arguments);
    },
});
