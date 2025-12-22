/** @odoo-module **/

import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { user } from "@web/core/user";

/**
 * Button Control Service
 * 
 * This service manages button visibility rules for the current user.
 * It loads rules from the backend and provides methods to check if buttons
 * should be hidden based on context, model, and view type.
 * 
 * The service ensures that users without rules experience 100% native Odoo behavior.
 */
class ButtonControlService {
    constructor(env, services) {
        this.env = env;
        this.orm = services.orm;
        this.notification = services.notification;

        // Cache for user rules, loaded on service start
        this.rules = {
            kanban: [],
            list: [],
            form: []
        };

        this.isLoaded = false;
    }

    /**
     * Load button rules for the current user from the backend.
     * Called automatically when the service starts.
     */
    async start() {
        console.info('[Button Control] Service starting...');
        try {
            // In Odoo 19, user info is in the user module. 
            // session.user_id might be deleted by the user module for single source of truth.
            const userId = user.userId;
            console.info('[Button Control] Loading rules for user ID:', userId);

            if (!userId) {
                console.warn('[Button Control] No user ID found, skipping rule load');
                this.isLoaded = true;
                return;
            }

            this.rules = await this.orm.call(
                'ui.button.rule',
                'get_user_rules',
                [userId]
            );
            console.info('[Button Control] Rules loaded successfully:', this.rules);
            this.isLoaded = true;

            // Optional: Notify user that rules are active (only if rules exist)
            const hasRules = this.rules.kanban.length > 0 ||
                this.rules.list.length > 0 ||
                this.rules.form.length > 0;

            if (hasRules) {
                this.notification.add('Button Visibility Rules active for your user.', {
                    type: 'info',
                    sticky: false,
                });
            }
        } catch (error) {
            console.error('[Button Control] Failed to load rules:', error);
            this.rules = { kanban: [], list: [], form: [] };
            this.isLoaded = true;
        }
    }

    /**
     * Check if a button should be hidden based on rules.
     * 
     * @param {string} buttonName - Name of the button (create, edit, archive, etc.)
     * @param {string} viewType - Type of view (kanban, list, form)
     * @param {string} resModel - Model name (e.g., 'project.task')
     * @param {Object} context - Odoo context object
     * @param {Object} props - Component props (for accessing readonly state)
     * @returns {boolean} - true if button should be hidden, false otherwise
     */
    shouldHideButton(buttonName, viewType, resModel, context = {}, props = {}) {
        // If service not loaded yet or no rules exist for this view type, don't hide
        if (!this.isLoaded || !this.rules[viewType]) {
            return false;
        }

        const viewRules = this.rules[viewType];
        if (!viewRules || viewRules.length === 0) {
            return false;
        }

        // Find matching rule
        for (const rule of viewRules) {
            // Check if button name matches (exact or fuzzy for cancel/validate)
            if (!this._isButtonMatch(rule.button_name, buttonName, props)) {
                continue;
            }

            // Check if model matches (empty res_model means "applies to all")
            // Handle both False (from Python) and "" or null
            const ruleModel = rule.res_model;
            if (ruleModel && ruleModel !== resModel) {
                continue;
            }

            // Check if context matches
            if (!this._evaluateContext(rule.context_key, context, props)) {
                continue;
            }

            console.info(`[Button Control] Hiding button "${buttonName}" in "${viewType}" for model "${resModel}"`);
            // Rule matches! Button should be hidden
            return true;
        }

        // No matching rule found, button should be visible (native behavior)
        return false;
    }

    /**
     * Check if a rule button name matches the current button ID/string.
     * 
     * @private
     */
    _isButtonMatch(ruleButtonName, currentButtonName, props) {
        // Standard exact match
        if (ruleButtonName === currentButtonName) {
            return true;
        }

        const buttonString = (props.string || "").toLowerCase();
        const techName = (currentButtonName || "").toLowerCase();
        const clickParams = props.clickParams || {};

        // Special handling for Cancel
        if (ruleButtonName === 'cancel') {
            return techName.includes('cancel') ||
                clickParams.special === 'cancel' ||
                techName.includes('reject') ||
                techName.includes('rollback') ||
                buttonString.includes('cancel') ||
                buttonString.includes('anular') ||
                buttonString.includes('rechazar') ||
                buttonString.includes('rejet');
        }

        // Special handling for Validate
        if (ruleButtonName === 'validate') {
            return techName.includes('validate') ||
                techName === 'action_confirm' ||
                techName.includes('confirm') ||
                techName === 'button_validate' ||
                techName === 'action_validate' ||
                techName.includes('validate') ||
                techName.includes('done') ||
                techName.includes('approve') ||
                techName.includes('post') ||
                techName.includes('payment') ||
                buttonString.includes('validate') ||
                buttonString.includes('validar') ||
                buttonString.includes('confirm') ||
                buttonString.includes('approuv') ||
                buttonString.includes('aprobar') ||
                buttonString.includes('hecho') ||
                buttonString.includes('finalizar') ||
                buttonString.includes('terminar') ||
                buttonString.includes('publicar') ||
                buttonString.includes('postear');
        }

        return false;
    }

    /**
     * Evaluate if the current context matches the rule's context requirement.
     * 
     * Context mapping (internal, not exposed to admins):
     * - 'any': Always true
     * - 'fsm': Checks if context has fsm_mode
     * - 'from_sale': Checks if context has default_sale_order_id
     * - 'readonly': Checks if view is in readonly mode
     * 
     * @param {string} contextKey - Context key from rule
     * @param {Object} context - Odoo context
     * @param {Object} props - Component props
     * @returns {boolean} - true if context matches
     * @private
     */
    _evaluateContext(contextKey, context, props) {
        switch (contextKey) {
            case 'any':
                return true;

            case 'fsm':
                // FSM context is typically indicated by fsm_mode in context
                return !!(context && context.fsm_mode);

            case 'from_sale':
                // From sale context is indicated by default_sale_order_id
                return !!(context && context.default_sale_order_id);

            case 'readonly':
                // Check if view is in readonly mode
                // This can be from props.isReadonly or model state
                return !!(props && props.isReadonly);

            default:
                // Unknown context key, don't match
                return false;
        }
    }

    /**
     * Get all rules for debugging purposes.
     * Accessible via window.odoo.__DEBUG__.services['button_control'].getRules()
     * 
     * @returns {Object} - Current rules
     */
    getRules() {
        return this.rules;
    }
}

export const buttonControlService = {
    dependencies: ["orm", "notification"],
    async start(env, services) {
        const service = new ButtonControlService(env, services);
        await service.start();
        return service;
    },
};

registry.category("services").add("button_control", buttonControlService);
