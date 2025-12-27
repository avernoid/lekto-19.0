# Attendance Geolocation Control

[![License: OPL-1](https://img.shields.io/badge/License-OPL--1-purple.svg)](https://www.ganemo.co/license)

The **Attendance Geolocation Control** module for Odoo 19 empowers HR managers to enforce strict attendance policies by validating the physical location of employees during check-in and check-out. By integrating high-precision geofencing and GPS accuracy filtering, it transforms Odoo's native attendance system into a robust, audit-ready security tool.

## Key Features

- **Advanced Geofencing**: Define precise allowed radii (in meters) for every workstation or job site.
- **Location Determination**: Intelligent priority logic (Exceptional Location > Weekday Location > Default) ensures the correct validation target is always used.
- **GPS Accuracy Filtering**: Classify and filter location signals (High, Medium, Low) to prevent fraudulent "proxy" check-ins or spoofed coordinates.
- **Flexible Enforcement Policies**: Configure how the system responds to violations:
  - **Block**: Prevent the attendance action entirely.
  - **Allow with Reason**: Require the employee to provide a mandatory justification.
  - **Allow and Mark**: Record the violation but allow the action for later auditing.
- **Integrated Backend Auditing**: New fields in attendance records for distance, status, and reliability badges.
- **Interactive Reason Dialog**: Smart dialog that prompts employees for a justification only when required by policy.
- **Multilingual Support**: Full Spanish translations included.
- **Zero-Disruption UX**: Patched Odoo's native systray button to capture geolocation data without adding new steps for the employee.

## Configuration

1. **Job Positions (Policies)**:
   - Go to **Recruitment > Configuration > Job Positions**.
   - Open a job position and navigate to the **Geolocation Control** tab.
   - Enable "Attendance Geo-Enforced".
   - Define the allowed **Radius** (e.g., 100m).
   - Configure policies for "Out of Location", "Low Accuracy", and "GPS Unavailable".

2. **Work Locations (Coordinates)**:
   - Go to **Attendances > Configuration > Work Locations**.
   - Open a location and set the **Geofencing Data** (Latitude / Longitude).
   
3. **Company Defaults**:
   - Go to **Settings > Companies**.
   - Set global fallback policies under the **Attendance Geolocation Defaults** tab.

4. **Employee Mapping**:
   - Ensure employees have assigned work locations for their workdays (using Odoo's `hr_homeworking` logic).

## Usage

- **Employees**: Simply click the 'Check In' or 'Check Out' button in the Odoo top menu. The module automatically fetches coordinates and validates them in the background.
- **HR Managers**: Audit attendance records in **Attendances > Attendances**. Use the list and form views to see the `Location Status` and `Reliability` badges.

## Technical Details

- **Distance Calculation**: Uses the Haversine formula for spherical distance accuracy.
- **Frontend**: Lightweight JS patch to Odoo's native `ActivityMenu` component.
- **Backend**: Strict validation hooks on `hr.attendance` creation and updates.

---

**Author**: [Ganemo](https://www.ganemo.com)  
**Maintenance**: This module is maintained by Ganemo.  
**Contact**: [leads@ganemo.com](mailto:leads@ganemo.com)

For more information, visit [www.ganemo.com](https://www.ganemo.com)
