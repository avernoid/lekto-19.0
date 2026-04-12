**Openclaw Connector**

<img src="static/description/banner.png" width="100%" alt="Banner">

## Overview

The **Openclaw Connector** module adds a dedicated Openclaw configuration section to the **Universal Connector** settings page in Odoo 19. It allows you to configure and store your Openclaw API credentials (API URL and API Key) from a single, centralized location.

Once configured, any module in the system can retrieve these credentials programmatically to interact with the Openclaw API.

## Requirements

- Odoo 19 (Enterprise, Odoo.SH, or Ganemo Online)
- **Universal Connector** module (`universal_connector`) must be installed

## Installation

1. Place the `openclaw_connector` folder in your Odoo addons path.
2. Update the Apps list: **Settings > Apps > Update Apps List**.
3. Search for **Openclaw Connector** and click **Install**.

## Configuration

1. Navigate to **Settings > Connectors**.
2. Locate the **Openclaw** block within the Universal Connector settings page.
3. Fill in the following fields:
   - **API URL**: The base URL of your Openclaw API endpoint (e.g., `https://api.openclaw.io`). This is the root URL that all API requests will be sent to. Do not include trailing slashes or specific endpoint paths.
   - **API Key**: The secret key used to authenticate requests with the Openclaw API. This value is masked in the UI for security. You can obtain this key from your Openclaw account dashboard.
4. Click **Save** to persist the credentials.

## How Other Modules Access the Credentials

The credentials are stored as Odoo system parameters (`ir.config_parameter`). Any module can retrieve them using:

```python
api_url = self.env['ir.config_parameter'].sudo().get_param('openclaw_connector.api_url')
api_key = self.env['ir.config_parameter'].sudo().get_param('openclaw_connector.api_key')
```

### System Parameter Keys

| Key | Description |
|---|---|
| `openclaw_connector.api_url` | Base URL of the Openclaw API |
| `openclaw_connector.api_key` | Secret API authentication key |

## Multi-Language Support

This module includes translations for **English** and **Spanish** (es).

## License

OPL-1

**Author**: [Ganemo](https://www.ganemo.com)
