/** @odoo-module **/

import { FsmProjectTaskFormController } from "@industry_fsm/views/fsm_task_form/fsm_task_form_view";
import { patch } from "@web/core/utils/patch";

patch(FsmProjectTaskFormController.prototype, {
    /**
     * @override
     * Extend to add server-side distance validation before starting timer
     */
    async beforeExecuteActionButton(clickParams) {
        // Call parent to get geolocation
        const result = await super.beforeExecuteActionButton(...arguments);
        
        // If this is the start timer action and geolocation is enabled
        if (clickParams.name === "action_timer_start" && this.model.root.data.allow_geolocation) {
            const projectId = this.model.root.data.project_id && this.model.root.data.project_id[0];
            
            if (projectId) {
                // Check if distance control is enabled on the project
                const projectData = await this.orm.read(
                    "project.project",
                    [projectId],
                    ["control_distance_on_start"]
                );
                
                if (projectData && projectData[0] && projectData[0].control_distance_on_start) {
                    // Distance validation will be done on server side in action_timer_start
                    // The geolocation is already in the context from parent call
                    // If validation fails, server will raise UserError
                    // No additional client-side validation needed
                }
            }
        }
        
        return result;
    },
});
