/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

/**
 * Patch ListController to integrate button visibility rules.
 * 
 * This patch overrides:
 * - activeActions (using safe getter descriptor pattern)
 * - getStaticActionMenuItems() to filter out hidden buttons (export, archive, duplicate)
 * 
 * This approach is safer than mutating archInfo and more resilient to Odoo core changes.
 */
patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);

        // Access the button control service
        this.buttonControl = useService("button_control");

        // Apply rules to activeActions instance property
        this.applyButtonRules();
    },

    /**
     * Apply visibility rules to instance properties that shadow the prototype.
     */
    applyButtonRules() {
        if (!this.buttonControl || !this.buttonControl.isLoaded) {
            return;
        }

        const resModel = this.props.resModel || this.model?.root?.resModel;
        const context = this.props.context || {};
        const props = this.props;

        if (this.activeActions && this.activeActions.create) {
            const shouldHide = this.buttonControl.shouldHideButton(
                'create', 'list', resModel, context, props
            );
            if (shouldHide) {
                console.warn(`[Button Control] Hiding "New" button in List instance for ${resModel}`);
                this.activeActions = {
                    ...this.activeActions,
                    create: false
                };
            }
        }
    },

    /**
     * Override getStaticActionMenuItems to filter out buttons based on rules.
     * 
     * @returns {Object} - Static action menu items (export, archive, duplicate, delete)
     */
    getStaticActionMenuItems() {
        // Get native items first
        const nativeItems = super.getStaticActionMenuItems(...arguments);

        const resModel = this.props.resModel || this.model?.root?.resModel;
        const context = this.props.context || {};
        const props = this.props;

        // Filter each item based on rules
        const filteredItems = {};

        for (const [key, item] of Object.entries(nativeItems)) {
            let shouldHide = false;

            // Map action keys to button names
            switch (key) {
                case 'export':
                    shouldHide = this.buttonControl.shouldHideButton(
                        'export', 'list', resModel, context, props
                    );
                    break;
                case 'archive':
                case 'unarchive':
                    shouldHide = this.buttonControl.shouldHideButton(
                        'archive', 'list', resModel, context, props
                    );
                    break;
                case 'duplicate':
                    shouldHide = this.buttonControl.shouldHideButton(
                        'duplicate', 'list', resModel, context, props
                    );
                    break;
                case 'delete':
                    shouldHide = this.buttonControl.shouldHideButton(
                        'delete', 'list', resModel, context, props
                    );
                    break;
                default:
                    shouldHide = false;
            }

            // Only include item if it shouldn't be hidden
            if (!shouldHide) {
                filteredItems[key] = item;
            }
        }

        return filteredItems;
    },
});

/**
 * Safe way to override the activeActions getter.
 * 
 * IMPORTANT: We include a dummy setter for OWL reactivity compatibility.
 */
const originalDescriptor = Object.getOwnPropertyDescriptor(
    ListController.prototype,
    'activeActions'
);

if (originalDescriptor && originalDescriptor.get) {
    const originalGetter = originalDescriptor.get;

    Object.defineProperty(ListController.prototype, 'activeActions', {
        get() {
            // Call the original getter to get native behavior
            const nativeActiveActions = originalGetter.call(this);

            // Check if buttonControl service is available and loaded
            if (!this.buttonControl || !this.buttonControl.isLoaded) {
                return nativeActiveActions;
            }

            // Check if create button should be hidden
            const resModel = this.props.resModel || this.model?.root?.resModel;
            const context = this.props.context || {};
            const props = this.props;

            const shouldHide = this.buttonControl.shouldHideButton(
                'create',
                'list',
                resModel,
                context,
                props
            );

            if (shouldHide) {
                console.warn(`[Button Control] Hiding "New" button in List for ${resModel}`);
                // Return modified activeActions with create disabled
                return {
                    ...nativeActiveActions,
                    create: false
                };
            }

            // No rule applies, return native
            return nativeActiveActions;
        },
        set() {
            // Dummy setter for OWL reactivity compatibility
        },
        configurable: true,
        enumerable: true
    });
}
