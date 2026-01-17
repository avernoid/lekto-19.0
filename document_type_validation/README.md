# Document Type Validation

<img src="static/description/banner.png" width="100%" alt="Banner">

**Author**: [Ganemo](https://www.ganemo.com)

## Overview

This module extends Odoo's localization capabilities by providing advanced validation rules for **L10n Latam Identification Types**. It ensures that VAT/RUC/DNI numbers entered in `res.partner` records strictly adhere to the formats defined by local regulations.

## Key Features

-   **Length Validation:** Enforce "Exact" or "Maximum" character limits.
-   **Type Validation:** Restrict input to "Numeric" or "Alphanumeric".
-   **Custom Regex:** Define powerful custom Regular Expressions (e.g., `^[A-Z]{3}-[0-9]{3}$`) for complex document formats.
-   **Real-time Feedback:** Instant visual alerts in the Partner form if validation fails.
-   **Save Prevention:** Blocks saving of records with invalid identification numbers to maintain data integrity.

## Functionality

1.  **Configuration:** Go to `Contacts > Configuration > Identification Types` and set up the rules for each document type.
2.  **Validation:** When a user enters a VAT number, the system checks:
    -   Is it the correct length?
    -   Does it contain only allowed characters?
    -   Does it match the configured Regex pattern?

If any check fails, a clear error message is displayed and the record cannot be saved.

## License

This module is licensed under the **Odoo Proprietary License v1.0 (OPL-1)**.
See `LICENSE` file for full copyright and licensing details.

## Support

For support and commercial inquiries, visit [ganemo.co](https://www.ganemo.co) or contact us at leads@ganemo.com.
