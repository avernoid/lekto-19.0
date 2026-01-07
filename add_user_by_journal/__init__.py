from . import models


def _uninstall_module_complete(env):
    act_dashboard = env.ref('account.open_account_journal_dashboard_kanban', raise_if_not_found=False)
    if act_dashboard:
        act_dashboard.domain = '[]'
    act_journals = env.ref('account.action_account_journal_form', raise_if_not_found=False)
    if act_journals:
        act_journals.domain = '[]'
