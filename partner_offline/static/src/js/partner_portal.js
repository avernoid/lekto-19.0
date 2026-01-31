/** @odoo-module **/

// 1. PWA Install Logic (Capture Early Pattern)
let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
    // Prevent the mini-infobar from appearing on mobile
    e.preventDefault();
    // Stash the event so it can be triggered later.
    deferredPrompt = e;
    console.log("Partner Portal: beforeinstallprompt captured");

    // Show Install Button if it exists
    const installBtn = document.getElementById('pwaInstallBtn');
    if (installBtn) {
        installBtn.classList.remove('d-none');
    }
});

// Event Delegation for Install Click
document.addEventListener('click', (e) => {
    if (e.target.closest('#pwaInstallBtn')) {
        // Hide the app provided install promotion
        const installBtn = document.getElementById('pwaInstallBtn');
        if (installBtn) installBtn.classList.add('d-none');

        // Show the install prompt
        if (deferredPrompt) {
            deferredPrompt.prompt();
            // Wait for the user to respond to the prompt
            deferredPrompt.userChoice.then((choiceResult) => {
                if (choiceResult.outcome === 'accepted') {
                    console.log('User accepted the install prompt');
                } else {
                    console.log('User dismissed the install prompt');
                }
                deferredPrompt = null;
            });
        }
    }
});

// 2. App Installed Event
window.addEventListener('appinstalled', () => {
    console.log('Partner Portal: PWA installed');
    const installBtn = document.getElementById('pwaInstallBtn');
    if (installBtn) installBtn.classList.add('d-none');
});

// 3. UI Enhancements
document.addEventListener('DOMContentLoaded', () => {
    // Detect Standalone Mode
    if (window.matchMedia('(display-mode: standalone)').matches) {
        console.log("Running in standalone mode");
        document.body.classList.add('pwa-standalone');
    }
});
// --- Pull to Refresh ---

window.initPullToRefresh = function () {
    const el = document.getElementById('ptr-loader');
    if (!el) return;

    let startY = 0;
    let currentY = 0;
    let pulling = false;
    const threshold = 80;

    window.addEventListener('touchstart', (e) => {
        if (window.scrollY === 0) {
            startY = e.touches[0].clientY;
            pulling = true;
        }
    }, { passive: true });

    window.addEventListener('touchmove', (e) => {
        if (!pulling) return;

        currentY = e.touches[0].clientY;
        let delta = currentY - startY;

        if (delta > 0) {
            // Pulling down
            if (window.scrollY > 0) {
                pulling = false;
                return;
            }

            // Apply resistance
            let translate = Math.min(delta * 0.5, 150);

            // Visuals
            el.style.transform = `translateY(${translate}px)`;
            el.style.opacity = Math.min(translate / threshold, 1);

            // Rotate icon
            const icon = el.querySelector('i');
            if (icon) icon.style.transform = `rotate(${translate * 2}deg)`;

            // Prevent default chrome "overscroll" only if we are actively pulling
            if (delta > 10 && e.cancelable) {
                e.preventDefault();
            }
        } else {
            pulling = false;
        }
    }, { passive: false });

    window.addEventListener('touchend', (e) => {
        if (!pulling) return;
        pulling = false;

        let delta = currentY - startY;
        if (delta > threshold && window.scrollY === 0) {
            // Trigger Refresh
            el.style.transform = `translateY(${threshold}px)`;
            el.classList.add('ptr-loading');
            window.location.reload();
        } else {
            // Snap back
            el.style.transform = 'translateY(0)';
            el.style.opacity = '0';
        }

        startY = 0;
        currentY = 0;
    });
}

document.addEventListener('DOMContentLoaded', () => {
    window.initPullToRefresh();
});
