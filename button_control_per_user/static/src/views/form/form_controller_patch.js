/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

/**
 * Patch FormController to integrate button visibility rules.
 * 
 * This patch overrides:
 * - canCreate and canEdit getters (using safe property descriptor pattern)
 * - getStaticActionMenuItems() to filter archive/duplicate/export
 */
patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);

        // Access the button control service
        this.buttonControl = useService("button_control");

        // Wait for service to be loaded before applying rules to instance properties
        // However, setup is synchronous. We rely on the service being initialized 
        // earlier in the app lifecycle.
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

        // Apply to canCreate
        if (this.canCreate) {
            const shouldHideCreate = this.buttonControl.shouldHideButton(
                'create', 'form', resModel, context, props
            );
            if (shouldHideCreate) {
                console.warn(`[Button Control] Hiding "New" button in Form instance for ${resModel}`);
                this.canCreate = false;
            }
        }

        // Apply to canEdit
        if (this.canEdit) {
            const propsWithReadonly = {
                ...props,
                isReadonly: this.model?.root?.isReadonly || false
            };
            const shouldHideEdit = this.buttonControl.shouldHideButton(
                'edit', 'form', resModel, context, propsWithReadonly
            );
            if (shouldHideEdit) {
                console.warn(`[Button Control] Hiding "Edit" button in Form instance for ${resModel}`);
                this.canEdit = false;
            }
        }
    },

    /**
     * Override getStaticActionMenuItems to filter buttons based on rules.
     * This affects Archive, Duplicate, and Export buttons in the cogmenu.
     * 
     * @returns {Object} - Static action menu items
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
                        'export', 'form', resModel, context, props
                    );
                    break;
                case 'archive':
                case 'unarchive':
                    shouldHide = this.buttonControl.shouldHideButton(
                        'archive', 'form', resModel, context, props
                    );
                    break;
                case 'duplicate':
                    shouldHide = this.buttonControl.shouldHideButton(
                        'duplicate', 'form', resModel, context, props
                    );
                    break;
                case 'delete':
                    shouldHide = this.buttonControl.shouldHideButton(
                        'delete', 'form', resModel, context, props
                    );
                    break;
                // Other buttons keep native behavior
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
 * Safe override for canCreate getter using Object.defineProperty
 * IMPORTANT: Includes dummy setter for OWL reactivity compatibility
 */
const canCreateDescriptor = Object.getOwnPropertyDescriptor(
    FormController.prototype,
    'canCreate'
);

if (canCreateDescriptor && canCreateDescriptor.get) {
    const originalCanCreateGetter = canCreateDescriptor.get;

    Object.defineProperty(FormController.prototype, 'canCreate', {
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
                'form',
                resModel,
                context,
                props
            );

            if (shouldHide) {
                console.warn(`[Button Control] Hiding "New" button in Form for ${resModel}`);
                return false;
            }

            // No rule applies, use native behavior
            return nativeCanCreate;
        },
        set() {
            // Dummy setter for OWL reactivity compatibility
        },
        configurable: true,
        enumerable: true
    });
}

/**
 * Safe override for canEdit getter using Object.defineProperty
 * IMPORTANT: Includes dummy setter for OWL reactivity compatibility
 */
const canEditDescriptor = Object.getOwnPropertyDescriptor(
    FormController.prototype,
    'canEdit'
);

if (canEditDescriptor && canEditDescriptor.get) {
    const originalCanEditGetter = canEditDescriptor.get;

    Object.defineProperty(FormController.prototype, 'canEdit', {
        get() {
            // Get native value first
            const nativeCanEdit = originalCanEditGetter.call(this);

            // Check if buttonControl service is available and loaded
            if (!this.buttonControl || !this.buttonControl.isLoaded) {
                return nativeCanEdit;
            }

            // Check if button should be hidden by rules
            const resModel = this.props.resModel || this.model?.root?.resModel;
            const context = this.props.context || {};

            // For readonly check, we need to check the model's readonly state
            const props = {
                ...this.props,
                isReadonly: this.model?.root?.isReadonly || false
            };

            const shouldHide = this.buttonControl.shouldHideButton(
                'edit',
                'form',
                resModel,
                context,
                props
            );

            if (shouldHide) {
                console.warn(`[Button Control] Hiding "Edit" button in Form for ${resModel}`);
                return false;
            }

            // No rule applies, use native behavior
            return nativeCanEdit;
        },
        set() {
            // Dummy setter for OWL reactivity compatibility
        },
        configurable: true,
        enumerable: true
    });
}
