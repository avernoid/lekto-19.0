# Auto Cancel FSM Task

## Description

This module automatically marks tasks as done if they exceed a configured antiquity threshold relative to their end date. Tasks that are automatically completed are flagged as "Not Executed".

## Features

- **Antiquity in Hours**: Configure a threshold (in hours) at the project level to determine when tasks should be automatically marked as done.
- **Automatic Task Completion**: A scheduled action runs daily to check and complete tasks that meet the criteria.
- **Manual Execution**: A button on the project form allows manual execution of the auto-completion logic for tasks in that specific project.
- **Not Executed Flag**: Tasks that are automatically completed are marked with a "No Ejecutada" (Not Executed) boolean field, visible only when the task is in the 'done' state.

## Configuration

1. Install the module.
2. Navigate to a Project.
3. Set the "Antiguedad en Horas" (Antiquity in Hours) field to the desired threshold (e.g., 24 for 24 hours).
4. The "Run Manually" button will appear next to the field when the value is greater than zero.

## Usage

### Automatic Execution
The scheduled action runs once per day and processes all tasks that meet the following criteria:
- State is not 'done' or 'canceled'
- Task is not archived
- Project's "Antiguedad en Horas" is not zero
- Task's end date is more than X hours in the past (where X is the project's antiquity threshold)

### Manual Execution
Click the "Run Manually" button on a project to immediately process tasks for that specific project.

## Technical Details

- **Models Extended**: `project.project`, `project.task`
- **New Fields**:
  - `project.project.antiquity_in_hours` (Float)
  - `project.task.not_executed` (Boolean)
- **Scheduled Action**: `ir_cron_auto_cancel_fsm_tasks` (runs daily)

## Author

Developed for Odoo 19.0+

## License

LGPL-3
