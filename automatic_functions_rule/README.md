# **Automatic Functions Rule**

<img src="static/description/banner.png" width="100%" alt="Banner">

## Overview

**Automatic Functions Rule** is an Odoo 19 module that automatically cleans zero-value lines from payslips (`hr.payslip`) and injects input line types from the salary structure. It ensures your payroll data is clean, professional, and ready for reporting — without any manual intervention.

## Features

### 1. Automatic Zero-Value Cleanup

The module automatically removes lines with zero values at three key moments:

| Trigger | What Gets Cleaned |
|---|---|
| **Compute Sheet** | Salary lines (`hr.payslip.line`) where `total == 0` |
| **Confirm Payslip** | Worked days with `number_of_days == 0` and inputs with `amount == 0` |
| **"Eliminate Zeros" Button** | All of the above (manual trigger) |

### 2. Manual "Eliminate Zeros" Button

A button is added to the payslip form (next to "Print Payslip") that allows manual execution of all three cleanup functions. Safe to press multiple times — if there are no zero-value lines, nothing happens.

### 3. Structure Input Injection

When an employee or salary structure is selected, the module reads the **Input Line Types** configured in the salary structure and creates corresponding input lines on the payslip with `amount = 0`, ready for the user to fill in.

**Optional Integration:** If the `data.utilities` module is installed and has an active record, the system automatically fills:
- `UTL_003` → `utilities.factor_days`
- `UTL_004` → `utilities.factor_amount`

### 4. Batch Payroll Integration

The module extends batch payroll generation (`hr.payslip.run`) to inject structure inputs after payslip computation, ensuring consistency across mass-generated payslips.

## Configuration

**No configuration required.** Install the module and it works immediately. The cleanup runs automatically during standard payroll operations.

To configure which input types are injected, go to:
**Payroll → Configuration → Structures → [Your Structure] → Input Line Types**

## Dependencies

| Module | Purpose |
|---|---|
| `hr_payroll` | Base payroll module (required) |
| `data.utilities` | Optional: Peruvian utility factors auto-fill |

## Compatibility

- **Odoo Version:** 19.0
- **Edition:** Enterprise (Odoo.SH, Ganemo Online, Ganemo.SH)
- **Languages:** English, Spanish

## Technical Details

### Models Extended

- **`hr.payslip`** — Added cleanup methods and structure input injection
- **`hr.payslip.run`** — Extended batch generation to inject inputs post-computation

### Key Methods

| Method | Description |
|---|---|
| `_remove_zero_salary_lines()` | Removes `hr.payslip.line` records with `total == 0` |
| `_remove_zero_worked_days()` | Removes worked days with `number_of_days == 0` |
| `_remove_zero_inputs()` | Removes input lines with `amount == 0` |
| `action_remove_zeros()` | Manual button: executes all three cleanup methods |
| `get_inputs_data()` | Reads input types from structure and builds values |
| `get_inputs()` | Creates input line records on the payslip |

## License

**OPL-1** (Odoo Proprietary License v1.0)

## **Author**: [Ganemo](https://www.ganemo.co)
