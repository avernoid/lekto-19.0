# **Portal App Launcher**

<img src="static/description/banner.png" width="100%" alt="Banner">

## 🌟 Overview

The **Portal App Launcher** is a foundational module that transforms the standard Odoo Portal into a high-performance, mobile-first **Progressive Web App (PWA)** dashboard. 

It is designed with a **"Hyper-Optimized" philosophy**: eliminating complex configurations for end-users while ensuring professional, harmonized aesthetics through a **Hybrid Theming Engine**. Whether for field service drivers, logistics operators, or client portals, this launcher provides a native-app feel directly in the browser.

---

## 🚀 Key Features

### 🎨 Hybrid Theming Engine
We use a dual-layer approach to ensure the app looks perfect on every device:
*   **CSS Themes**: Rich, gradient-based styling with Glassmorphism effects (e.g., Ocean Blue, Sunset Orange) injected directly into the DOM.
*   **Native Sync**: The backend automatically calculates the perfect hex codes for the **Browser Status Bar** and **Splash Screen**, ensuring the browser UI matches the app design.

### 📱 Full PWA Capabilities
*   **One-Click Install**: Built-in "Install App" button that triggers the native Android/iOS installation prompt.
*   **Smart Manifest**: Automatically generates `manifest.webmanifest` based on the active app's metadata.
*   **Offline Ready**: Service workers (if configured) allow the launcher to load instantly even on flaky networks.

### 🔒 Enterprise-Grade Access
*   **Granular Permissions**: Limit visibility of specific apps to specific User Groups (e.g., "Drivers" only see "Deliveries", "Managers" see "Reports").
*   **Secure Routing**: Prevents unauthorized access to app routes if the user doesn't belong to the allowed group.

---

## ⚙️ Configuration Guide

### 1. Registering a New App
Navigate to **Website > Configuration > Portal Apps** (or search "App Launcher" in the main menu).

| Field | Description |
| :--- | :--- |
| **Name** | The label shown under the icon (e.g., "Evidence"). |
| **Action URL** | The portal route to open (e.g., `/my/tasks`). |
| **Allowed Groups** | (Optional) Limit visibility to specific user groups. |
| **Technical Name** | Unique ID for PWA scoping (e.g., `evidence`). |

### 2. Design & Theming
Instead of manually picking colors, we provide **Pre-Optimized Themes**. Select one, and the system handles the rest.

| Theme | Aesthetic Profile | Best For |
| :--- | :--- | :--- |
| **Light (Clean)** | Professional White/Grey. High contrast. | Standard Business, Admin Tools |
| **Ocean (Blue)** | Cyan-to-Blue Linear Gradient. Glass Cards. | Logistics, Maritime, Standard UI |
| **Sunset (Orange)** | Red-to-Orange Gradient. Warm Tones. | Alerts, Urgent Tasks, Food |
| **Purple (Royalty)** | Deep Purple-to-Violet. Premium Feel. | HR, Employee Services, VIP |
| **Dark Mode** | OLED Black Background. Dark Grey Cards. | Night Shift, Low-Light Environments |

> **Note**: The "Theme Color" and "Background Color" fields are **read-only**. They are automatically computed to ensure the PWA meta tags match your chosen visual theme.

---

## 🛠️ Technical Architecture

### The "Hidden" Logic
While the UI is simple, the backend performs robust calculations:

1.  **CSS Injection**: When a user selects `Ocean`, the specific class `.theme-ocean` is injected into the HTML `<body>`. This triggers the CSS gradients defined in `static/src/css/portal_launcher.css`.
2.  **Meta Sync**: Simultaneously, the model sets `theme_color` to `#007BFF`. This value is rendered in `<meta name="theme-color" content="#007BFF"/>`, causing the Chrome/Safari toolbar to turn blue.
3.  **Scope Filtering**: The launcher intelligently detects which app is "Active" based on the URL path, dynamically switching the theme as the user moves between apps.

### PWA Assets
*   **Manifest**: `/portal_app/manifest.webmanifest` (Dynamic JSON)
*   **Service Worker**: `/service-worker.js` (Root scope registration)
*   **Icons**: Supports SVG and PNG. Adaptive icons are recommended.

---

## ❓ Troubleshooting

**Q: I don't see the "Install App" button.**
*   **A**: The button automatically hides if:
    1.  The app is **already installed**.
    2.  You are not serving Odoo over **HTTPS** (PWAs require secure contexts).
    3.  You are in a private/incognito window.

**Q: The colors look flat.**
*   **A**: Ensure you have upgraded the module to the latest version. The new **CSS Themes** require the updated `portal_launcher.css` and `portal_templates.xml`.

**Q: My customized colors disappeared.**
*   **A**: We deprecated manual color picking in favor of the **Theme System** to prevent inconsistent designs. Choose the theme that significantly matches your brand.

---

## 💳 Credits

**Author**: [Ganemo](https://www.ganemo.co)  
**Maintained by**: Fernando Pastor  
**License**: Odoo Proprietary License v1.0
