/** @odoo-module **/

import { ViewButton } from "@web/views/view_button/view_button";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

/**
 * Patch ViewButton to integrate button visibility rules centrally.
 * This allows hiding "Cancel", "Validate" and other named buttons across any view.
 */
patch(ViewButton.prototype, {
    setup() {
        super.setup(...arguments);

        // Access the button control service
        this.buttonControl = useService("button_control");
    },

    /**
     * Getter for shouldHide.
     * Evaluated during rendering to react to prop changes (like record loading).
     */
    get shouldHide() {
        if (!this.buttonControl || !this.buttonControl.isLoaded) {
            return false;
        }

        // Extract button info from various possible sources in props/params
        const buttonName = this.props.clickParams?.name || this.props.name || "";

        // MultiRecordViewButton (List View) uses props.list
        // ViewButton (Form View) uses props.record
        const resModel = this.props.record?.resModel || this.props.list?.resModel || this.props.resModel || "";
        const context = this.props.record?.context || this.props.list?.context || this.props.context || {};

        // Default to form, but allow detection from env or props.list
        const viewType = this.env.viewType || (this.props.list ? 'list' : 'form');

        const hide = this.buttonControl.shouldHideButton(
            buttonName,
            viewType,
            resModel,
            context,
            this.props
        );

        if (hide) {
            // Log for debugging (only in debug mode or for developers)
            console.debug(`[Button Control] Hiding button "${buttonName}" for model "${resModel}"`);
        }
        return hide;
    }
});
