# Filter Payroll

<div align="center">
  <img src="static/description/banner.png" width="100%" alt="Banner">
</div>

## Overview
The **Filter Payroll** module for Odoo 19 adds robust Attendance and Payroll analysis capabilities by identifying Work Entries that affect **CTS** and **Gratifications**.

Specifically designed for the Peruvian localization, it provides targeted search filters in:
- Attendances (`hr.attendance`)
- Leaves / Time Off (`hr.leave`)
- Payslips (`hr.payslip`)
- Worked Days (`hr.payslip.worked_days`)

## Usage and Configuration
1. Go to **Payroll > Configuration > Work Entry Types** or **Time Off > Configuration > Time Off Types**.
2. Mark the relevant records by checking the **Is CTS** or **Is Gratification** boxes.
3. In actual Payslips, Attendances, and Leaves, users can use the search bar filters to quickly look for records that have the CTS or Gratification tags.

### Filter Reference Summary

| Filter Name | Exact Menu Location | Target Model | Filtering Conditions (Logic) |
| :--- | :--- | :--- | :--- |
| **CTS** | Attendances > Attendances | `hr.attendance` | No Holiday Status (False) **OR** Holiday Code = '20' **OR** Is Tagged as "License for Social Benefits" **OR** Is Tagged as "Absence for Social Benefits" |
| **Gratification** | Attendances > Attendances | `hr.attendance` | No Holiday Status (False) **OR** Is Tagged as "License for Social Benefits" **OR** Is Tagged as "Absence for Social Benefits" |
| **CTS** | Time Off > Management > Time Off | `hr.leave` | Holiday Code = '20' **OR** Is Tagged as "License for Social Benefits" **OR** Is Tagged as "Absence for Social Benefits" |
| **Gratification** | Time Off > Management > Time Off | `hr.leave` | Is Tagged as "License for Social Benefits" **OR** Is Tagged as "Absence for Social Benefits" |

## Dependencies
This module strictly requires the following addons:
- `absence_day`
- `payroll_field`

**Author**: [Ganemo](https://www.ganemo.com)
