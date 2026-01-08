/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { AccountReportLineName } from "@account_reports/components/account_report/line_name/line_name";

patch(AccountReportLineName.prototype, {

    async openWizardFinancial() {
        var date_from = false;
        var date_to = false;
        if (this.controller.options.date) {
            date_from = this.controller.options.date.date_from;
            date_to = this.controller.options.date.date_to;
        }
        const accountId = this.props.line['account_id'];
        this.action.doAction(
            "financial_statement_annexes.action_wizard_report_financial", {
            additionalContext: {
                'default_account_ids': [accountId],
                'default_date_start': date_from,
                'default_date_end': date_to
            }
        }
        );
    },

    get AnnexesAndNotes() {
        const reconcile = this.props.line['reconcile'];
        const accountId = this.props.line['account_id'];
        const isAccountAccount = this.props.line.caret_options == 'account.account';
        return isAccountAccount && reconcile && accountId;
    }
});
