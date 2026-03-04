def migrate(cr, version):
    """Rename column gender → sex in hr_employee_relative table."""
    cr.execute("""
        ALTER TABLE hr_employee_relative
        RENAME COLUMN gender TO sex
    """)
