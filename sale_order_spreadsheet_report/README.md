# Sale Order Spreadsheet Report

Generate dynamic, filterable spreadsheet reports for your Sales Orders (Quotations).

## Features

- **Smart Button Integration**: Access reports directly from any Sale Order with a single click
- **Template Management**: Create reusable spreadsheet templates with pre-configured charts and pivot tables
- **Automatic Filtering**: Reports are automatically filtered to show only data for the current sale order
- **Flexible Configuration**: Assign default templates to CRM Tags, Sales Teams, or Quotation Templates
- **Wizard Integration**: Insert charts and pivot tables from any Odoo view into your templates

## Installation

1. Install the module from Apps menu
2. The module will add a "Spreadsheet" smart button to all Sale Order forms
3. A new menu "Sale Spreadsheet Templates" will appear under Sales > Configuration

## Configuration Guide

### Step 1: Create a Template

1. Go to **Sales > Configuration > Sale Spreadsheet Templates**
2. Click **Create** (or add a new line in list view)
3. Enter a descriptive name (e.g., "Margin Analysis", "Product Mix")
4. Click **Save**
5. Click the **Create Spreadsheet** button

### Step 2: Design Your Template

When the spreadsheet editor opens, you'll see a blank spreadsheet with a **Global Filter** already configured:

#### Understanding the Global Filter

- **Filter Name**: "Sale Order" (visible in the Filters panel on the right)
- **Purpose**: This filter will automatically populate with the current sale order when a user opens a report
- **Status**: Initially empty (this is normal for templates)

#### Adding Data to Your Template

**Option A: Insert a Pivot Table**

1. Click **Insert** in the top menu
2. Select **Pivot Table**
3. Choose a model related to sales:
   - `sale.order` (Sales Orders) - for order-level analysis
   - `sale.order.line` (Sales Order Lines) - for product/line-level analysis
   - `account.move.line` (Invoice Lines) - for invoice analysis (requires linking)
4. Configure your pivot:
   - **Rows**: Add dimensions (e.g., Product, Category, Salesperson)
   - **Columns**: Add groupings (e.g., Date, Status)
   - **Measures**: Add metrics (e.g., Total, Quantity, Margin, Discount)
5. Click **Insert**

**Option B: Insert a List**

1. Click **Insert** > **List**
2. Choose a model (e.g., `sale.order.line`)
3. Select the fields you want to display
4. Click **Insert**

**Option C: Insert from Another View**

1. Navigate to any Odoo view (e.g., Sales > Orders)
2. Apply filters or groupings as needed
3. Click the **Favorites** menu (⭐)
4. Select **Insert in Spreadsheet**
5. Choose the **Sale Templates** tab
6. Select your template
7. The chart/list will be inserted

#### Step 3: Link Data to the Global Filter (CRITICAL)

After inserting a pivot table or list, you MUST link it to the Global Filter so it filters by the current sale order:

**For Pivot Tables:**

1. Click on the pivot table in your spreadsheet
2. In the right panel, find the **Filters** section
3. You'll see the "Sale Order" filter listed
4. Click **Edit** (pencil icon) next to the Sale Order filter
5. In the popup, configure the relationship:
   - **Field to filter**: Select the field that links to `sale.order`
     - If using `sale.order`: Select `id` (the order itself)
     - If using `sale.order.line`: Select `order_id`
     - If using `stock.move`: Select `origin` (requires exact match) or related field
     - If using other models: Select the appropriate Many2one field that links to sale order
6. Click **Confirm**
7. The filter icon should now show as "linked" (🔗)

**For Lists:**

1. Click on the list in your spreadsheet
2. Follow the same steps as pivot tables to link the "Sale Order" filter

**Important Notes:**
- If you don't link the filter, the report will show ALL data from the database (not filtered by order)
- You can verify the link by checking if the filter icon shows a chain link (🔗)
- You can link multiple pivot tables/lists to the same filter

**Common Field Mappings:**

| Model | Field to Link | Description |
|-------|---------------|-------------|
| `sale.order` | `id` | The order itself |
| `sale.order.line` | `order_id` | Lines belonging to the order |
| `account.move` | `invoice_origin` | Linked via source document (text match) |
| `stock.picking` | `origin` | Linked via source document (text match) |

#### Step 4: Add Charts and Formatting

1. **Create Charts**: Select your pivot data > Insert > Chart
2. **Add Formulas**: Use standard spreadsheet formulas (SUM, AVERAGE, etc.)
3. **Format**: Apply colors, borders, fonts to make it visually appealing
4. **Add Headers**: Include titles, company logo, order details, etc.

#### Step 5: Save Your Template

1. Click **Save** in the spreadsheet editor
2. Close the editor
3. Your template is now ready to use!

### Step 6: Assign the Template

You can assign templates at three levels (priority order):

**Option A: Assign to CRM Tags (Highest Priority)**

1. Go to **Sales > Configuration > Tags**
2. Open a Tag
3. Find the field **Sale Spreadsheet Template**
4. Select your template
5. Save
*Note: If an order has multiple tags, the first one with a template is used.*

**Option B: Assign to Sales Team**

1. Go to **Sales > Configuration > Sales Teams**
2. Open a Team
3. Find the field **Sale Spreadsheet Template**
4. Select your template
5. Save

**Option C: Assign to Quotation Template**

1. Go to **Sales > Configuration > Quotation Templates**
2. Open a Template
3. Find the field **Spreadsheet Template**
4. Select your template
5. Save

**Template Selection Logic:**
- When a user clicks the Spreadsheet button on a Sale Order:
  1. Checks **CRM Tags** on the order → Uses first found template
  2. If none, checks **Sales Team** → Uses assigned template
  3. If none, checks **Quotation Template** → Uses assigned template
  4. If none → Shows an error with instructions

## Usage

### Creating a Report

1. Open any **Sale Order**
2. Click the **Spreadsheet** smart button (shows count of existing reports)
3. **First time**: A new report is created from the template and opens automatically
4. **Subsequent times**: The existing report opens

### What Happens Automatically

- The report is created by copying the template
- The report name is set to: `[Template Name] - [Order Reference]`
- The "Sale Order" global filter is automatically set to the current order
- All linked pivot tables and lists show data ONLY for this order
- The report is saved and linked to the sale order

### Editing a Report

- Users can modify their reports (add data, change formatting, etc.)
- Changes are saved automatically
- The original template remains unchanged

## Permissions

- **Sales Users**: Can create and edit reports, can read templates
- **Sales Managers**: Can create, edit, and delete templates and reports

## Troubleshooting

**Problem**: Report shows all sale lines instead of just the current order
- **Solution**: The pivot/list is not linked to the Global Filter. Edit the template and link the filter as described in Step 3.

**Problem**: Error "No Spreadsheet Template found"
- **Solution**: Assign a template to a CRM Tag, Sales Team, or Quotation Template associated with the order.

**Problem**: Smart button shows "0" but I created a report
- **Solution**: The report might be linked to a different order. Check the report's name or create a new one.

**Problem**: Can't see the "Sale Templates" tab in "Insert in Spreadsheet"
- **Solution**: Make sure the module is installed and you've created at least one template.

**Problem**: Pivot table shows "No data" even though the order has lines
- **Solution**: Check that you've linked the correct field in the Global Filter. For `sale.order.line`, you must link `order_id`, not `id`.

## Example Use Cases

1. **Profitability Analysis**: Detailed margin analysis by product and category for large quotes
2. **Discount Report**: Track discounts given on lines compared to standard prices
3. **Product Mix**: Visualize the distribution of product categories in the order
4. **Commission Calculation**: Estimate commissions based on order value and salesperson rules

## Credits

**Author**: [Ganemo](https://www.ganemo.co)

This module was developed by Ganemo to provide advanced spreadsheet reporting capabilities for Odoo sales.

## Support

For issues or questions, contact your system administrator or Ganemo support at www.ganemo.co
