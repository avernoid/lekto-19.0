from . import controllers
from . import models
from . import report
from . import wizards


def post_init_hook(env):
    """Set default system parameters on first install only.

    post_init_hook is called exclusively on INSTALL (never on upgrade),
    so existing admin customizations are never overwritten.
    Using get_param as guard avoids UniqueViolation even when the key
    already exists in ir.config_parameter without an ir.model.data entry.
    """
    params = env['ir.config_parameter'].sudo()
    if not params.get_param('github.max_try'):
        params.set_param('github.max_try', '5')
    if not params.get_param('git.partial_commit_during_analysis'):
        params.set_param('git.partial_commit_during_analysis', 'True')
