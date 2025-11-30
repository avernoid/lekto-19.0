# Project Spreadsheet Report

Generate dynamic, filterable spreadsheet reports for your Projects.

## Features

- **Smart Button Integration**: Access reports directly from any Project with a single click
- **Template Management**: Create reusable spreadsheet templates with pre-configured charts and pivot tables
- **Automatic Filtering**: Reports are automatically filtered to show only data for the current project
- **Flexible Configuration**: Assign default templates to Partners or Project Tags
- **Wizard Integration**: Insert charts and pivot tables from any Odoo view into your templates

## Installation

1. Install the module from Apps menu
2. The module will add a "Spreadsheet" smart button to all Project forms
3. A new menu "Project Spreadsheet Templates" will appear under Project > Configuration

## Configuration Guide

### Step 1: Create a Template

1. Go to **Project > Configuration > Project Spreadsheet Templates**
2. Click **Create** (or add a new line in list view)
3. Enter a descriptive name (e.g., "Project Performance", "Task Analysis")
4. Click **Save**
5. Click the **Create Spreadsheet** button

### Step 2: Design Your Template

When the spreadsheet editor opens, you'll see a blank spreadsheet with a **Global Filter** already configured:

#### Understanding the Global Filter

- **Filter Name**: "Project" (visible in the Filters panel on the right)
- **Purpose**: This filter will automatically populate with the current project when a user opens a report
- **Status**: Initially empty (this is normal for templates)

#### Adding Data to Your Template

**Option A: Insert a Pivot Table**

1. Click **Insert** in the top menu
2. Select **Pivot Table**
3. Choose a model related to projects:
   - `project.task` (Tasks) - for task-level details
   - `account.analytic.line` (Timesheet Entries) - for time tracking
   - `project.milestone` (Milestones) - for milestone tracking
   - `res.users` (Users) - for team analysis
4. Configure your pivot:
   - **Rows**: Add dimensions (e.g., Task, User, Stage, Date)
   - **Columns**: Add groupings (e.g., Priority, Tag, Milestone)
   - **Measures**: Add metrics (e.g., Hours Spent, Remaining Hours, Progress)
5. Click **Insert**

**Option B: Insert a List**

1. Click **Insert** > **List**
2. Choose a model (e.g., `project.task`)
3. Select the fields you want to display
4. Click **Insert**

**Option C: Insert from Another View**

1. Navigate to any Odoo view (e.g., Project > Tasks)
2. Apply filters or groupings as needed
3. Click the **Favorites** menu (⭐)
4. Select **Insert in Spreadsheet**
5. Choose the **Project Templates** tab
6. Select your template
7. The chart/list will be inserted

#### Step 3: Link Data to the Global Filter (CRITICAL)

After inserting a pivot table or list, you MUST link it to the Global Filter so it filters by the current project:

**For Pivot Tables:**

1. Click on the pivot table in your spreadsheet
2. In the right panel, find the **Filters** section
3. You'll see the "Project" filter listed
4. Click **Edit** (pencil icon) next to the Project filter
5. In the popup, configure the relationship:
   - **Field to filter**: Select the field that links to `project.project`
     - If using `project.task`: Select `project_id`
     - If using `account.analytic.line`: Select `project_id`
     - If using `project.milestone`: Select `project_id`
     - If using other models: Select the appropriate Many2one field that links to project
6. Click **Confirm**
7. The filter icon should now show as "linked" (🔗)

**For Lists:**

1. Click on the list in your spreadsheet
2. Follow the same steps as pivot tables to link the "Project" filter

**Important Notes:**
- If you don't link the filter, the report will show ALL data from the database (not filtered by project)
- You can verify the link by checking if the filter icon shows a chain link (🔗)
- You can link multiple pivot tables/lists to the same filter

#### Step 4: Add Charts and Formatting

1. **Create Charts**: Select your pivot data > Insert > Chart
2. **Add Formulas**: Use standard spreadsheet formulas (SUM, AVERAGE, COUNTIF, etc.)
3. **Format**: Apply colors, borders, fonts to make it visually appealing
4. **Add Headers**: Include titles, company logo, project details, etc.
5. **Add KPIs**: Calculate metrics like:
   - Total tasks
   - Completion percentage
   - Average task duration
   - Hours spent vs. planned

#### Step 5: Save Your Template

1. Click **Save** in the spreadsheet editor
2. Close the editor
3. Your template is now ready to use!

### Step 6: Assign the Template

You can assign templates at two levels (priority order):

**Option A: Assign to a Partner (Highest Priority)**

1. Go to **Contacts**
2. Open a Partner (Customer)
3. Find the field **Project Spreadsheet Template**
4. Select your template
5. Save

**Option B: Assign to Project Tags**

1. Go to **Project > Configuration > Tags**
2. Open a Tag (e.g., "Development", "Consulting")
3. Find the field **Spreadsheet Template**
4. Select your template
5. Save

**Template Selection Logic:**
- When a user clicks the Spreadsheet button on a Project:
  1. First checks if the Partner has a template assigned → Uses it
  2. If not, checks if any of the Project's Tags have a template → Uses the first one found
  3. If neither has a template → Shows an error with instructions

## Usage

### Creating a Report

1. Open any **Project**
2. Click the **Spreadsheet** smart button (shows count of existing reports)
3. **First time**: A new report is created from the template and opens automatically
4. **Subsequent times**: The existing report opens

### What Happens Automatically

- The report is created by copying the template
- The report name is set to: `[Template Name] - [Project Name]`
- The "Project" global filter is automatically set to the current project
- All linked pivot tables and lists show data ONLY for this project
- The report is saved and linked to the project

### Editing a Report

- Users can modify their reports (add data, change formatting, etc.)
- Changes are saved automatically
- The original template remains unchanged

## Permissions

- **Project Users**: Can create and edit reports, can read templates
- **Project Managers**: Can create, edit, and delete templates and reports

## Troubleshooting

**Problem**: Report shows all tasks instead of just the current project
- **Solution**: The pivot/list is not linked to the Global Filter. Edit the template and link the filter as described in Step 3.

**Problem**: Error "No Spreadsheet Template found"
- **Solution**: Assign a template to either the Partner or at least one Project Tag.

**Problem**: Smart button shows "0" but I created a report
- **Solution**: The report might be linked to a different project. Check the report's name or create a new one.

**Problem**: Can't see the "Project Templates" tab in "Insert in Spreadsheet"
- **Solution**: Make sure the module is installed and you've created at least one template.

## Example Use Cases

1. **Task Performance**: Track task completion rates, time spent, and user productivity
2. **Milestone Tracking**: Monitor milestone progress, deadlines, and deliverables
3. **Time Analysis**: Analyze timesheet entries, billable vs. non-billable hours
4. **Resource Planning**: Compare planned vs. actual hours, identify bottlenecks
5. **Client Reporting**: Generate professional reports for customers with project metrics

## Support

For issues or questions, contact your system administrator or Ganemo support at www.ganemo.co
