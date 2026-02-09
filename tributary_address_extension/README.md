# **Tributary Address Extension**

<img src="static/description/banner.png" width="100%" alt="Banner">

## Description

This module extends the contact form (`res.partner`) to include the **Establishment Annex** field, which is essential for the Peruvian localization.

In Peru, companies often have multiple branches or establishments, each identified by a unique 4-digit code assigned by SUNAT (e.g., `0001`, `0002`). This code is mandatory for:
- Electronic Invoicing (CPE).
- Electronic Books (PLE).
- Official tax compliance.

This module ensures that you can register this code correctly for each contact or address.

## Requirements

- Odoo 19.0
- This module relies on `base`. It is designed to work within the Peruvian Localization ecosystem.

## Configuration

No special configuration is required in the settings. The field is automatically added to the contact form.

However, the field is **conditional**:
- It will **only appear** if the contact's **Country** is set to **Peru**.

## Usage

1. Go to the **Contacts** app.
2. Create a new contact or open an existing one.
3. In the address section, ensure the **Country** field is set to **Peru**.
4. You will see a new field labeled **Establishment Annex**.
5. Enter the 4-digit code assigned by SUNAT (e.g., `0001`).
6. Save the contact.

## Credits

**Author**: [Ganemo](https://www.ganemo.com)
**Maintainer**: Ganemo
