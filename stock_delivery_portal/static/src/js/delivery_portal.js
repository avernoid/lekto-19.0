/** @odoo-module **/

// Filtrado de items por paquete en la vista de picking portal
window.currentFilteredPackageId = null;
window.filterItemsByPackage = function (btn) {
    if (!btn) return;
    var pkgId = String(btn.getAttribute('data-package-id') || "");
    var items = document.querySelectorAll('#itemsList li');
    var clearBtn = document.getElementById('clearPackageFilterBtn');

    // Toggle logic
    if (window.currentFilteredPackageId === pkgId) {
        items.forEach(function (li) { li.style.setProperty('display', '', 'important'); });
        if (clearBtn) clearBtn.classList.add('d-none');
        window.currentFilteredPackageId = null;
    } else {
        items.forEach(function (li) {
            var itemPkgId = String(li.getAttribute('data-package-id') || "");
            if (itemPkgId === pkgId) {
                li.style.setProperty('display', '', 'important');
            } else {
                li.style.setProperty('display', 'none', 'important');
            }
        });
        if (clearBtn) clearBtn.classList.remove('d-none');
        window.currentFilteredPackageId = pkgId;
    }
}
window.clearPackageFilter = function () {
    var items = document.querySelectorAll('#itemsList li');
    var clearBtn = document.getElementById('clearPackageFilterBtn');
    items.forEach(function (li) { li.style.setProperty('display', '', 'important'); });
    if (clearBtn) clearBtn.classList.add('d-none');
    window.currentFilteredPackageId = null;
}

// Simple vanilla JS implementation for the Portal App

// Network Status Monitoring (detect 3G/4G/5G/WiFi)
window.getNetworkInfo = function () {
    if (navigator.connection) {
        return navigator.connection.effectiveType; // 'slow-2g', '2g', '3g', '4g'
    }
    return null; // Not available
}

window.isSlowConnection = function () {
    var type = window.getNetworkInfo();
    return type === 'slow-2g' || type === '2g' || type === '3g';
}

// Image Compression Utility
window.compressImage = function (file, callback) {
    if (!file) return;
    var reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = function (event) {
        var img = new Image();
        img.src = event.target.result;
        img.onload = function () {
            var elem = document.createElement('canvas');
            var width = img.width;
            var height = img.height;
            var MAX_WIDTH = 1024;
            var MAX_HEIGHT = 1024;

            if (width > height) {
                if (width > MAX_WIDTH) {
                    height *= MAX_WIDTH / width;
                    width = MAX_WIDTH;
                }
            } else {
                if (height > MAX_HEIGHT) {
                    width *= MAX_HEIGHT / height;
                    height = MAX_HEIGHT;
                }
            }
            elem.width = width;
            elem.height = height;
            var ctx = elem.getContext('2d');
            ctx.drawImage(img, 0, 0, width, height);
            var dataUrl = elem.toDataURL('image/webp', 0.6);
            callback(dataUrl);
        }
    }
}

// Custom Filter Logic mimicking project_task_photo_evidence
// Attached to window to be accessible by onclick events in templates

window.toggleDeliverySearchBar = function () {
    var bar = document.getElementById('deliverySearchBar');
    if (bar) {
        bar.style.display = (bar.style.display === 'none' || !bar.style.display) ? 'block' : 'none';
        if (bar.style.display === 'block') {
            var input = bar.querySelector('input');
            if (input) input.focus();
        }
    }
}

window.toggleDeliveryFilterMenu = function (menuId) {
    // Close all others first
    const menus = ['filter_type_menu', 'filter_state_menu'];
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
    if (!e.target.closest('.dropup') && !e.target.closest('.dropdown-menu')) {
        const menus = ['filter_type_menu', 'filter_state_menu'];
        menus.forEach(function (id) {
            var el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });
    }
});

// Scanner Logic
let html5QrcodeScanner = null;

window.openScannerModal = function () {
    var modalEl = document.getElementById('scannerModal');
    // Manual Modal Show
    modalEl.classList.add('show');
    modalEl.style.display = 'block';
    modalEl.setAttribute('aria-modal', 'true');
    modalEl.removeAttribute('aria-hidden');

    // Add backdrop
    var backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop fade show';
    backdrop.id = 'scannerBackdrop';
    document.body.appendChild(backdrop);

    // Start scanner
    startScanner();
}

window.closeScannerModal = function () {
    var modalEl = document.getElementById('scannerModal');
    modalEl.classList.remove('show');
    modalEl.style.display = 'none';
    modalEl.setAttribute('aria-hidden', 'true');
    modalEl.removeAttribute('aria-modal');

    // Remove backdrop
    var backdrop = document.getElementById('scannerBackdrop');
    if (backdrop) backdrop.remove();

    // Stop scanner
    if (html5QrcodeScanner) {
        html5QrcodeScanner.stop().then(ignore => {
            html5QrcodeScanner.clear();
        }).catch(err => {
            // Handle race condition if stop called before start finished
            console.log("Scanner stop error", err);
        });
    }
}

function startScanner() {
    if (!document.getElementById('reader')) return;

    // Check if Html5Qrcode is loaded
    if (typeof Html5Qrcode === 'undefined') {
        alert("Scanner library not loaded. Please reload the page.");
        return;
    }

    const html5QrCode = new Html5Qrcode("reader");
    html5QrcodeScanner = html5QrCode;

    const config = { fps: 10, qrbox: { width: 250, height: 250 } };

    // Prefer back camera
    html5QrCode.start({ facingMode: "environment" }, config, onScanSuccess)
        .catch(err => {
            console.error(err);
            document.getElementById('reader').innerHTML = '<div class="alert alert-warning">Camera not available or permission denied. Use manual entry.</div>';
        });
}

function onScanSuccess(decodedText, decodedResult) {
    // Determine what to do
    // Stop scanning and close
    window.closeScannerModal();
    // Perform Search
    window.processScanResult(decodedText);
}

window.searchBarcode = function () {
    var val = document.getElementById('manualBarcode').value;
    if (val) {
        window.closeScannerModal();
        window.processScanResult(val);
    }
}

window.processScanResult = function (query) {
    // Call controller
    fetch('/my/delivery/search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            jsonrpc: "2.0",
            method: "call",
            params: {
                query: query
            }
        })
    }).then(res => res.json()).then(data => {
        if (data.error) {
            console.error("JSONRPC Error:", data.error);
            alert("Error in search request: " + (data.error.message || "Unknown error"));
            return;
        }
        if (data.result) {
            var res = data.result;
            if (res.match_type === 'exact') {
                window.location.href = res.action_url;
            } else if (res.match_type === 'multiple' && Array.isArray(res.picking_ids) && res.picking_ids.length > 0) {
                window.filterDeliveriesByIds(res.picking_ids);
            } else if (res.match_type === 'error') {
                console.error("Server Logic Error:", res.message);
                alert("Search failed: " + res.message);
            } else {
                alert("No delivery found for: " + query);
            }
        } else {
            alert("Internal search error (Missing result)");
        }
    }).catch(err => {
        console.error("Fetch/Network Error:", err);
        alert("Connection error or search failed.");
    });
}

// Filtra la lista de cards de entregas mostrando solo los que tengan un data-picking-id en la lista
window.filterDeliveriesByIds = function (ids) {
    // Oculta todos los cards excepto los que coinciden
    var cards = document.querySelectorAll('[data-picking-id]');
    var found = false;
    window._activeIdFilter = ids;
    cards.forEach(function (card) {
        var pid = card.getAttribute('data-picking-id');
        if (ids.includes(Number(pid)) || ids.includes(pid)) {
            card.style.display = '';
            found = true;
        } else {
            card.style.display = 'none';
        }
    });

    // Show Clear buttons if scan result is active
    ['clearAllFiltersBtnTop', 'clearAllFiltersBtnBottom'].forEach(id => {
        var btn = document.getElementById(id);
        if (btn) btn.classList.remove('d-none');
    });

    if (!found) {
        alert('No deliveries found for this scan.');
    }
}

// Limpia el filtro por IDs y muestra todos los cards
window.clearIdFilter = function () {
    var cards = document.querySelectorAll('[data-picking-id]');
    cards.forEach(function (card) {
        card.style.display = '';
    });
    window._activeIdFilter = null;

    // Check if we also have server-side filters
    const urlParams = new URLSearchParams(window.location.search);
    const hasServerFilters = urlParams.has('search') || urlParams.has('filter_state') || urlParams.has('filter_type');

    if (!hasServerFilters) {
        ['clearAllFiltersBtnTop', 'clearAllFiltersBtnBottom'].forEach(id => {
            var btn = document.getElementById(id);
            if (btn) btn.classList.add('d-none');
        });
    }
}

// Hook para los botones Clear existentes
window.clearAllFilters = function () {
    window.clearIdFilter();

    // Use URLSearchParams for more robust filter detection
    const urlParams = new URLSearchParams(window.location.search);
    const hasSearch = urlParams.has('search') && urlParams.get('search');
    const hasState = urlParams.has('filter_state') && urlParams.get('filter_state');
    const hasType = urlParams.has('filter_type') && urlParams.get('filter_type');

    if (hasSearch || hasState || hasType) {
        // Redirigir a /my/delivery preservando solo el parámetro history si existe
        let targetUrl = '/my/delivery';
        if (urlParams.has('history')) {
            targetUrl += '?history=' + urlParams.get('history');
        }
        window.location.href = targetUrl;
    }
}

// Map Navigation with App Selector
window.openMapSelector = function (latitude, longitude, address) {
    // Parse coordinates
    var lat = parseFloat(latitude);
    var lng = parseFloat(longitude);

    // Double-check coordinates validity (safety net)
    if (isNaN(lat) || isNaN(lng) || lat < -90 || lat > 90 || lng < -180 || lng > 180) {
        alert("Location coordinates are invalid.");
        return;
    }

    // Store coordinates for modal buttons
    window._mapCoordinates = { lat: lat, lng: lng };
    // Escape address for safe HTML display
    var addressDisplay = address ? address.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\"/g, '&quot;').replace(/'/g, '&#039;') : 'Unknown location';

    // Create modal backdrop
    var backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop fade show';
    backdrop.id = 'mapSelectorBackdrop';
    backdrop.style.zIndex = '1040';
    document.body.appendChild(backdrop);

    // Create modal
    var modal = document.createElement('div');
    modal.className = 'modal fade show';
    modal.id = 'mapSelectorModal';
    modal.setAttribute('tabindex', '-1');
    modal.setAttribute('aria-labelledby', 'mapSelectorLabel');
    modal.setAttribute('aria-hidden', 'true');
    modal.style.display = 'block';
    modal.style.zIndex = '1050';
    modal.innerHTML = `
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content rounded-3">
                <div class="modal-header border-bottom">
                    <h5 class="modal-title" id="mapSelectorLabel">Open Maps with</h5>
                    <button type="button" class="btn-close" onclick="closeMapSelector()"></button>
                </div>
                <div class="modal-body">
                    <div class="alert alert-light border rounded-2 mb-3 p-2">
                        <small class="text-muted"><i class="fa fa-map-marker me-1"></i> <strong>Navigation to:</strong></small>
                        <div class="small mt-1">${addressDisplay}</div>
                    </div>
                    <div class="d-grid gap-2">
                        <button class="btn btn-light border text-start p-3 rounded-2" onclick="window.openMapApp('google')">
                            <div class="fw-bold d-flex align-items-center">
                                <i class="fa fa-map-marker me-2 text-danger"></i> Google Maps
                            </div>
                            <small class="text-muted ms-4">Navigate with Google Maps</small>
                        </button>
                        <button class="btn btn-light border text-start p-3 rounded-2" onclick="window.openMapApp('apple')">
                            <div class="fw-bold d-flex align-items-center">
                                <i class="fa fa-map me-2 text-primary"></i> Apple Maps
                            </div>
                            <small class="text-muted ms-4">Navigate with Apple Maps</small>
                        </button>
                        <button class="btn btn-light border text-start p-3 rounded-2" onclick="window.openMapApp('waze')">
                            <div class="fw-bold d-flex align-items-center">
                                <i class="fa fa-road me-2" style="color: #00BEF7;"></i> Waze
                            </div>
                            <small class="text-muted ms-4">Navigate with Waze</small>
                        </button>
                        <button class="btn btn-light border text-start p-3 rounded-2" onclick="window.openMapApp('osm')">
                            <div class="fw-bold d-flex align-items-center">
                                <i class="fa fa-globe me-2" style="color: #7FB069;"></i> OpenStreetMap
                            </div>
                            <small class="text-muted ms-4">Navigate with OpenStreetMap</small>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}

window.closeMapSelector = function () {
    var modal = document.getElementById('mapSelectorModal');
    var backdrop = document.getElementById('mapSelectorBackdrop');
    if (modal) modal.remove();
    if (backdrop) backdrop.remove();
}

window.openMapApp = function (appType) {
    // Get stored coordinates
    if (!window._mapCoordinates) {
        alert("Location data not available");
        return;
    }

    var lat = window._mapCoordinates.lat;
    var lng = window._mapCoordinates.lng;
    var url = '';

    // Handle different app types
    switch (appType) {
        case 'google':
            // Google Maps (works on web and mobile)
            url = `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`;
            break;
        case 'apple':
            // Apple Maps URL scheme (for iOS)
            url = `maps://maps.apple.com/?ll=${lat},${lng}&q=Delivery Location`;
            break;
        case 'waze':
            // Waze URL scheme
            url = `https://waze.com/ul?ll=${lat},${lng}&navigate=yes`;
            break;
        case 'osm':
            // OpenStreetMap
            url = `https://maps.openstreetmap.org/?mlat=${lat}&mlon=${lng}&zoom=18`;
            break;
    }

    // Close modal and navigate
    closeMapSelector();
    if (url) {
        window.location.href = url;
    }
}

// --- Pull to Refresh ---

window.initPullToRefresh = function () {
    const el = document.getElementById('ptr-loader');
    const content = document.querySelector('.container'); // Target the main content
    if (!el || !content) return;

    let startY = 0;
    let currentY = 0;
    let pulling = false;
    const threshold = 80;

    // Helper to reset styles
    const reset = () => {
        el.style.transition = 'transform 0.3s, opacity 0.3s';
        el.style.transform = 'translateY(0)';
        el.style.opacity = '0';

        content.style.transition = 'transform 0.3s';
        content.style.transform = 'translateY(0)';

        pulling = false;
        startY = 0;
        currentY = 0;
    };

    window.addEventListener('touchstart', (e) => {
        // Only trigger if we are at the very top of the page
        if (window.scrollY === 0) {
            startY = e.touches[0].clientY;
            pulling = false; // Wait for move to confirm direction
        } else {
            startY = 0;
        }
    }, { passive: true });

    window.addEventListener('touchmove', (e) => {
        if (startY === 0) return;

        const y = e.touches[0].clientY;
        const delta = y - startY;

        // Check if we are pulling down
        if (delta > 0 && window.scrollY === 0) {
            pulling = true;

            // Prevent native scroll/overscroll since we handle it
            if (e.cancelable) e.preventDefault();

            // Store current Y
            currentY = y;

            // Resistance curve (logarithmic for native feel)
            const translate = Math.min(delta * 0.45, 150);

            // 1. Move Loader
            el.style.transition = 'none';
            el.style.transform = `translateY(${translate}px)`;

            // 2. Fade in Loader (start showing after 15px pull)
            const opacity = Math.min(Math.max(translate - 15, 0) / (threshold - 15), 1);
            el.style.opacity = opacity;

            // 3. Move Content (Physically push content down)
            content.style.transition = 'none';
            content.style.transform = `translateY(${translate}px)`;

            // 4. Rotate Icon
            const icon = el.querySelector('i');
            if (icon) icon.style.transform = `rotate(${translate * 2}deg)`;

        } else {
            // Scrolled back up or down-page, cancel pull
            pulling = false;
        }
    }, { passive: false });

    window.addEventListener('touchend', (e) => {
        if (!pulling) return;

        const delta = currentY - startY;
        // Check if we pulled enough (visual translation approx matches delta * resist)
        // Let's use computed style or just the logic
        const translate = Math.min(delta * 0.45, 150);

        if (translate > 65) { // Threshold reached
            // Show Loading State
            el.style.transition = 'transform 0.3s';
            el.style.transform = `translateY(70px)`;
            el.style.opacity = '1';

            // Keep content pushed down momentarily
            content.style.transition = 'transform 0.3s';
            content.style.transform = `translateY(70px)`;

            // Spin icon
            const icon = el.querySelector('i');
            if (icon) icon.className = "fa fa-refresh fa-spin fa-2x"; // Use big spinner

            // Reload
            setTimeout(() => {
                window.location.reload();
            }, 500);
        } else {
            // Snap back
            reset();
        }
    });
}

// Init on Load
document.addEventListener('DOMContentLoaded', function () {
    window.initPullToRefresh();
});
