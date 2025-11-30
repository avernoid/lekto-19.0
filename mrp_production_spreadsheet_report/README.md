# MRP Production Spreadsheet Report

Generate dynamic, filterable spreadsheet reports for your Manufacturing Orders.

## Features

- **Smart Button Integration**: Access reports directly from any Manufacturing Order with a single click
- **Template Management**: Create reusable spreadsheet templates with pre-configured charts and pivot tables
- **Automatic Filtering**: Reports are automatically filtered to show only data for the current production order
- **Flexible Configuration**: Assign default templates to Bills of Materials or Picking Types
- **Wizard Integration**: Insert charts and pivot tables from any Odoo view into your templates

## Installation

1. Install the module from Apps menu
2. The module will add a "Spreadsheet" smart button to all Manufacturing Order forms
3. A new menu "MRP Spreadsheet Templates" will appear under Manufacturing > Configuration

## Configuration Guide

### Step 1: Create a Template

1. Go to **Manufacturing > Configuration > MRP Spreadsheet Templates**
2. Click **Create** (or add a new line in list view)
3. Enter a descriptive name (e.g., "Production Analysis", "Material Consumption Report")
4. Click **Save**
5. Click the **Create Spreadsheet** button

### Step 2: Design Your Template

When the spreadsheet editor opens, you'll see a blank spreadsheet with a **Global Filter** already configured:

#### Understanding the Global Filter

- **Filter Name**: "Manufacturing Order" (visible in the Filters panel on the right)
- **Purpose**: This filter will automatically populate with the current manufacturing order when a user opens a report
- **Status**: Initially empty (this is normal for templates)

#### Adding Data to Your Template

**Option A: Insert a Pivot Table**

1. Click **Insert** in the top menu
2. Select **Pivot Table**
3. Choose a model related to manufacturing:
   - `mrp.production` (Manufacturing Orders) - for production details
   - `stock.move` (Stock Moves) - for material consumption and production
   - `mrp.workorder` (Work Orders) - for operation analysis
   - `product.product` (Products) - for product analysis
   - `mrp.bom` (Bills of Materials) - for BOM structure
4. Configure your pivot:
   - **Rows**: Add dimensions (e.g., Product, Work Center, Operation)
   - **Columns**: Add groupings (e.g., Date, Status, Location)
   - **Measures**: Add metrics (e.g., Quantity, Duration, Cost)
5. Click **Insert**

**Option B: Insert a List**

1. Click **Insert** > **List**
2. Choose a model (e.g., `stock.move`)
3. Select the fields you want to display
4. Click **Insert**

**Option C: Insert from Another View**

1. Navigate to any Odoo view (e.g., Manufacturing > Products)
2. Apply filters or groupings as needed
3. Click the **Favorites** menu (⭐)
4. Select **Insert in Spreadsheet**
5. Choose the **MRP Templates** tab
6. Select your template
7. The chart/list will be inserted

#### Step 3: Link Data to the Global Filter (CRITICAL)

After inserting a pivot table or list, you MUST link it to the Global Filter so it filters by the current manufacturing order:

**For Pivot Tables:**

1. Click on the pivot table in your spreadsheet
2. In the right panel, find the **Filters** section
3. You'll see the "Manufacturing Order" filter listed
4. Click **Edit** (pencil icon) next to the Manufacturing Order filter
5. In the popup, configure the relationship:
   - **Field to filter**: Select the field that links to `mrp.production`
     - If using `mrp.production`: Select `id` (the production order itself)
     - If using `stock.move`: Select `production_id` or `raw_material_production_id`
     - If using `mrp.workorder`: Select `production_id`
     - If using `product.product`: You may need to use a related field or skip filtering
     - If using other models: Select the appropriate Many2one field that links to production
6. Click **Confirm**
7. The filter icon should now show as "linked" (🔗)

**For Lists:**

1. Click on the list in your spreadsheet
2. Follow the same steps as pivot tables to link the "Manufacturing Order" filter

**Important Notes:**
- If you don't link the filter, the report will show ALL data from the database (not filtered by production order)
- You can verify the link by checking if the filter icon shows a chain link (🔗)
- You can link multiple pivot tables/lists to the same filter

**Common Field Mappings:**

| Model | Field to Link | Description |
|-------|---------------|-------------|
| `mrp.production` | `id` | The production order itself |
| `stock.move` | `production_id` | Finished product moves |
| `stock.move` | `raw_material_production_id` | Raw material consumption |
| `mrp.workorder` | `production_id` | Work orders for this production |
| `mrp.bom.line` | Use related field | May need `bom_id.product_id` |

**Special Case - Stock Moves:**
Stock moves have TWO fields that can link to production:
- `production_id`: For moves that PRODUCE the finished product
- `raw_material_production_id`: For moves that CONSUME raw materials

Choose the appropriate field based on what you want to analyze.

#### Step 4: Add Charts and Formatting

1. **Create Charts**: Select your pivot data > Insert > Chart
2. **Add Formulas**: Use standard spreadsheet formulas (SUM, AVERAGE, etc.)
3. **Format**: Apply colors, borders, fonts to make it visually appealing
4. **Add Headers**: Include titles, company logo, production details, etc.

#### Step 5: Save Your Template

1. Click **Save** in the spreadsheet editor
2. Close the editor
3. Your template is now ready to use!

### Step 6: Assign the Template

You can assign templates at two levels (priority order):

**Option A: Assign to a Bill of Materials (Highest Priority)**

1. Go to **Manufacturing > Products > Bills of Materials**
2. Open a Bill of Materials
3. Find the field **Spreadsheet Template**
4. Select your template
5. Save

**Option B: Assign to a Picking Type**

1. Go to **Inventory > Configuration > Operations Types**
2. Open a Picking Type (e.g., "Manufacturing")
3. Find the field **MRP Spreadsheet Template**
4. Select your template
5. Save

**Template Selection Logic:**
- When a user clicks the Spreadsheet button on a Manufacturing Order:
  1. First checks if the Bill of Materials has a template assigned → Uses it
  2. If not, checks if the Picking Type has a template → Uses it
  3. If neither has a template → Shows an error with instructions

## Usage

### Creating a Report

1. Open any **Manufacturing Order**
2. Click the **Spreadsheet** smart button (shows count of existing reports)
3. **First time**: A new report is created from the template and opens automatically
4. **Subsequent times**: The existing report opens

### What Happens Automatically

- The report is created by copying the template
- The report name is set to: `[Template Name] - [MO Reference]`
- The "Manufacturing Order" global filter is automatically set to the current production
- All linked pivot tables and lists show data ONLY for this production order
- The report is saved and linked to the manufacturing order

### Editing a Report

- Users can modify their reports (add data, change formatting, etc.)
- Changes are saved automatically
- The original template remains unchanged

## Permissions

- **Manufacturing Users**: Can create and edit reports, can read templates
- **Manufacturing Managers**: Can create, edit, and delete templates and reports

## Troubleshooting

**Problem**: Report shows all stock moves instead of just the current production
- **Solution**: The pivot/list is not linked to the Global Filter. Edit the template and link the filter as described in Step 3.

**Problem**: Stock moves show finished products but not raw materials (or vice versa)
- **Solution**: Check which field you linked in the filter. Use `production_id` for finished products, `raw_material_production_id` for raw materials.

**Problem**: Error "No Spreadsheet Template found"
- **Solution**: Assign a template to either the Bill of Materials or the Picking Type.

**Problem**: Smart button shows "0" but I created a report
- **Solution**: The report might be linked to a different production order. Check the report's name or create a new one.

**Problem**: Can't see the "MRP Templates" tab in "Insert in Spreadsheet"
- **Solution**: Make sure the module is installed and you've created at least one template.

**Problem**: Pivot table shows "No data" even though the production has stock moves
- **Solution**: Check that you've linked the correct field in the Global Filter. For `stock.move`, you must link either `production_id` or `raw_material_production_id`, not `id`.

**Problem**: Work orders don't appear in the report
- **Solution**: Make sure you're using the `mrp.workorder` model and linking the `production_id` field to the filter.

## Example Use Cases

1. **Production Efficiency Dashboard**: Track work order durations, delays, and productivity
2. **Material Consumption Report**: Monitor raw material usage, waste, and variances
3. **Cost Analysis**: Compare planned vs actual costs for materials and operations
4. **Quality Metrics**: Analyze scrap rates, rework, and quality check results
5. **BOM Comparison**: Compare different BOMs for the same product

## Credits

**Author**: [Ganemo](https://www.ganemo.co)

This module was developed by Ganemo to provide advanced spreadsheet reporting capabilities for Odoo manufacturing operations.

## Support

For issues or questions, contact your system administrator or Ganemo support at www.ganemo.co
