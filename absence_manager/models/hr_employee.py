from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    attendance = fields.Boolean(
        string='Required to Mark Attendance?',
        help="When enabled, the daily Absence Monitor CRON will check if this employee "
             "has an attendance record for the day. If no record is found and the employee "
             "was scheduled to work (not a rest day or public holiday), an automatic leave "
             "of type 'Pending determination' (PPD) will be created. Disable this for "
             "employees who are exempt from attendance tracking (e.g., freelancers, managers).",
        groups="hr.group_hr_user",
        default=False,
    )