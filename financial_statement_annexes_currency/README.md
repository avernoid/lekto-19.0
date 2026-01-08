# **Unrealized gains and losses for foreign currency**

<img src="static/description/banner.png" width="100%" alt="Banner">

**Author**: [Ganemo](https://www.ganemo.com)

This module allows you to calculate the exchange rate difference of accounting accounts in foreign currency and record the accounting entry for the difference automatically. It is essential for companies managing assets or liabilities in multiple currencies who need accurate period-end financial statements.

## Key Features
- **Automatic Calculation**: Uses system exchange rates to calculate unrealized gains/losses.
- **Wizard Interface**: Easy-to-use wizard to select accounts and dates.
- **Adjustment Entries**: Automatically posts adjustment entries to the general ledger.
- **Reversal**: Option to reverse the entry at the beginning of the next period.

## Installation
1. Install the module.
2. Ensure `financial_statement_annexes` is also installed (dependency).

## Configuration
Go to **Accounting > Configuration > Settings** and ensure your Currency Exchange Journal and Accounts are set up correctly.

## Usage
1. Go to **Accounting > Reporting > Unrealized Gains/Losses**.
2. Select the date range and accounts.
3. Click "Generate Entry".
