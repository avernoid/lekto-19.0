import logging

_logger = logging.getLogger(__name__)

AGENT_LOGIN = 'agent@ganemo.co'
AGENT_PASSWORD = 'GanemoDevBot2025!'


def migrate(cr, version):
    """
    Migration 19.0.1.0.1 -> 19.0.1.0.2
    Fixes bot user group assignment using ORM (which expands implied groups).
    Root cause: ir.logging requires base.group_erp_manager. Raw SQL INSERT
    into res_groups_users_rel does not expand implied groups, so the user
    had group_system in the DB but not the effective group_erp_manager.
    """
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})

    agent_user = env['res.users'].search([('login', '=', AGENT_LOGIN)], limit=1)
    if not agent_user:
        _logger.warning('Ganemo DevOps migrate 1.0.2: Bot user %s not found', AGENT_LOGIN)
        return

    group_user    = env.ref('base.group_user')
    group_erp_mgr = env.ref('base.group_erp_manager')
    group_system  = env.ref('base.group_system')
    target_groups = group_user | group_erp_mgr | group_system

    missing = target_groups - agent_user.group_ids
    if missing:
        # Use write() so ORM triggers implied group expansion
        agent_user.write({'group_ids': [(4, g.id) for g in missing]})
        _logger.info(
            'Ganemo DevOps migrate 1.0.2: Granted %s to bot user %s',
            missing.mapped('name'), AGENT_LOGIN
        )
    else:
        _logger.info('Ganemo DevOps migrate 1.0.2: Bot user already has all required groups')

    # Reset password in case it changed
    agent_user.write({'password': AGENT_PASSWORD})
    _logger.info('Ganemo DevOps migrate 1.0.2: Migration complete')
