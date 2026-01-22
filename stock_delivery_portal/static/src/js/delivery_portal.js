/** @odoo-module **/

// Simple vanilla JS implementation for the Portal App

// Network Status Monitoring (detect 3G/4G/5G/WiFi)
window.getNetworkInfo = function() {
    if (navigator.connection) {
        return navigator.connection.effectiveType; // 'slow-2g', '2g', '3g', '4g'
    }
    return null; // Not available
}

window.isSlowConnection = function() {
    var type = window.getNetworkInfo();
    return type === 'slow-2g' || type === '2g' || type === '3g';
}

// Image Compression Utility
window.compressImage = function(file, callback) {
    if (!file) return;
    var reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = function(event) {
        var img = new Image();
        img.src = event.target.result;
        img.onload = function() {
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

function openScannerModal() {
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

function closeScannerModal() {
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
    closeScannerModal();
    // Perform Search
    processScanResult(decodedText);
}

function searchBarcode() {
    var val = document.getElementById('manualBarcode').value;
    if (val) {
        closeScannerModal();
        processScanResult(val);
    }
}

function processScanResult(query) {
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
        if (data.result) {
            var res = data.result;
            if (res.match_type === 'exact') {
                window.location.href = res.action_url;
            } else if (res.match_type === 'multiple') {
                window.location.href = '/my/delivery?search=' + encodeURIComponent(query);
            } else {
                alert("No delivery found for: " + query);
            }
        } else {
            alert("Error searching.");
        }
    });
}

// Map Navigation with App Selector
window.openMapSelector = function(latitude, longitude, address) {
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

window.closeMapSelector = function() {
    var modal = document.getElementById('mapSelectorModal');
    var backdrop = document.getElementById('mapSelectorBackdrop');
    if (modal) modal.remove();
    if (backdrop) backdrop.remove();
}

window.openMapApp = function(appType) {
    // Get stored coordinates
    if (!window._mapCoordinates) {
        alert("Location data not available");
        return;
    }
    
    var lat = window._mapCoordinates.lat;
    var lng = window._mapCoordinates.lng;
    var url = '';

    // Handle different app types
    switch(appType) {
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
