def migrate(cr, version):
    """
    Activate show_in_time_off_request for the 'S.I. Días Compens Por Horas De Sobretiempo'
    leave type (automatic_leave_type.hr_leave_type_27) in environments where both
    holiday_process and automatic_leave_type were previously installed together.

    This preserves the pre-refactor behaviour where that leave type showed
    the Allocation (hr_leave_id) field on the time off request form.

    Safe to run when automatic_leave_type is not installed — the subquery
    returns no rows and no rows are updated.
    """
    cr.execute("""
        UPDATE hr_leave_type
        SET show_in_time_off_request = TRUE
        WHERE id IN (
            SELECT res_id
            FROM ir_model_data
            WHERE module = 'automatic_leave_type'
              AND name = 'hr_leave_type_27'
              AND model = 'hr.leave.type'
        )
    """)
