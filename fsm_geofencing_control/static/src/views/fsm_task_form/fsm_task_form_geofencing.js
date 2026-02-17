/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";

patch(FormController.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
    },

    /**
     * @override
     * Extend to add server-side distance validation before starting timer
     */
    async beforeExecuteActionButton(clickParams) {

        // CATCH-ALL LOG to ensure patch is working
        // console.log("Geofencing Patch: beforeExecuteActionButton called for", clickParams.name);

        // Check if we are starting the timer
        // We use 'action_timer_start' which is the standard button name
        if (clickParams.name === "action_timer_start") {

            // Validate availability of model data
            if (this.model && this.model.root && this.model.root.resModel === "project.task") {

                // console.log("Geofencing: Valid context (project.task + action_timer_start)");

                // Get project_id from data
                const projectIdData = this.model.root.data.project_id;
                const projectId = Array.isArray(projectIdData) ? projectIdData[0] : projectIdData;

                let allowGeolocation = false;

                if (projectId) {
                    try {
                        // console.log("Geofencing: Fetching config for project", projectId);
                        // Fetch allow_geolocation from project.project
                        const projectData = await this.orm.read(
                            "project.project",
                            [projectId],
                            ["allow_geolocation"]
                        );

                        if (projectData && projectData[0] && projectData[0].allow_geolocation) {
                            allowGeolocation = true;
                        }
                    } catch (error) {
                        console.warn("Geofencing: Failed to fetch project configuration", error);
                    }
                }

                // console.log("Geofencing: allowGeolocation result:", allowGeolocation);

                if (allowGeolocation) {
                    try {
                        const position = await new Promise((resolve, reject) => {
                            browser.navigator.geolocation.getCurrentPosition(resolve, reject, {
                                enableHighAccuracy: true,
                                timeout: 5000,
                                maximumAge: 0
                            });
                        });

                        const geolocation = {
                            latitude: position.coords.latitude,
                            longitude: position.coords.longitude,
                            success: true
                        };

                        // Inject into clickParams.context
                        if (!clickParams.context) {
                            clickParams.context = {};
                        }

                        // Create a NEW context object to ensure it's passed
                        clickParams.context = {
                            ...clickParams.context,
                            geolocation: geolocation
                        };

                        // console.log("Geofencing: Location injected", geolocation);

                    } catch (error) {
                        console.warn("Geofencing: Failed to retrieve position for Start Timer", error);
                    }
                }
            }
        }

        return super.beforeExecuteActionButton(...arguments);
    },
});
