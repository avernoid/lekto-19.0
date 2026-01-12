# **Project Task Photo Evidence**

<img src="static/description/banner.png" width="100%" alt="Banner">

## Description

This module enables the capture of photo evidence for project tasks with **automatic geolocation validation**. It is designed for field service operations where proof of work and location verification are critical. Unlike standard attachments, this module enforces business rules (Min/Max photos) and creates a shareable, professional evidence report for your customers.

## Key Features

*   **Automatic Geolocation**: Captures GPS coordinates (Latitude/Longitude) instantly when the photo wizard is opened.
*   **Enforced Business Rules**: Configure products to require a minimum quantity of photos (Warning) and a maximum limit (Blocking Error).
*   **Public Share Link**: Generate a secure, read-only URL for clients to view the evidence dashboard without logging in.
*   **Internal PDF Report**: Consolidated PDF report accessible via Smart Button on the Project.
*   **Integrity Protection**: Read-only coordinate fields to ensure data authenticity.

## Requirements

*   **Odoo Version**: 19.0
*   **Dependencies**: `project`, `sale_management`, `website`, `portal`
*   **Browser**: Requires **HTTPS** (secure context) or localhost to access the Geolocation API.

## Configuration

### 1. Product Rules
1.  Go to **Sales > Products**.
2.  Select a service product (e.g., "Field Service").
3.  In the **Sales** tab, scroll to the **Task Evidence** group.
4.  Enable **Evidence Required**.
5.  Set **Minimum Evidence** (triggers yellow warning) and **Maximum Evidence** (triggers red validation error).

### 2. Project Privacy (For Sharing)
To use the **"Generate Share Link"** feature:
1.  Go to **Project > Configuration > Settings** (or the Project Form).
2.  Set **Visibility** to **"Invited internal users and portal users"** or **"Public"**.
3.  *Note: If set to "Invited internal users only", the Share Link button will be disabled with a warning.*

## Usage

### Field Worker Flow
1.  Open the assigned **Task** on a mobile device or desktop.
2.  Navigate to the **"Photo Evidence"** page.
3.  Click the **"📷 Add Photo"** button (Camera Icon).
4.  **Important:** Click **"Allow"** when the browser requests Location Access.
5.  Upload the photo. The system silently records the Latitude and Longitude.

### Reporting Flow
1.  **Internal Review:** On the **Project Form**, click the **"Internal Report"** smart button to download the PDF.
2.  **Customer Sharing:**
    *   On the **Project Form**, click **"Generate Share Link"**.
    *   The **"Evidence Report URL"** field will appear.
    *   Copy the URL and send it to the client.
    *   *To stop sharing, click "Revoke Link".*

## Troubleshooting

*   **"Location Stuck on Searching..."**: This usually means the browser denied permission or the site is not on HTTPS.
*   **"Generate Share Link button is missing"**: Check your Project Visibility settings. It demands Portal or Public access.

## Credits

**Author**: [Ganemo](https://www.ganemo.co)
**Maintainer**: Ganemo
