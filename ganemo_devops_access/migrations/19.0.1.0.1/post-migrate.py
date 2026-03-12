import logging

_logger = logging.getLogger(__name__)

AGENT_LOGIN = 'agent@ganemo.co'


def migrate(cr, version):
    """
    Migration 19.0.1.0.0 -> 19.0.1.0.1
    Grants base.group_system to the Ganemo Agent bot user via SQL.

    Root cause: post_init_hook used role='group_system' which only fires via
    UI onchange and does NOT work programmatically in create(). This script
    corrects the group assignment using a direct SQL INSERT.
    """
    cr.execute("""
        INSERT INTO res_groups_users_rel (uid, gid)
        SELECT u.id, imd.res_id
          FROM res_users u
          JOIN ir_model_data imd
            ON imd.module = 'base'
           AND imd.name = 'group_system'
         WHERE u.login = %s
           AND NOT EXISTS (
               SELECT 1 FROM res_groups_users_rel rel2
                WHERE rel2.uid = u.id
                  AND rel2.gid = imd.res_id
           )
    """, [AGENT_LOGIN])

    _logger.info(
        'Ganemo DevOps migrate 1.0.1: granted admin group to %s (%d row inserted)',
        AGENT_LOGIN, cr.rowcount
    )
