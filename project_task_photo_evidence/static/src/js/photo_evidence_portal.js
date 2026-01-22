/** @odoo-module **/

// Photo Evidence Portal App - Offline Optimizations

// Network Status Monitoring
window.getNetworkInfo = function() {
    if (navigator.connection) {
        return navigator.connection.effectiveType; // 'slow-2g', '2g', '3g', '4g'
    }
    return null;
}

window.isSlowConnection = function() {
    var type = window.getNetworkInfo();
    return type === 'slow-2g' || type === '2g' || type === '3g';
}

// Toggle Search Bar
window.toggleEvidenceSearchBar = function() {
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
window.toggleFilterMenu = function(menuId) {
    // Close all others first
    const menus = ['filter_product_menu', 'filter_project_menu', 'filter_tag_menu'];
    menus.forEach(function(id) {
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
document.addEventListener('click', function(e) {
    if (!e.target.closest('.dropup') && !e.target.closest('.dropdown-menu')) {
        const menus = ['filter_product_menu', 'filter_project_menu', 'filter_tag_menu'];
        menus.forEach(function(id) {
            var el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });
    }
});

// Offline Draft Storage for Upload Form
const OFFLINE_UPLOAD_KEY = 'pending_evidence_upload_';

window.saveOfflineUpload = function(formData, taskId) {
    try {
        const key = OFFLINE_UPLOAD_KEY + taskId;
        const data = {};
        
        // Convert FormData to plain object (except file)
        formData.forEach((value, key) => {
            if (key !== 'evidence_file' && key !== 'evidence_file_base64') {
                data[key] = value;
            }
        });
        
        data.timestamp = new Date().toISOString();
        data.pending = true;
        
        localStorage.setItem(key, JSON.stringify(data));
        return true;
    } catch(e) {
        console.error('Storage failed', e);
        return false;
    }
}

window.getOfflineUploads = function() {
    const uploads = {};
    for (let key in localStorage) {
        if (key.startsWith(OFFLINE_UPLOAD_KEY)) {
            try {
                uploads[key] = JSON.parse(localStorage[key]);
            } catch(e) {
                console.error('Parse error', e);
            }
        }
    }
    return uploads;
}

window.clearOfflineUpload = function(taskId) {
    const key = OFFLINE_UPLOAD_KEY + taskId;
    localStorage.removeItem(key);
}

// Check and Show Offline Notification
window.showOfflineNotification = function() {
    if (!navigator.onLine) {
        var existing = document.getElementById('offlineNotificationBanner');
        if (!existing) {
            var banner = document.createElement('div');
            banner.id = 'offlineNotificationBanner';
            banner.className = 'alert alert-warning position-fixed top-0 start-0 end-0 rounded-0 mb-0';
            banner.style.zIndex = '9999';
            banner.innerHTML = '<i class="fa fa-wifi-off me-2"></i> <strong>You are offline.</strong> Your uploads will be saved locally and synced when online.';
            document.body.insertBefore(banner, document.body.firstChild);
        }
    }
}

// Monitor online/offline status
window.addEventListener('online', function() {
    var banner = document.getElementById('offlineNotificationBanner');
    if (banner) banner.remove();
});

window.addEventListener('offline', function() {
    window.showOfflineNotification();
});

// Show on load
document.addEventListener('DOMContentLoaded', function() {
    window.showOfflineNotification();
});
