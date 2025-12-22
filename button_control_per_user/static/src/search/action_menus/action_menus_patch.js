/** @odoo-module **/

import { ActionMenus } from "@web/search/action_menus/action_menus";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

/**
 * Patch ActionMenus to filter items (Actions and Print dropdowns)
 * based on button visibility rules.
 */
patch(ActionMenus.prototype, {
    setup() {
        super.setup(...arguments);
        this.buttonControl = useService("button_control");
    },

    /**
     * Filter action items before they are returned to the state.
     */
    async getActionItems(props) {
        const items = await super.getActionItems(props);

        if (!this.buttonControl || !this.buttonControl.isLoaded) {
            return items;
        }

        const resModel = props?.resModel;
        const context = props?.context || {};
        const viewType = this.env.viewType || 'list';

        return items.filter(item => {
            // Treat the description/name as the button name for fuzzy matching
            // We use item.description (label) and technical action ID if present
            const techName = item.action?.name || item.description || "";
            const buttonId = item.action?.id?.toString() || "";

            const shouldHide = this.buttonControl.shouldHideButton(
                buttonId || techName,
                viewType,
                resModel,
                context,
                { string: item.description, clickParams: { name: techName } }
            );

            if (shouldHide) {
                console.debug(`[Button Control] Hiding action "${item.description}" for model "${resModel}" in ActionMenus`);
            }
            return !shouldHide;
        });
    }
});
