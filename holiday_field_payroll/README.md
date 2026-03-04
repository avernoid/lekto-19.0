# Holiday Field Payroll 
<img src="static/description/banner.png" width="100%" alt="Banner">

Regular payroll calculation requires the monthly salary, which is the total salary stipulated in the employee's contract. This module automatically determines the daily rate (calculated by dividing the monthly salary by the number of working days in the month) and the hourly rate (determined by dividing the daily rate by the standard number of work hours per day). 

Standard working hours must also be defined, facilitating any hours worked beyond these as overtime to be appropriately tracked and compensated.

## Features

*   **Automated Daily Rates:** Calculates the daily rate from the contract's monthly salary.
*   **Automatic Hourly Rates:** Computes the hourly rate based on standard working hours.
*   **Contract Setup:** Extends the employee contract form with standard working hours and days setup.
*   **Multi-currency & localization compatible:** Works natively with Odoo's core modules.

## Configuration & Usage

1. Navigate to **Employees > Contracts**.
2. Open or create an employee contract.
3. Observe the newly added fields for standard working days per month and working hours per day.
4. Input the monthly wage, and the module calculates the daily and hourly wates on the fly.
5. These fields will be directly available to be called from the payroll rules.

**Author**: [Ganemo](https://www.ganemo.com)
