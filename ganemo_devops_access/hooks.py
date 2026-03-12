import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Bot user credentials
# These values are INTENTIONALLY hardcoded — this module is a DevOps tool
# for staging/testing environments only. NEVER install on production.
# The agent reads these same values from odoo_deploy.secrets.yml.
# ─────────────────────────────────────────────────────────────────────────────
AGENT_LOGIN = 'agent@ganemo.co'
AGENT_PASSWORD = 'GanemoDevBot2025!'
AGENT_NAME = 'Ganemo Agent'
AGENT_KEY_NAME = 'Ganemo Agent Key'
CONFIG_KEY = 'devops.agent_key'
CONFIG_LOGIN = 'devops.agent_login'


def post_init_hook(env):
    """
    Called once after the module is installed.
    Creates (or resets) the Ganemo bot user and generates a fresh API key.
    Stores the key in ir.config_parameter so the Antigravity agent can retrieve it
    via classic JSON-RPC and then use JSON-2 for all subsequent calls.
    """
    _logger.info('Ganemo DevOps: Running post_init_hook...')

    # ── 1. Create or update the bot user ─────────────────────────────────────
    User = env['res.users'].with_context(no_reset_password=True)
    agent_user = User.search([('login', '=', AGENT_LOGIN)], limit=1)

    # Required groups:
    # - base.group_user       → base internal user (required foundation)
    # - base.group_erp_manager → grants ir.logging read access (from native ir.model.access.csv)
    # - base.group_system     → admin/technical full access
    # Using ORM write() so Odoo expands implied groups in res_groups_users_rel automatically.
    group_user    = env.ref('base.group_user')
    group_erp_mgr = env.ref('base.group_erp_manager')
    group_system  = env.ref('base.group_system')
    target_groups = group_user | group_erp_mgr | group_system

    if not agent_user:
        agent_user = User.create({
            'name': AGENT_NAME,
            'login': AGENT_LOGIN,
            'email': AGENT_LOGIN,
            # Assign all three groups explicitly — ORM handles implied group expansion
            'group_ids': [(6, 0, target_groups.ids)],
        })
        _logger.info('Ganemo DevOps: Bot user created → %s', AGENT_LOGIN)
    else:
        # Ensure all required groups are present (handles upgrades where groups were missing)
        missing = target_groups - agent_user.group_ids
        if missing:
            agent_user.write({'group_ids': [(4, g.id) for g in missing]})
            _logger.info('Ganemo DevOps: Granted groups %s to existing bot user', missing.mapped('name'))
        _logger.info('Ganemo DevOps: Bot user already exists → %s', AGENT_LOGIN)

    # Always (re)set the password in case it changed between deployments
    agent_user.write({'password': AGENT_PASSWORD})

    # ── 2. Generate a fresh API key for the bot ───────────────────────────────
    # ir.api.key requires Enterprise modules to be initialized.
    # In isolated test DBs (only `base` + this module installed), it's not in env.
    # In Odoo.SH with full Enterprise install, it IS available and the API key
    # generation path will always execute.
    Param = env['ir.config_parameter'].sudo()
    Param.set_param(CONFIG_LOGIN, AGENT_LOGIN)

    if 'ir.api.key' in env:
        # Remove any existing keys to avoid accumulation
        env['ir.api.key'].search([('user_id', '=', agent_user.id)]).unlink()

        api_key_record = env['ir.api.key'].create({
            'name': AGENT_KEY_NAME,
            'user_id': agent_user.id,
        })

        # ── 3. Store key value in ir.config_parameter ─────────────────────────
        # Odoo sets the raw key in a transient (non-stored) field on the record
        # during create() so it can be shown once in the UI. We capture it here.
        raw_key = getattr(api_key_record, 'key', None)

        if raw_key:
            Param.set_param(CONFIG_KEY, raw_key)
            _logger.info(
                'Ganemo DevOps: API key stored in ir.config_parameter[%s]. '
                'Agent can authenticate via JSON-2 Bearer token.',
                CONFIG_KEY,
            )
        else:
            _logger.warning(
                'Ganemo DevOps: ir.api.key.create() did not expose raw key. '
                'Falling back to password auth (classic JSON-RPC).'
            )
            Param.set_param('devops.agent_password', AGENT_PASSWORD)
    else:
        # Community or local dev: skip API key, use password only
        Param.set_param('devops.agent_password', AGENT_PASSWORD)
        _logger.info(
            'Ganemo DevOps: ir.api.key not available (Community/local). '
            'Password stored in ir.config_parameter[devops.agent_password]. '
            'On Odoo Enterprise/SH the API key will be generated automatically.'
        )

    _logger.info('Ganemo DevOps: post_init_hook completed successfully.')


def uninstall_hook(env):
    """
    Called when the module is uninstalled.
    Removes the bot user and all associated API keys and config parameters.
    """
    _logger.info('Ganemo DevOps: Running uninstall_hook...')

    # Remove config parameters
    Param = env['ir.config_parameter'].sudo()
    for key in [CONFIG_KEY, CONFIG_LOGIN, 'devops.agent_password']:
        param = Param.search([('key', '=', key)])
        if param:
            param.unlink()

    # Remove the bot user (also cascades API keys)
    agent_user = env['res.users'].search([('login', '=', AGENT_LOGIN)], limit=1)
    if agent_user:
        agent_user.unlink()
        _logger.info('Ganemo DevOps: Bot user removed → %s', AGENT_LOGIN)

    _logger.info('Ganemo DevOps: uninstall_hook completed.')
