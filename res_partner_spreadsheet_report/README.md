# Contact Spreadsheet Report

Generate dynamic, filterable spreadsheet reports for your Contacts (Customers, Vendors, and Partners).

## Features

- **Smart Button Integration**: Access reports directly from any Contact with a single click
- **Template Management**: Create reusable spreadsheet templates with pre-configured charts and pivot tables
- **Automatic Filtering**: Reports are automatically filtered to show only data for the current contact
- **Flexible Configuration**: Assign default templates to Contacts or Contact Tags
- **Wizard Integration**: Insert charts and pivot tables from any Odoo view into your templates

## Installation

1. Install the module from Apps menu
2. The module will add a "Spreadsheet" smart button to all Contact forms
3. A new menu "Contact Spreadsheet Templates" will appear under Contacts > Configuration

## Configuration Guide

### Step 1: Create a Template

1. Go to **Contacts > Configuration > Contact Spreadsheet Templates**
2. Click **Create** (or add a new line in list view)
3. Enter a descriptive name (e.g., "Customer Analysis", "Vendor Report")
4. Click **Save**
5. Click the **Create Spreadsheet** button

### Step 2: Design Your Template

When the spreadsheet editor opens, you'll see a blank spreadsheet with a **Global Filter** already configured:

#### Understanding the Global Filter

- **Filter Name**: "Contact" (visible in the Filters panel on the right)
- **Purpose**: This filter will automatically populate with the current contact when a user opens a report
- **Status**: Initially empty (this is normal for templates)

#### Adding Data to Your Template

**Option A: Insert a Pivot Table**

1. Click **Insert** in the top menu
2. Select **Pivot Table**
3. Choose a model related to contacts:
   - `res.partner` (Contacts) - for contact details
   - `sale.order` (Sales Orders) - for sales analysis
   - `purchase.order` (Purchase Orders) - for vendor analysis
   - `account.move` (Invoices) - for invoice analysis
   - `crm.lead` (Opportunities) - for CRM analysis
4. Configure your pivot:
   - **Rows**: Add dimensions (e.g., Product, Salesperson, Date)
   - **Columns**: Add groupings (e.g., Status, Category)
   - **Measures**: Add metrics (e.g., Amount, Quantity, Count)
5. Click **Insert**

**Option B: Insert a List**

1. Click **Insert** > **List**
2. Choose a model (e.g., `sale.order`)
3. Select the fields you want to display
4. Click **Insert**

**Option C: Insert from Another View**

1. Navigate to any Odoo view (e.g., Sales > Orders)
2. Apply filters or groupings as needed
3. Click the **Favorites** menu (⭐)
4. Select **Insert in Spreadsheet**
5. Choose the **Contact Templates** tab
6. Select your template
7. The chart/list will be inserted

#### Step 3: Link Data to the Global Filter (CRITICAL)

After inserting a pivot table or list, you MUST link it to the Global Filter so it filters by the current contact:

**For Pivot Tables:**

1. Click on the pivot table in your spreadsheet
2. In the right panel, find the **Filters** section
3. You'll see the "Contact" filter listed
4. Click **Edit** (pencil icon) next to the Contact filter
5. In the popup, configure the relationship:
   - **Field to filter**: Select the field that links to `res.partner`
     - If using `res.partner`: Select `id` (the contact itself)
     - If using `sale.order`: Select `partner_id`
     - If using `purchase.order`: Select `partner_id`
     - If using `account.move`: Select `partner_id`
     - If using `crm.lead`: Select `partner_id`
     - If using other models: Select the appropriate Many2one field that links to contact
6. Click **Confirm**
7. The filter icon should now show as "linked" (🔗)

**For Lists:**

1. Click on the list in your spreadsheet
2. Follow the same steps as pivot tables to link the "Contact" filter

**Important Notes:**
- If you don't link the filter, the report will show ALL data from the database (not filtered by contact)
- You can verify the link by checking if the filter icon shows a chain link (🔗)
- You can link multiple pivot tables/lists to the same filter

**Common Field Mappings:**

| Model | Field to Link | Description |
|-------|---------------|-------------|
| `res.partner` | `id` | The contact itself |
| `sale.order` | `partner_id` | Customer on sales order |
| `purchase.order` | `partner_id` | Vendor on purchase order |
| `account.move` | `partner_id` | Customer/Vendor on invoice |
| `crm.lead` | `partner_id` | Customer on opportunity |
| `account.payment` | `partner_id` | Customer/Vendor on payment |

#### Step 4: Add Charts and Formatting

1. **Create Charts**: Select your pivot data > Insert > Chart
2. **Add Formulas**: Use standard spreadsheet formulas (SUM, AVERAGE, etc.)
3. **Format**: Apply colors, borders, fonts to make it visually appealing
4. **Add Headers**: Include titles, company logo, contact details, etc.

#### Step 5: Save Your Template

1. Click **Save** in the spreadsheet editor
2. Close the editor
3. Your template is now ready to use!

### Step 6: Assign the Template

You can assign templates at two levels (priority order):

**Option A: Assign to a Contact (Highest Priority)**

1. Go to **Contacts**
2. Open a Contact record
3. Find the field **Spreadsheet Template**
4. Select your template
5. Save

**Option B: Assign to Contact Tags**

1. Go to **Contacts > Configuration > Contact Tags**
2. Open a Tag
3. Find the field **Spreadsheet Template**
4. Select your template
5. Save

**Template Selection Logic:**
- When a user clicks the Spreadsheet button on a Contact:
  1. First checks if the Contact has a template assigned → Uses it
  2. If not, checks if any Contact Tag has a template → Uses the first one found
  3. If neither has a template → Shows an error with instructions

## Usage

### Creating a Report

1. Open any **Contact** record
2. Click the **Spreadsheet** smart button (shows count of existing reports)
3. **First time**: A new report is created from the template and opens automatically
4. **Subsequent times**: The existing report opens

### What Happens Automatically

- The report is created by copying the template
- The report name is set to: `[Template Name] - [Contact Name]`
- The "Contact" global filter is automatically set to the current contact
- All linked pivot tables and lists show data ONLY for this contact
- The report is saved and linked to the contact

### Editing a Report

- Users can modify their reports (add data, change formatting, etc.)
- Changes are saved automatically
- The original template remains unchanged

## Permissions

- **Contact Managers**: Can create and edit reports, can read templates
- **Sales Managers**: Can create, edit, and delete templates and reports

## Troubleshooting

**Problem**: Report shows all sales orders instead of just the current contact
- **Solution**: The pivot/list is not linked to the Global Filter. Edit the template and link the filter as described in Step 3.

**Problem**: Error "No Spreadsheet Template found"
- **Solution**: Assign a template to either the Contact or one of its Tags.

**Problem**: Smart button shows "0" but I created a report
- **Solution**: The report might be linked to a different contact. Check the report's name or create a new one.

**Problem**: Can't see the "Contact Templates" tab in "Insert in Spreadsheet"
- **Solution**: Make sure the module is installed and you've created at least one template.

**Problem**: Pivot table shows "No data" even though the contact has sales orders
- **Solution**: Check that you've linked the correct field in the Global Filter. For `sale.order`, you must link `partner_id`, not `id`.

## Example Use Cases

1. **Customer Sales Analysis**: Track sales orders, revenue, and product preferences by customer
2. **Vendor Purchase Report**: Monitor purchase orders, costs, and delivery performance
3. **Invoice Summary**: Analyze invoices, payments, and outstanding balances
4. **CRM Opportunity Pipeline**: Review opportunities, conversion rates, and revenue forecast

## Credits

**Author**: [Ganemo](https://www.ganemo.co)

This module was developed by Ganemo to provide advanced spreadsheet reporting capabilities for Odoo contacts.

## Support

For issues or questions, contact your system administrator or Ganemo support at www.ganemo.co
