# Stock Batch Spreadsheet Report

## Overview
This module empowers your warehouse team to generate detailed, dynamic reports for Batch Pickings using Odoo's powerful Spreadsheet engine. By configuring templates per Operation Type, you can instantly create reports (like Picking Lists, Packing Slips, or Analysis) that are automatically filtered to show only the data relevant to the current Batch.

## Features
- **Template Management**: Design templates using the standard Odoo Spreadsheet editor.
- **Dynamic Filtering**: Automatically injects the current Batch ID into the report's data source.
- **Operation Type Config**: Assign default templates to specific operation types (e.g., Pick, Pack, Ship).
- **Smart Button Access**: Generate and view reports directly from the Batch Picking form.

## Configuration
1.  Go to **Inventory > Configuration > Batch Spreadsheet Templates**.
2.  Create a new template. You can design it using the "Edit" button which opens the Odoo Spreadsheet editor.
3.  Go to **Inventory > Configuration > Operation Types**.
4.  Select an Operation Type (e.g., Pick).
5.  Set the **Batch Spreadsheet Template** field.

## Usage
1.  Go to **Inventory > Operations > Batch Transfers**.
2.  Open a Batch Picking.
3.  Click the **Create Report** button.
4.  Access the generated report via the **Reports** smart button.

## maintainer
    www.ganemo.com
