/** @odoo-module **/

// Photo Evidence Portal App - Offline Optimizations
// Powered by IndexedDB for robust large file storage

const DB_NAME = 'EvidencePortalDB';
const DB_VERSION = 1;
const STORE_NAME = 'offline_uploads';

class EvidenceStore {
    constructor() {
        this.db = null;
        this.initPromise = this.init();
    }

    init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(DB_NAME, DB_VERSION);

            request.onerror = (event) => {
                console.error("EvidencePortalDB error:", event.target.error);
                reject(event.target.error);
            };

            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                if (!db.objectStoreNames.contains(STORE_NAME)) {
                    db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true });
                }
            };

            request.onsuccess = (event) => {
                this.db = event.target.result;
                resolve(this.db);
            };
        });
    }

    async saveUpload(formData, actionUrl) {
        await this.initPromise;
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([STORE_NAME], 'readwrite');
            const store = transaction.objectStore(STORE_NAME);

            // Serialize FormData
            const data = {
                url: actionUrl,
                timestamp: new Date().toISOString(),
                fields: {},
                files: {} // We will store Blobs here
            };

            for (let [key, value] of formData.entries()) {
                if (value instanceof File || value instanceof Blob) {
                    // Blob storage is supported in modern IndexedDB
                    data.files[key] = value;
                } else {
                    data.fields[key] = value;
                }
            }

            const request = store.add(data);

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async getAllUploads() {
        await this.initPromise;
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([STORE_NAME], 'readonly');
            const store = transaction.objectStore(STORE_NAME);
            const request = store.getAll();

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async deleteUpload(id) {
        await this.initPromise;
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([STORE_NAME], 'readwrite');
            const store = transaction.objectStore(STORE_NAME);
            const request = store.delete(id);

            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }

    async count() {
        await this.initPromise;
        return new Promise((resolve) => {
            const transaction = this.db.transaction([STORE_NAME], 'readonly');
            const store = transaction.objectStore(STORE_NAME);
            const req = store.count();
            req.onsuccess = () => resolve(req.result);
            req.onerror = () => resolve(0);
        });
    }
}

const evidenceStore = new EvidenceStore();

// --- Network & UI Helpers ---

window.getNetworkInfo = function () {
    if (navigator.connection) {
        return navigator.connection.effectiveType;
    }
    return null;
}

// Toggle Search Bar
window.toggleEvidenceSearchBar = function () {
    var bar = document.getElementById('evidenceSearchBar');
    if (bar) {
        bar.style.display = (bar.style.display === 'none' || !bar.style.display) ? 'block' : 'none';
        if (bar.style.display === 'block') {
            var input = bar.querySelector('input');
            if (input) input.focus();
        }
    }
}

// Toggle Filter Menu
window.toggleFilterMenu = function (menuId) {
    // Close all others first
    const menus = ['filter_product_menu', 'filter_project_menu', 'filter_tag_menu', 'userMenu'];
    menus.forEach(function (id) {
        var el = document.getElementById(id);
        if (id !== menuId && el) {
            el.style.display = 'none';
        }
    });

    // Toggle target
    var menu = document.getElementById(menuId);
    if (menu) {
        menu.style.display = (menu.style.display === 'block') ? 'none' : 'block';
    }
}

// Close dropdowns when clicking outside
document.addEventListener('click', function (e) {
    if (!e.target.closest('.dropup') && !e.target.closest('.dropdown-menu') && !e.target.closest('.btn-light')) {
        const menus = ['filter_product_menu', 'filter_project_menu', 'filter_tag_menu', 'userMenu'];
        menus.forEach(function (id) {
            var el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });
    }
});


// --- Offline Logic ---

window.saveOfflineUpload = async function (formElement) {
    try {
        const formData = new FormData(formElement);
        const action = formElement.getAttribute('action');

        await evidenceStore.saveUpload(formData, action);

        // UI Feedback
        window.showToast('Offline', 'Evidence saved securely on device. Will auto-upload when online.', 'info');
        return true;
    } catch (e) {
        console.error('Offline save failed', e);
        window.showToast('Error', 'Storage failed: ' + e.message, 'danger');
        return false;
    }
}

window.syncOfflineUploads = async function () {
    if (!navigator.onLine) return;

    const count = await evidenceStore.count();
    if (count === 0) return;

    window.showToast('Syncing', `Uploading ${count} pending items...`, 'warning');

    const uploads = await evidenceStore.getAllUploads();

    for (const item of uploads) {
        try {
            const formData = new FormData();
            // Reconstruct FormData
            for (const [key, val] of Object.entries(item.fields)) {
                formData.append(key, val);
            }
            for (const [key, blob] of Object.entries(item.files)) {
                formData.append(key, blob); // Filename might be lost here? Usually not critical for backend
            }

            // Add flag to tell backend this is a sync
            formData.append('is_sync', 'true');

            // Send
            const response = await fetch(item.url, {
                method: 'POST',
                body: formData,
                // Do NOT set Content-Type header, fetch does it for FormData
            });

            if (response.ok || response.status === 302 || response.status === 303) {
                // Even redirects usually mean success in Odoo controller land
                await evidenceStore.deleteUpload(item.id);
            } else {
                console.warn("Sync failed for item", item.id, response.status);
            }

        } catch (e) {
            console.error("Sync network error", e);
        }
    }

    const remaining = await evidenceStore.count();
    if (remaining === 0) {
        window.showToast('Success', 'All pending evidence uploaded!', 'success');
        // Refresh page to show new state if we are on a list or task view
        if (window.location.pathname.includes('/my/evidence')) {
            setTimeout(() => window.location.reload(), 1500);
        }
    }
}


// --- Notifications ---

window.showToast = function (title, message, type = 'info') {
    // Check if toast container exists
    let container = document.getElementById('evidenceToastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'evidenceToastContainer';
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '1060';
        document.body.appendChild(container);
    }

    const toastHtml = `
        <div class="toast align-items-center text-white bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">
                    <strong>${title}:</strong> ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;

    const el = document.createElement('div');
    el.innerHTML = toastHtml;
    const toastEl = el.firstElementChild;
    container.appendChild(toastEl);

    // Bootstrap Toast (if available via Odoo) or simple fallback
    if (window.bootstrap && window.bootstrap.Toast) {
        const toast = new window.bootstrap.Toast(toastEl, { delay: 5000 });
        toast.show();
    } else {
        // Fallback animation
        toastEl.classList.add('show');
        setTimeout(() => toastEl.remove(), 5000);
    }
}

window.showOfflineNotification = function () {
    if (!navigator.onLine) {
        var existing = document.getElementById('offlineNotificationBanner');
        if (!existing) {
            var banner = document.createElement('div');
            banner.id = 'offlineNotificationBanner';
            banner.className = 'alert alert-warning position-fixed top-0 start-0 end-0 rounded-0 mb-0 text-center';
            banner.style.zIndex = '9999';
            banner.innerHTML = '<i class="fa fa-wifi-off me-2"></i> <strong>Offline Mode Active.</strong> Changes will sync automatically when online.';
            document.body.insertBefore(banner, document.body.firstChild);
        }
    }
}

// Monitor online/offline status
window.addEventListener('online', function () {
    var banner = document.getElementById('offlineNotificationBanner');
    if (banner) banner.remove();
    window.showToast('Online', 'Connection restored. Resuming sync...', 'success');
    window.syncOfflineUploads();
});

window.addEventListener('offline', function () {
    window.showOfflineNotification();
});

// --- Pull to Refresh ---

window.initPullToRefresh = function () {
    const el = document.getElementById('ptr-loader');
    if (!el) return;

    let startY = 0;
    let currentY = 0;
    let pulling = false;
    // Lower threshold for easier activation
    const threshold = 70;

    // Helper to get truly accurate scroll position
    function getScrollTop() {
        return window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop || 0;
    }

    const container = document.body; // Listen on body to catch all

    container.addEventListener('touchstart', (e) => {
        // Only enable if we are at the very top
        if (getScrollTop() <= 1) {
            startY = e.touches[0].clientY;
            currentY = startY;
            pulling = true;
            // Reset state
            el.style.transition = 'none';
        } else {
            pulling = false;
        }
    }, { passive: true }); // Passive true for performance start

    container.addEventListener('touchmove', (e) => {
        if (!pulling) return;

        currentY = e.touches[0].clientY;
        let delta = currentY - startY;
        const scrollTop = getScrollTop();

        // If we moved down but generated a scroll event (went below 0), abort
        if (scrollTop > 1) {
            pulling = false;
            el.style.transform = 'translateY(0)';
            el.style.opacity = '0';
            return;
        }

        if (delta > 0) {
            // We are pulling down
            // Calculate resistance
            let translate = Math.min(delta * 0.45, 120); // slightly more responsive

            // Visual updates
            requestAnimationFrame(() => {
                el.style.transform = `translateY(${translate}px)`;
                // Fade in quickly
                el.style.opacity = Math.min(translate / (threshold * 0.8), 1);

                const icon = el.querySelector('i');
                if (icon) icon.style.transform = `rotate(${translate * 2.5}deg)`;
            });

            // If we are significantly pulling, preventing default helps stop "overscroll" glow on Chrome Android
            if (delta > 10 && e.cancelable) {
                e.preventDefault();
            }
        }
    }, { passive: false }); // Passive false is KEY to allow preventDefault

    container.addEventListener('touchend', (e) => {
        if (!pulling) return;
        pulling = false;

        let delta = currentY - startY;
        const scrollTop = getScrollTop();

        // Restore transition for smooth snap back
        el.style.transition = 'transform 0.3s cubic-bezier(0,0,0.2,1), opacity 0.3s';

        if (delta > threshold && scrollTop <= 1) {
            // ACTION: Refresh
            el.style.transform = `translateY(${threshold}px)`;
            el.style.opacity = '1';

            const icon = el.querySelector('i');
            if (icon) {
                icon.style.transition = 'transform 1s linear';
                icon.style.transform = 'rotate(720deg)';
            }

            // Force reload
            setTimeout(() => {
                window.location.reload();
            }, 250);
        } else {
            // CANCEL: Snap back
            el.style.transform = 'translateY(0)';
            el.style.opacity = '0';
        }

        // Reset vars
        startY = 0;
        currentY = 0;
    });
}

// Show on load
document.addEventListener('DOMContentLoaded', async function () {
    window.initPullToRefresh();

    if (!navigator.onLine) {
        window.showOfflineNotification();
    } else {
        // Try sync on load
        window.syncOfflineUploads();
    }
});
