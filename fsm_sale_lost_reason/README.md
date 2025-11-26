# FSM Sale Lost Reason

## Overview

This module enhances Field Service Management by requiring technicians to specify a reason when completing tasks without generating a confirmed sale order. This feature helps businesses understand why sales opportunities are lost during field service visits.

## Features

- **Project-Level Configuration**: Enable the "Use Lost Reason" setting on specific FSM projects
- **Conditional Requirement**: Lost reason is only required when marking a task as done without a confirmed sale order
- **User-Friendly Wizard**: Simple popup prompts users to select from predefined lost reasons
- **Seamless Integration**: Works alongside existing FSM workflows without disrupting native Odoo functionality
- **Reporting & Analysis**: Lost reasons are stored on tasks for easy reporting and trend identification

## Configuration

1. Navigate to **Field Service > Configuration > Projects**
2. Select or create an FSM project
3. In the project settings, enable **Allow Material** (if not already enabled)
4. Enable **Use Lost Reason**
5. Configure lost reason options in **Sales > Configuration > Lost Reasons**

## Usage

When a technician attempts to mark a task as done:

1. If the project has "Use Lost Reason" enabled
2. AND no confirmed sale order exists for the task
3. A wizard will appear requiring the selection of a lost reason
4. The task can only be completed after selecting a reason

The lost reason is then stored on the task for reporting and analysis purposes.

## Technical Details

### Dependencies

- `project`
- `sale`
- `sale_lost_reason`
- `industry_fsm_sale`

### Models Extended

- `project.project`: Added `use_lost_reason` boolean field
- `project.task`: Added `lost_reason_id` field and validation logic

### New Models

- `project.task.lost.reason.wizard`: Transient model for capturing lost reasons

## Credits

### Authors

- Ganemo

### Maintainer

This module is maintained by Ganemo.

For support and more information, please visit [https://www.ganemo.co](https://www.ganemo.co)
