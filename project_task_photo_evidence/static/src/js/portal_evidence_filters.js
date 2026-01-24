/** @odoo-module **/

// Global functions for Portal Search & Filters
// Attached to window to be accessible by onclick events in templates

window.toggleEvidenceSearchBar = function () {
    var bar = document.getElementById('evidenceSearchBar');
    if (bar) {
        bar.style.display = bar.style.display === 'none' ? 'block' : 'none';

        // Auto focus input when opened
        if (bar.style.display === 'block') {
            var input = bar.querySelector('input[name="search"]');
            if (input) input.focus();
        }
    }
};

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
        // Toggle logic
        if (menu.style.display === 'block') {
            menu.style.display = 'none';
        } else {
            menu.style.display = 'block';
        }
    }
};

// Close menus when clicking outside
document.addEventListener('click', function (event) {
    // Check if click is outside of any toggle button or menu
    if (!event.target.closest('.dropup') && !event.target.closest('.dropdown-menu')) {
        const menus = ['filter_product_menu', 'filter_project_menu', 'filter_tag_menu', 'userMenu'];
        menus.forEach(function (id) {
            var el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });
    }
});
