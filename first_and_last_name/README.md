# First and Last Name Details

<img src="static/description/banner.png" width="100%" alt="Banner">

Separate and manage individual contact names with precision. This module adds dedicated fields for first names and surnames (paternal and maternal), ensuring clean data organization and legal compliance for businesses dealing with complex naming conventions.

## Features

- **Structured Identification**: Adds specific fields for First Name, Paternal Surname, and Maternal Surname.
- **Smart Visibility**: Fields are context-aware and automatically hidden for company/entity contacts to keep the form clean.
- **Header Integration**: Seamlessly integrated into the contact header (right below the main name), ensuring high visibility without conflicting with address blocks or localization modules.
- **Data Integrity**: Keeps detailed name components independent from Odoo's standard `name` field, allowing for flexible reporting and display.
- **Multi-Language Support**: Fully internationalized with native English base and complete Spanish translation included.
- **Odoo 19 Ready**: Built and tested specifically for Odoo 19 environments, including support for Odoo.sh and multi-company setups.

## Visibility Logic

The "Name Details" section is designed for **Individual** contacts only. If a contact is marked as a **Company**, the fields will be hidden to prevent unnecessary clutter and data entry errors.

## Installation

1. Go to **Apps**.
2. Search for `first_and_last_name`.
3. Click **Activate**.

## Usage

1. Open any **Contact** or create a new one.
2. Select **Individual** as the contact type.
3. You will see the **Name Details** fields immediately below the main Name field in the header.
4. Fill in the breakdown of the name.
5. Save the contact. The standard Odoo `name` field remains independent, allowing you to manually set the display name as needed.

## Configuration

No additional configuration is required. The module works immediately after installation.

---

**Author**: [Ganemo](https://www.ganemo.com)
**License**: OPL-1
**Category**: Extra Tools