from odoo import fields, models


class ProjectProject(models.Model):
    _inherit = "project.project"

    include_in_visit_report = fields.Boolean(
        string="Include in Visit Reports",
        default=True,
        help=(
            "Controls whether tasks from this project are included in FSM visit reports.\n"
            "When enabled, this project's visits are considered in Visit Compliance, "
            "Conversion, and Sales Analysis report menus.\n"
            "When disabled, tasks from this project are excluded globally from "
            "report.fsm.task.visit analytics.\n"
            "Default is enabled for new projects."
        ),
    )

