/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

// PWA Setup Pattern
let delayedPrompt = null;

browser.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    delayedPrompt = e;
    console.log("PWA install prompt delayed.");
});

// Check standalone display mode to hide install buttons if needed
if (window.matchMedia('(display-mode: standalone)').matches) {
    console.log("Running in standalone mode.");
}
