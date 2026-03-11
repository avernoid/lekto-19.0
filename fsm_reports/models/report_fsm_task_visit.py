from odoo import api, fields, models, tools


class ReportFsmTaskVisit(models.Model):
    """
    SQL View: One row per (task, assigned_user).
    This one-to-many expansion (via project_task_user_rel) is intentional:
    it allows Odoo Record Rules to filter rows by `user_id = uid` transparently.
    FSM managers see all rows; FSM users see only rows where user_id = their uid.
    """
    _name = 'report.fsm.task.visit'
    _description = 'FSM Task Visit Report'
    _auto = False
    _rec_name = 'task_id'
    _order = 'planned_date_begin desc, user_id'

    # -------------------------------------------------------------------------
    # Identifiers
    # -------------------------------------------------------------------------
    task_id = fields.Many2one(
        'project.task',
        string='Tarea',
        readonly=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string='Vendedor',
        readonly=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        readonly=True,
    )
    project_id = fields.Many2one(
        'project.project',
        string='Proyecto',
        readonly=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        readonly=True,
    )
    lost_reason_id = fields.Many2one(
        'sale.lost.reason',
        string='Motivo de No Venta',
        readonly=True,
    )

    # -------------------------------------------------------------------------
    # Date grouping columns (pre-truncated for fast GROUP BY)
    # -------------------------------------------------------------------------
    planned_date_begin = fields.Datetime(
        string='Fecha/Hora Planificada',
        readonly=True,
    )
    planned_date = fields.Date(
        string='Fecha de Visita',
        readonly=True,
    )
    planned_week = fields.Date(
        string='Semana Planificada',
        readonly=True,
    )
    planned_month = fields.Date(
        string='Mes Planificado',
        readonly=True,
    )

    # -------------------------------------------------------------------------
    # Visit status
    # -------------------------------------------------------------------------
    state = fields.Selection(
        selection=[
            ('01_in_progress', 'En Progreso'),
            ('1_done', 'Finalizada'),
            ('1_canceled', 'Cancelada'),
        ],
        string='Estado',
        readonly=True,
    )
    not_executed = fields.Integer(
        string='Not Executed',
        aggregator='sum',
        readonly=True,
        help="1 if the visit was marked as not executed by the auto_cancel_fsm_task module, else 0.",
    )
    executed = fields.Integer(
        string='Executed',
        aggregator='sum',
        readonly=True,
        help="1 if the visit was actually carried out (not_executed = False), else 0.",
    )
    planned = fields.Integer(
        string='Planned',
        readonly=True,
        help=(
            "Always 1 per row. When summed in pivot/graph, gives the total number "
            "of planned visits regardless of execution status or sales outcome."
        ),
    )
    execution_rate = fields.Float(
        string='Execution Rate (%)',
        aggregator='avg',
        digits=(5, 2),
        readonly=True,
        help=(
            "Percentage of planned visits that were executed. "
            "Executed visit = 100.0, Not executed = 0.0. "
            "When grouped in pivot, the average equals the execution rate of the group."
        ),
    )
    not_execution_rate = fields.Float(
        string='Not Executed Rate (%)',
        aggregator='avg',
        digits=(5, 2),
        readonly=True,
        help=(
            "Percentage of planned visits that were NOT executed (auto-cancelled). "
            "Not executed = 100.0, Executed = 0.0. "
            "Complementary to Execution Rate: execution_rate + not_execution_rate = 100."
        ),
    )
    # -------------------------------------------------------------------------
    # Sale metrics
    # -------------------------------------------------------------------------
    has_sale = fields.Integer(
        string='Con Venta',
        aggregator='sum',
        readonly=True,
        help="1 if a confirmed Sale Order is linked to this visit, else 0.",
    )
    sale_order_count = fields.Integer(
        string='# Órdenes de Venta',
        readonly=True,
    )
    sale_amount_untaxed = fields.Monetary(
        string='Importe Neto (Ventas)',
        currency_field='currency_id',
        readonly=True,
    )
    sale_amount_total = fields.Monetary(
        string='Total Ventas',
        currency_field='currency_id',
        readonly=True,
    )
    conversion_rate = fields.Float(
        string='Conversion Rate (%)',
        aggregator='avg',
        digits=(5, 2),
        readonly=True,
        help=(
            "Percentage of executed visits that generated a confirmed Sale Order. "
            "Executed + sale = 100.0, Executed + no sale = 0.0, Not executed = NULL (excluded from average). "
            "When grouped in pivot, the average of these row values equals the conversion rate of the group."
        ),
    )

    # -------------------------------------------------------------------------
    # SQL View
    # -------------------------------------------------------------------------
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW report_fsm_task_visit AS (
                SELECT
                    ROW_NUMBER() OVER (
                        ORDER BY t.id, u.user_id
                    )                                           AS id,
                    t.id                                        AS task_id,
                    u.user_id                                   AS user_id,
                    t.partner_id,
                    t.project_id,
                    t.company_id,
                    c.currency_id,
                    t.planned_date_begin,
                    -- Date truncations for fast groupby in pivot/graph
                    (t.planned_date_begin AT TIME ZONE 'UTC')::date
                                                                AS planned_date,
                    DATE_TRUNC('week',
                        t.planned_date_begin AT TIME ZONE 'UTC'
                    )::date                                     AS planned_week,
                    DATE_TRUNC('month',
                        t.planned_date_begin AT TIME ZONE 'UTC'
                    )::date                                     AS planned_month,
                    t.state,
                    t.lost_reason_id,
                    COALESCE(t.not_executed, FALSE)::int       AS not_executed,
                    -- Executed: task must be DONE and NOT auto-cancelled
                    CASE WHEN NOT COALESCE(t.not_executed, FALSE)
                              AND t.state = '1_done'
                         THEN 1 ELSE 0
                    END                                          AS executed,
                    1                                            AS planned,
                    -- Execution rate: 100 if done + not auto-cancelled, 0 otherwise → AVG = % execution
                    CASE WHEN NOT COALESCE(t.not_executed, FALSE)
                              AND t.state = '1_done'
                         THEN 100.0 ELSE 0.0
                    END                                          AS execution_rate,
                    -- Not execution rate: 100 if auto-cancelled, 0 otherwise → AVG = % not executed
                    CASE WHEN COALESCE(t.not_executed, FALSE) THEN 100.0 ELSE 0.0 END     AS not_execution_rate,
                    -- Sale order: joined via project_task.sale_order_id (Odoo FSM native relation)
                    -- sale_order does NOT have a task_id column; the FK lives on project_task.
                    CASE WHEN so.id IS NOT NULL THEN 1    ELSE 0    END AS has_sale,
                    CASE WHEN so.id IS NOT NULL THEN 1    ELSE 0    END AS sale_order_count,
                    COALESCE(so.amount_untaxed, 0.0)    AS sale_amount_untaxed,
                    COALESCE(so.amount_total,   0.0)    AS sale_amount_total,
                    -- Conversion rate: 100.0 if executed+sold, 0.0 if executed+unsold, NULL if not done
                    -- Using AVG group_operator in ORM → yields % conversion when grouped
                    CASE
                        WHEN NOT COALESCE(t.not_executed, FALSE) AND t.state = '1_done'
                        THEN CASE WHEN so.id IS NOT NULL THEN 100.0 ELSE 0.0 END
                        ELSE NULL
                    END                                         AS conversion_rate
                FROM project_task t
                -- Expand per assigned user via user_ids M2M (project_task_user_rel)
                -- In Odoo 19, user_id has no SQL column; only user_ids is stored in the DB
                JOIN project_task_user_rel u
                    ON u.task_id = t.id

                -- FSM filter: is_fsm lives on project_project, not on project_task in Odoo 19
                JOIN project_project p
                    ON p.id = t.project_id AND p.is_fsm = TRUE
                -- Company currency
                JOIN res_company c
                    ON c.id = t.company_id
                -- Sale Order linked to the task via project_task.sale_order_id (only confirmed/done)
                LEFT JOIN sale_order so
                    ON so.id = t.sale_order_id
                   AND so.state IN ('sale', 'done')
                WHERE t.active     = TRUE
                  AND t.parent_id  IS NULL
            )
        """)
