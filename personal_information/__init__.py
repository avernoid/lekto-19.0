from . import models


def post_init_hook(env):
    """Set generate_legal_name=True for all existing companies on first install.
    This hook only runs on installation, never on upgrade, so user-configured
    values are always preserved after the initial setup.
    """
    env['res.company'].search([]).write({'generate_legal_name': True})
