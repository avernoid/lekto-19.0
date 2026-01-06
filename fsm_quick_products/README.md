# FSM Quick Products Button

This module enhances the Field Service Management (FSM) experience by providing a direct-access button to the products and materials list from the task form header.

## Features

- **Direct Accessibility**: Adds dedicated buttons for products (box icon) and Sales Orders (shopping cart icon) in a compact section just below the task header.
- **Context-Aware Visibility**: The Sales Order icon automatically hidden if no Sale Order is linked to the task, preventing UI clutter.
- **Mobile Optimized**: Ensures these critical buttons are always visible on mobile devices, preventing them from being hidden inside Odoo's native "lightning" (⚡) or "more" (⋮) menus.
- **Seamless Integration**: Uses Odoo's native color palette and design patterns for a non-intrusive look.
- **Configurable Visibility**: Use Odoo Studio or project settings to toggle the products button's visibility via the `show_fsm_products_button` field on the task.

## Configuration

1. Install the module.
2. Navigate to **Field Service > Tasks**.
3. Open any task. The button will appear automatically if the task belongs to a project where materials are allowed.
4. (Optional) Use Odoo Studio to hide the button by toggling the "Show FSM Products Button" boolean field.

## Usage

- **On Mobile**: The button appears as a small box icon at the top of the form, allowing technical field workers to record materials with a single tap.
- **On Desktop**: Provides a redundant, highly visible shortcut next to the standard smart buttons.

## Technical Details

- **Model Extended**: `project.task`
- **View Inherited**: `project.view_task_form2`
- **Dependencies**: `project`, `sale`, `industry_fsm`, `industry_fsm_stock`

---
**Author**: [Ganemo](https://www.ganemo.co)
