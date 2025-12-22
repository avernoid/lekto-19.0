/** @odoo-module **/

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

/**
 * Patch KanbanController to integrate button visibility rules.
 * 
 * This patch overrides the canCreate getter using safe property descriptor pattern.
 */
patch(KanbanController.prototype, {
    setup() {
        super.setup(...arguments);

        // Access the button control service
        this.buttonControl = useService("button_control");
    },
});

/**
 * Safe override for canCreate getter using Object.defineProperty
 * 
 * IMPORTANT: We include a dummy setter to ensure compatibility with OWL's
 * reactivity system when controller subclasses exist (like SaleFileUploadKanbanController).
 * Without the setter, OWL's capture() function throws "Cannot set property which has only a getter"
 */
const canCreateDescriptor = Object.getOwnPropertyDescriptor(
    KanbanController.prototype,
    'canCreate'
);

if (canCreateDescriptor && canCreateDescriptor.get) {
    const originalCanCreateGetter = canCreateDescriptor.get;

    Object.defineProperty(KanbanController.prototype, 'canCreate', {
        get() {
            // Get native value first
            const nativeCanCreate = originalCanCreateGetter.call(this);

            // Check if buttonControl service is available and loaded
            if (!this.buttonControl || !this.buttonControl.isLoaded) {
                return nativeCanCreate;
            }

            // Check if button should be hidden by rules
            const resModel = this.props.resModel || this.model?.root?.resModel;
            const context = this.props.context || {};
            const props = this.props;

            const shouldHide = this.buttonControl.shouldHideButton(
                'create',
                'kanban',
                resModel,
                context,
                props
            );

            if (shouldHide) {
                console.warn(`[Button Control] Hiding "New" button in Kanban for ${resModel}`);
                return false;
            }

            // No rule applies, use native behavior
            return nativeCanCreate;
        },
        set() {
            // Dummy setter required for OWL reactivity system compatibility
            // This prevents "Cannot set property which has only a getter" errors
            // when OWL's capture() tries to track this property
        },
        configurable: true,
        enumerable: true
    });
}
