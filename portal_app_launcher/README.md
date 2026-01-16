# **Portal App Launcher**

<img src="static/description/banner.png" width="100%" alt="Banner">

## 🌟 Overview

The **Portal App Launcher** is a foundational module that transforms the standard Odoo Portal into a high-performance, mobile-first app dashboard. It provides users with a clean, navigable interface optimized for "one-hand" operation, making it ideal for field services, logistics, and on-the-go client portals.

---

## 🚀 Key Features

### 📱 App-Like Experience
*   **Grid Navigation**: A simple, intuitive 3x3 grid (or list) of available apps.
*   **PWA Ready**: Built-in Progressive Web App (PWA) manifest and service worker configuration.
*   **Home Screen Install**: Prompt users to "install" the portal as a smartphone app.

### 🛠️ Developer Friendly
*   **Modular Architecture**: Easily register new portal apps from any module using the `portal.app` model.
*   **Custom Icons**: Support for FontAwesome and custom SVG icons for each app.
*   **Sequential Logic**: Control the order of apps on the dashboard directly from the configuration.

### 🧩 Seamless Integration
*   **Breadcrumb Optimization**: Intelligent navigation that returns users to the launcher after completing tasks.
*   **One-Hand UX**: Bottom navigation bar for core shortcuts.

---

## ⚙️ Configuration

1.  **Install the Module**: Go to Apps and search for `portal_app_launcher`.
2.  **Configure Apps**: Navigate to **Website > Configuration > Portal Apps**.
3.  **App Setup**:
    *   **Name**: The label shown to the user.
    *   **Icon**: FontAwesome class (e.g., `fa-camera`).
    *   **URL**: The portal route to redirect to.
    *   **Sequence**: Lower numbers appear first.
    *   **Is Published**: Only published apps are visible.

---

## 🛠️ Technical Details

*   **PWA Assets**: The module serves a `manifest.json` at `/portal/manifest.json`.
*   **Routing**: The default portal home (`/my`) is enhanced to display the launcher.
*   **CSS Architecture**: Uses a specific `portal_launcher.css` for isolation and performance.

---

## 💳 Credits

**Author**: [Ganemo](https://www.ganemo.co)  
**Industry**: Specialized in Enterprise Odoo Localizations and Operational Excellence.  
**Support**: [leads@ganemo.com](mailto:leads@ganemo.com)
