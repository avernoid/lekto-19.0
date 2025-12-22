# Button Control Per User

[![License: OPL-1](https://img.shields.io/badge/License-OPL--1-blue.svg)](https://www.ganemo.com)
[![Version: 19.0.1.0.0](https://img.shields.io/badge/Version-19.0.1.0.0-purple.svg)]()

Empower your Odoo administrators with granular control over the user interface. **Button Control Per User** allows you to hide standard interface buttons (like New, Edit, Delete, Export, etc.) on a per-user basis, without modifying security groups or backend permissions.

## Key Features

*   **Granular Visibility Control**: Hide specific buttons for specific users.
*   **Context-Aware Rules**: Apply rules only in certain business contexts (e.g., only in Field Service, only for Sales, or only when a record is Read-only).
*   **Comprehensive Coverage**: Supports Form, List, and Kanban views.
*   **Universal Button Matcher**: Intelligent matching for standard header buttons (Cancel, Validate) across multiple languages.
*   **Zero Impact on Native Behavior**: Users without rules experience 100% native Odoo functionality.
*   **Odoo 19 Optimized**: Built with modern OWL patterns and non-invasive patching.

## Supported Buttons

The module currently supports controlling the following standard actions:
*   **Create / New**
*   **Edit**
*   **Delete**
*   **Archive / Unarchive**
*   **Duplicate**
*   **Export**
*   **Import**
*   **Cancel** (intelligent name/label matching)
*   **Validate** (intelligent name/label matching)

## Installation

1.  Copy the module folder to your Odoo addons directory.
2.  Update the Apps list in Odoo.
3.  Search for **Button Control Per User** and click **Install**.

## Configuration

1.  Navigate to **Settings -> Users & Companies -> Users**.
2.  Select the user you wish to configure.
3.  Go to the **Interface Rules** tab.
4.  Click **Add a line** and define your rules:
    *   **Model**: Specify a model (e.g., `project.task`) or leave empty for "All Models".
    *   **View Type**: Choose between Form, List, or Kanban.
    *   **Button**: Select the action to hide.
    *   **Business Context**: Choose when the rule should be active (Any, Field Service, From Sales, or Read-only).
5.  Save the user record.

## Technical Documentation

### How it works
The module uses a dedicated OWL service (`button_control`) that loads rules on session start. It patches core Odoo controllers and components (FormController, ListController, KanbanRecord, and ViewButton) to intercept the rendering logic and apply the visibility rules client-side.

### Language Support
Rules for "Cancel" and "Validate" buttons prioritize technical internal names and attributes (like `special="cancel"`), making them reliable even if the user interface is translated into different languages.

### Performance
Evaluation happens in-memory on the client side. No recurring database calls are made during navigation, ensuring zero impact on UI responsiveness.

## Credits

**Author**: [Ganemo](https://www.ganemo.co)

For support, custom implementations or inquiries, visit our website or contact us at leads@ganemo.co.
