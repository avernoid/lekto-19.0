# **Project Task Photo Evidence**

<img src="static/description/banner.png" width="100%" alt="Banner">

## 🌟 Overview

The **Project Task Photo Evidence** module transforms Odoo into a robust field-verification tool. It enables task assignees to capture and document work progress through a secure, "app-like" mobile interface. 

Designed for **High-Reliability Operations**, it enforces business rules (min/max photos), strictly captures GPS coordinates (Proof of Location), and provides professional reporting for stakeholders.

---

## 🚀 Key Features

### 📍 Smart Evidence & GPS
*   **Tamper-Proof Geolocation**: Automatically captures **Latitude & Longitude** from the device's GPS sensor at the exact moment of upload. These fields are read-only to ensure integrity.
*   **Multi-Product Evidence**: A single task can require photos for multiple different items (e.g., "Installation Photos" + "Cleanup Photos").
*   **Metadata Rich**: Every photo stores user, timestamp, and location data.

### 📱 Premium Mobile Experience (PWA)
*   **App-Like Interface**: Runs inside the **Portal App Launcher**, providing a distraction-free, native-feel environment.
*   **One-Handed Use**: Bottom navigation bar for easy filtering by Project, Product, or Tag.
*   **Installable**: Workers can add the app to their home screen (Android/iOS) for instant access.

### 🛡️ Business Logic Enforcement
*   **Min/Max Constraints**: Define "Minimum Photos" (to block completion if missing) and "Maximum Photos" (to prevent storage waste).
*   **Real-Time Validation**: The interface provides immediate visual feedback (Red/Yellow/Green indicators) on evidence status.

### 📊 Reporting & Sharing
*   **Public Share Link**: Generate a secure, read-only URL for clients to view real-time progress without logging in.
*   **PDF Reports**: One-click generation of professional evidence reports for internal or external use.

---

## ⚙️ Configuration Guide

### 1. Defining Evidence Rules
Control exactly what your field team needs to capture.

| Step | Action |
| :--- | :--- |
| **1. Product Setup** | Go to **Sales > Products**. Open a service product (e.g., "Installation"). |
| **2. Enforce** | in the **Sales Tab**, check **"Evidence Required"**. |
| **3. Set Limits** | Define **Min Qty** (Required count) and **Max Qty** (Hard limit). |

### 2. Automating the Flow
Link sales to tasks seamlessly.

1.  Create a **Sale Order** with the configured Service Product.
2.  **Confirm** the Order. Odoo automatically generates a **Project Task**.
3.  The Task inherits the **Evidence Rules** from the product line.
    *   *Example: Sale Order has 5 units. Product requires 2 photos per unit. Task requires 10 photos total.*

### 3. Enabling External Sharing
To use the "Share Link" feature, ensure your Project Privacy is correct.

*   **Navigate**: Project > Configuration > Settings.
*   **Setting**: Set Visibility to **"Invited internal users and portal users"** (or Public).
*   *Note: "Invited internal users only" disables sharing.*

---

## 🔄 Workflow Walkthrough

### 👷 For Field Workers
1.  **Open App**: Launch "Photos" from the Portal Home.
2.  **Select Task**: Tap a card. Red indicators show missing evidence.
3.  **Capture**: Tap the camera icon. 
    *   *Constraint*: You MUST allow **Location Access**.
4.  **Finalize**: Once the indicator turns Green, click **"Finalize Task"** to mark it as Done.

### 💼 For Managers
1.  **Review**: Open the Task in the backend. Go to the **Evidence** tab.
2.  **Map View**: Check the `Map` link to verify the GPS location on Google Maps.
3.  **Report**: Click **"Internal Report"** to download the PDF.

---

## 🛠️ Technical Requirements

*   **HTTPS Required**: Modern browsers **block** Geolocation and PWA installation on insecure (HTTP) connections. You must use SSL.
*   **Dependency**: This module requires `portal_app_launcher` to function.

---

## ❓ Troubleshooting

**Q: The GPS location says "Searching..." forever.**
*   **A**: Ensure you are on **HTTPS**. Check that the browser has permission to access Location.

**Q: I can't upload more photos.**
*   **A**: You have likely hit the **Max Qty** limit defined on the Product. Delete an old photo or increase the limit.

**Q: The "Share Link" button is grayed out/warning.**
*   **A**: Your **Project Visibility** is too strict. Change it to allow Portal Users.

---

## 💳 Credits

**Author**: [Ganemo](https://www.ganemo.co)  
**Maintained by**: Fernando Pastor  
**License**: Odoo Proprietary License v1.0
