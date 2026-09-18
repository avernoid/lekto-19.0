# **Peru - PLE 3.7 with Late Revaluations**

**Author**: [Ganemo](https://www.ganemo.com)

## Description

Book **3.7** (*detalle del saldo de la cuenta 20 — Mercaderías*) printed with the value **known at the end of the period**, so it closes on the same figure as the PLE 13.1 of that period and as the stock valuation account.

Installed automatically when `l10n_pe_reports_lib` and `stock_landed_cost_variance` are both present.

## What changes

| | Native 3.7 | With this module |
|---|---|---|
| Value | Sum of the stored value of the movements today, including freights and bills that arrived after the period | Value known at the end of the period |
| Movements of the last day of the period | Left out (the query compares the movement date with the date alone) | Included |
| Cancelled movements | Counted in the quantity | Only done movements |

Measured: receipt of 5 at 500, 3 sold in July, freight of 250 in August.

| 3.7 at | Native | Here |
|---|---|---|
| 31 July, generated in August | 1 100 | **1 000** (as filed) |
| 31 August | 1 100 | 1 100 |

Rows, codes, names and catalogues are the native ones. Rows are matched to products by the printed code; a code shared by two products is left as computed natively and logged.

## Support

For commercial inquiries: [leads@ganemo.com](mailto:leads@ganemo.com).
For technical support and bug reports: [ayuda@ganemo.com](mailto:ayuda@ganemo.com) or visit [ganemo.co](https://www.ganemo.co).
