# Project Task Spreadsheet Report

Generate dynamic, filterable spreadsheet reports for your Project Tasks.

## Features

- **Smart Button Integration**: Access reports directly from any Task with a single click
- **Template Management**: Create reusable spreadsheet templates with pre-configured charts and pivot tables
- **Automatic Filtering**: Reports are automatically filtered to show only data for the current task
- **Flexible Configuration**: Assign default templates to Partners, Projects, or Task Tags
- **Wizard Integration**: Insert charts and pivot tables from any Odoo view into your templates

## Installation

1. Install the module from Apps menu
2. The module will add a "Spreadsheet" smart button to all Task forms
3. A new menu "Task Spreadsheet Templates" will appear under Project > Configuration

## Template Priority Logic

When clicking the Spreadsheet button on a task, the system searches for a template in this order:
1. **Partner Template** (highest priority)
2. **Project Template**
3. **Task Tags Template** (first tag with a template)

## Configuration Guide

### Step 1: Create a Template

1. Go to **Project > Configuration > Task Spreadsheet Templates**
2. Click **Create** (or add a new line in list view)
3. Enter a descriptive name (e.g., "Task Performance", "Time Tracking")
4. Click **Save**
5. Click the **Create Spreadsheet** button

### Step 2: Design Your Template

The spreadsheet editor opens with a **Global Filter** already configured for "Task".

#### Adding Data

Insert pivot tables or lists using models like:
- `project.task` - Task details
- `account.analytic.line` - Timesheet entries
- `project.milestone` - Milestones
- `mail.message` - Task communications

### Step 3: Link Data to Global Filter (CRITICAL)

After inserting pivots/lists, link them to the "Task" filter:

1. Click on the pivot table
2. In the right panel, find **Filters**
3. Click **Edit** next to the "Task" filter
4. Select the field that links to `project.task`:
   - For `account.analytic.line`: Select `task_id`
   - For other models: Select the appropriate Many2one field
5. Click **Confirm**

### Step 4: Assign the Template

**Option A: Assign to Partner**
1. Go to **Contacts** > Open a Partner
2. Set **Task Spreadsheet Template**

**Option B: Assign to Project**
1. Go to **Project** > Open a Project
2. Set **Task Spreadsheet Template**

**Option C: Assign to Task Tags**
1. Go to **Project > Configuration > Tags**
2. Open a Tag
3. Set **Task Spreadsheet Template**

## Usage

1. Open any **Task**
2. Click the **Spreadsheet** smart button
3. Report opens (creates new if first time)

## Permissions

- **Project Users**: Can create/edit reports, read templates
- **Project Managers**: Full control over templates and reports

## Support

For issues or questions, contact your system administrator or Ganemo support at www.ganemo.co
