# Stock Picking Spreadsheet Report

Generate dynamic, filterable spreadsheet reports for your Stock Pickings (Transfers, Deliveries, Receipts, etc.).

## Features

- **Smart Button Integration**: Access reports directly from any Picking with a single click
- **Template Management**: Create reusable spreadsheet templates with pre-configured charts and pivot tables
- **Automatic Filtering**: Reports are automatically filtered to show only data for the current picking
- **Flexible Configuration**: Assign default templates to Partners or Picking Types
- **Wizard Integration**: Insert charts and pivot tables from any Odoo view into your templates

## Installation

1. Install the module from Apps menu
2. The module will add a "Spreadsheet" smart button to all Picking forms
3. A new menu "Picking Spreadsheet Templates" will appear under Inventory > Configuration

## Configuration Guide

### Step 1: Create a Template

1. Go to **Inventory > Configuration > Picking Spreadsheet Templates**
2. Click **Create** (or add a new line in list view)
3. Enter a descriptive name (e.g., "Delivery Analysis", "Receipt Report")
4. Click **Save**
5. Click the **Create Spreadsheet** button

### Step 2: Design Your Template

When the spreadsheet editor opens, you'll see a blank spreadsheet with a **Global Filter** already configured:

#### Understanding the Global Filter

- **Filter Name**: "Picking" (visible in the Filters panel on the right)
- **Purpose**: This filter will automatically populate with the current picking when a user opens a report
- **Status**: Initially empty (this is normal for templates)

#### Adding Data to Your Template

**Option A: Insert a Pivot Table**

1. Click **Insert** in the top menu
2. Select **Pivot Table**
3. Choose a model related to pickings:
   - `stock.move` (Stock Moves) - for line-level details
   - `stock.move.line` (Stock Move Lines) - for detailed lot/serial tracking
   - `product.product` (Products) - for product analysis
4. Configure your pivot:
   - **Rows**: Add dimensions (e.g., Product, Location, Date)
   - **Columns**: Add groupings (e.g., State, Partner)
   - **Measures**: Add metrics (e.g., Quantity, Reserved Quantity)
5. Click **Insert**

**Option B: Insert a List**

1. Click **Insert** > **List**
2. Choose a model (e.g., `stock.move`)
3. Select the fields you want to display
4. Click **Insert**

**Option C: Insert from Another View**

1. Navigate to any Odoo view (e.g., Inventory > Products)
2. Apply filters or groupings as needed
3. Click the **Favorites** menu (⭐)
4. Select **Insert in Spreadsheet**
5. Choose the **Picking Templates** tab
6. Select your template
7. The chart/list will be inserted

#### Step 3: Link Data to the Global Filter (CRITICAL)

After inserting a pivot table or list, you MUST link it to the Global Filter so it filters by the current picking:

**For Pivot Tables:**

1. Click on the pivot table in your spreadsheet
2. In the right panel, find the **Filters** section
3. You'll see the "Picking" filter listed
4. Click **Edit** (pencil icon) next to the Picking filter
5. In the popup, configure the relationship:
   - **Field to filter**: Select the field that links to `stock.picking`
     - If using `stock.move`: Select `picking_id`
     - If using `stock.move.line`: Select `picking_id`
     - If using other models: Select the appropriate Many2one field that links to picking
6. Click **Confirm**
7. The filter icon should now show as "linked" (🔗)

**For Lists:**

1. Click on the list in your spreadsheet
2. Follow the same steps as pivot tables to link the "Picking" filter

**Important Notes:**
- If you don't link the filter, the report will show ALL data from the database (not filtered by picking)
- You can verify the link by checking if the filter icon shows a chain link (🔗)
- You can link multiple pivot tables/lists to the same filter

#### Step 4: Add Charts and Formatting

1. **Create Charts**: Select your pivot data > Insert > Chart
2. **Add Formulas**: Use standard spreadsheet formulas (SUM, AVERAGE, etc.)
3. **Format**: Apply colors, borders, fonts to make it visually appealing
4. **Add Headers**: Include titles, company logo, etc.

#### Step 5: Save Your Template

1. Click **Save** in the spreadsheet editor
2. Close the editor
3. Your template is now ready to use!

### Step 6: Assign the Template

You can assign templates at two levels (priority order):

**Option A: Assign to a Partner (Highest Priority)**

1. Go to **Contacts**
2. Open a Partner (Customer or Supplier)
3. Find the field **Picking Spreadsheet Template**
4. Select your template
5. Save

**Option B: Assign to a Picking Type**

1. Go to **Inventory > Configuration > Operation Types**
2. Open a Picking Type (e.g., "Delivery Orders", "Receipts")
3. Find the field **Spreadsheet Template**
4. Select your template
5. Save

**Template Selection Logic:**
- When a user clicks the Spreadsheet button on a Picking:
  1. First checks if the Partner has a template assigned → Uses it
  2. If not, checks if the Picking Type has a template → Uses it
  3. If neither has a template → Shows an error with instructions

## Usage

### Creating a Report

1. Open any **Stock Picking** (Transfer, Delivery, Receipt, etc.)
2. Click the **Spreadsheet** smart button (shows count of existing reports)
3. **First time**: A new report is created from the template and opens automatically
4. **Subsequent times**: The existing report opens

### What Happens Automatically

- The report is created by copying the template
- The report name is set to: `[Template Name] - [Picking Name]`
- The "Picking" global filter is automatically set to the current picking
- All linked pivot tables and lists show data ONLY for this picking
- The report is saved and linked to the picking

### Editing a Report

- Users can modify their reports (add data, change formatting, etc.)
- Changes are saved automatically
- The original template remains unchanged

## Permissions

- **Inventory Users**: Can create and edit reports, can read templates
- **Inventory Managers**: Can create, edit, and delete templates and reports

## Troubleshooting

**Problem**: Report shows all data instead of just the current picking
- **Solution**: The pivot/list is not linked to the Global Filter. Edit the template and link the filter as described in Step 3.

**Problem**: Error "No Spreadsheet Template found"
- **Solution**: Assign a template to either the Partner or the Picking Type.

**Problem**: Smart button shows "0" but I created a report
- **Solution**: The report might be linked to a different picking. Check the report's name or create a new one.

**Problem**: Can't see the "Picking Templates" tab in "Insert in Spreadsheet"
- **Solution**: Make sure the module is installed and you've created at least one template.

## Example Use Cases

1. **Delivery Analysis**: Track products delivered, quantities, and destinations
2. **Receipt Report**: Monitor incoming products, suppliers, and quality checks
3. **Transfer Summary**: Analyze internal movements between locations
4. **Partner Performance**: Compare delivery times and quantities by partner

## Credits

**Author**: [Ganemo](https://www.ganemo.co)

This module was developed by Ganemo to provide advanced spreadsheet reporting capabilities for Odoo inventory operations.

## Support

For issues or questions, contact your system administrator or Ganemo support at www.ganemo.co
