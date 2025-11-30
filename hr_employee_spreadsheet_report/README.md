# Employee Spreadsheet Report

Generate dynamic, filterable spreadsheet reports for your Employees.

## Features

- **Smart Button Integration**: Access reports directly from any Employee with a single click
- **Template Management**: Create reusable spreadsheet templates with pre-configured charts and pivot tables
- **Automatic Filtering**: Reports are automatically filtered to show only data for the current employee
- **Flexible Configuration**: Assign default templates to Employees or Job Positions
- **Wizard Integration**: Insert charts and pivot tables from any Odoo view into your templates

## Installation

1. Install the module from Apps menu
2. The module will add a "Spreadsheet" smart button to all Employee forms
3. A new menu "Employee Spreadsheet Templates" will appear under Employees > Configuration

## Configuration Guide

### Step 1: Create a Template

1. Go to **Employees > Configuration > Employee Spreadsheet Templates**
2. Click **Create** (or add a new line in list view)
3. Enter a descriptive name (e.g., "Employee Performance", "Attendance Report")
4. Click **Save**
5. Click the **Create Spreadsheet** button

### Step 2: Design Your Template

When the spreadsheet editor opens, you'll see a blank spreadsheet with a **Global Filter** already configured:

#### Understanding the Global Filter

- **Filter Name**: "Employee" (visible in the Filters panel on the right)
- **Purpose**: This filter will automatically populate with the current employee when a user opens a report
- **Status**: Initially empty (this is normal for templates)

#### Adding Data to Your Template

**Option A: Insert a Pivot Table**

1. Click **Insert** in the top menu
2. Select **Pivot Table**
3. Choose a model related to employees:
   - `hr.employee` (Employees) - for employee details
   - `hr.attendance` (Attendances) - for attendance analysis
   - `hr.leave` (Time Off) - for leave analysis
   - `hr.contract` (Contracts) - for contract information
4. Configure your pivot:
   - **Rows**: Add dimensions (e.g., Department, Job Position)
   - **Columns**: Add groupings (e.g., Date, Status)
   - **Measures**: Add metrics (e.g., Count, Hours, Days)
5. Click **Insert**

**Option B: Insert a List**

1. Click **Insert** > **List**
2. Choose a model (e.g., `hr.attendance`)
3. Select the fields you want to display
4. Click **Insert**

**Option C: Insert from Another View**

1. Navigate to any Odoo view (e.g., Employees > Attendances)
2. Apply filters or groupings as needed
3. Click the **Favorites** menu (⭐)
4. Select **Insert in Spreadsheet**
5. Choose the **Employee Templates** tab
6. Select your template
7. The chart/list will be inserted

#### Step 3: Link Data to the Global Filter (CRITICAL)

After inserting a pivot table or list, you MUST link it to the Global Filter so it filters by the current employee:

**For Pivot Tables:**

1. Click on the pivot table in your spreadsheet
2. In the right panel, find the **Filters** section
3. You'll see the "Employee" filter listed
4. Click **Edit** (pencil icon) next to the Employee filter
5. In the popup, configure the relationship:
   - **Field to filter**: Select the field that links to `hr.employee`
     - If using `hr.employee`: Select `id` (the employee itself)
     - If using `hr.attendance`: Select `employee_id`
     - If using `hr.leave`: Select `employee_id`
     - If using `hr.contract`: Select `employee_id`
     - If using other models: Select the appropriate Many2one field that links to employee
6. Click **Confirm**
7. The filter icon should now show as "linked" (🔗)

**For Lists:**

1. Click on the list in your spreadsheet
2. Follow the same steps as pivot tables to link the "Employee" filter

**Important Notes:**
- If you don't link the filter, the report will show ALL data from the database (not filtered by employee)
- You can verify the link by checking if the filter icon shows a chain link (🔗)
- You can link multiple pivot tables/lists to the same filter

**Common Field Mappings:**

| Model | Field to Link |
|-------|---------------|
| `hr.employee` | `id` |
| `hr.attendance` | `employee_id` |
| `hr.leave` | `employee_id` |
| `hr.contract` | `employee_id` |
| `hr.payslip` | `employee_id` |
| `hr.expense` | `employee_id` |

#### Step 4: Add Charts and Formatting

1. **Create Charts**: Select your pivot data > Insert > Chart
2. **Add Formulas**: Use standard spreadsheet formulas (SUM, AVERAGE, etc.)
3. **Format**: Apply colors, borders, fonts to make it visually appealing
4. **Add Headers**: Include titles, company logo, employee details, etc.

#### Step 5: Save Your Template

1. Click **Save** in the spreadsheet editor
2. Close the editor
3. Your template is now ready to use!

### Step 6: Assign the Template

You can assign templates at two levels (priority order):

**Option A: Assign to an Employee (Highest Priority)**

1. Go to **Employees**
2. Open an Employee record
3. Find the field **Spreadsheet Template** (usually near Job Position)
4. Select your template
5. Save

**Option B: Assign to a Job Position**

1. Go to **Employees > Configuration > Job Positions**
2. Open a Job Position
3. Find the field **Spreadsheet Template** in the "Job" section
4. Select your template
5. Save

**Template Selection Logic:**
- When a user clicks the Spreadsheet button on an Employee:
  1. First checks if the Employee has a template assigned → Uses it
  2. If not, checks if the Job Position has a template → Uses it
  3. If neither has a template → Shows an error with instructions

## Usage

### Creating a Report

1. Open any **Employee** record
2. Click the **Spreadsheet** smart button (shows count of existing reports)
3. **First time**: A new report is created from the template and opens automatically
4. **Subsequent times**: The existing report opens

### What Happens Automatically

- The report is created by copying the template
- The report name is set to: `[Template Name] - [Employee Name]`
- The "Employee" global filter is automatically set to the current employee
- All linked pivot tables and lists show data ONLY for this employee
- The report is saved and linked to the employee

### Editing a Report

- Users can modify their reports (add data, change formatting, etc.)
- Changes are saved automatically
- The original template remains unchanged

## Permissions

- **HR Officers**: Can create and edit reports, can read templates
- **HR Managers**: Can create, edit, and delete templates and reports

## Troubleshooting

**Problem**: Report shows all attendance records instead of just the current employee
- **Solution**: The pivot/list is not linked to the Global Filter. Edit the template and link the filter as described in Step 3.

**Problem**: Error "No Spreadsheet Template found"
- **Solution**: Assign a template to either the Employee or the Job Position.

**Problem**: Smart button shows "0" but I created a report
- **Solution**: The report might be linked to a different employee. Check the report's name or create a new one.

**Problem**: Can't see the "Employee Templates" tab in "Insert in Spreadsheet"
- **Solution**: Make sure the module is installed and you've created at least one template.

**Problem**: Pivot table shows "No data" even though the employee has records
- **Solution**: Check that you've linked the correct field in the Global Filter. For example, if using `hr.attendance`, you must link `employee_id`, not `id`.

## Example Use Cases

1. **Employee Performance Dashboard**: Track KPIs, attendance, and productivity metrics
2. **Attendance Summary**: Monitor check-in/check-out times, total hours worked
3. **Leave Analysis**: Analyze time off requests, balances, and patterns
4. **Contract Overview**: Review contract details, salary history, and benefits

## Credits

**Author**: [Ganemo](https://www.ganemo.co)

This module was developed by Ganemo to provide advanced spreadsheet reporting capabilities for Odoo employees.

## Support

For issues or questions, contact your system administrator or Ganemo support at www.ganemo.co
