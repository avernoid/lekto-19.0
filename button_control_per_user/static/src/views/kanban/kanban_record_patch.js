/** @odoo-module **/

import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

/**
 * Patch KanbanRecord to integrate button visibility rules for per-card actions.
 */
patch(KanbanRecord.prototype, {
    setup() {
        super.setup(...arguments);

        // Access the button control service
        this.buttonControl = useService("button_control");
    },

    /**
     * Override createWidget to apply visibility rules to deletable and editable flags.
     * These flags control the visibility of options in the card dropdown menu.
     * 
     * @override
     */
    createWidget(props) {
        super.createWidget(props);

        // Check if buttonControl service is available and loaded
        if (!this.buttonControl || !this.buttonControl.isLoaded) {
            return;
        }

        const { list } = props;
        const resModel = list.resModel;
        const context = list.context || {};

        // Check Delete rule
        if (this.dataState.widget.deletable) {
            const shouldHideDelete = this.buttonControl.shouldHideButton(
                'delete', 'kanban', resModel, context, props
            );
            if (shouldHideDelete) {
                this.dataState.widget.deletable = false;
            }
        }

        // Check Edit rule
        if (this.dataState.widget.editable) {
            const shouldHideEdit = this.buttonControl.shouldHideButton(
                'edit', 'kanban', resModel, context, props
            );
            if (shouldHideEdit) {
                this.dataState.widget.editable = false;
            }
        }
    }
});
