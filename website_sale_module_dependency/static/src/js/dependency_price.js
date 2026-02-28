/** @odoo-module */

import { rpc } from "@web/core/network/rpc";

/**
 * Lazy-load pricelist-aware dependency prices on the catalog / product pages.
 *
 * HOW IT WORKS
 * ────────────
 * 1. The QWeb template renders dependency blocks with `data-dep-tmpl-id`
 *    attributes and small FA-spinner placeholders instead of prices.
 * 2. On DOMContentLoaded this script collects every product template id
 *    that has a dependency price placeholder.
 * 3. A single JSON-RPC call fetches pricelist + tax-aware prices for ALL
 *    visible products at once.
 * 4. The DOM is patched with formatted prices and spinners removed.
 *
 * The page is fully interactive before prices arrive (non-blocking).
 */

function formatPrice(value, symbol, position) {
    const formatted = parseFloat(value).toFixed(2);
    if (position === "before") {
        return `${symbol}\u00a0${formatted}`;
    }
    return `${formatted}\u00a0${symbol}`;
}

async function loadDependencyPrices() {
    // Collect all product template IDs that need dependency prices
    const elements = document.querySelectorAll("[data-dep-tmpl-id]");
    if (!elements.length) {
        return;
    }

    const tmplIds = new Set();
    for (const el of elements) {
        tmplIds.add(parseInt(el.dataset.depTmplId, 10));
    }

    let result;
    try {
        result = await rpc("/shop/module_deps_prices", {
            product_template_ids: [...tmplIds],
        });
    } catch (err) {
        // On failure, hide spinners and show fallback (the raw list_price
        // that is already in the hidden `.dep_price_fallback` span).
        console.warn("Module dependency prices: RPC failed", err);
        for (const el of document.querySelectorAll(".dep_price_spinner")) {
            el.classList.add("d-none");
        }
        for (const el of document.querySelectorAll(".dep_price_fallback")) {
            el.classList.remove("d-none");
        }
        return;
    }

    if (!result || typeof result !== "object") {
        return;
    }

    for (const [tmplId, data] of Object.entries(result)) {
        const { deps, total, currency_symbol, currency_position } = data;

        // ── Catalog: update total-with-deps value ──
        const catalogEls = document.querySelectorAll(
            `.module_dep_total[data-dep-tmpl-id="${tmplId}"]`
        );
        for (const el of catalogEls) {
            const valueEl = el.querySelector(".dep_price_value");
            if (valueEl) {
                valueEl.textContent = formatPrice(total, currency_symbol, currency_position);
            }
        }

        // ── Product page: update individual dep prices ──
        const blockEls = document.querySelectorAll(
            `.module_dependencies_block[data-dep-tmpl-id="${tmplId}"]`
        );
        for (const block of blockEls) {
            for (const dep of deps) {
                const depEl = block.querySelector(
                    `.dep_price_item[data-dep-id="${dep.id}"]`
                );
                if (depEl) {
                    const priceEl = depEl.querySelector(".dep_price_value");
                    if (priceEl) {
                        priceEl.textContent = formatPrice(dep.price, currency_symbol, currency_position);
                    }
                }
            }

            // Update the grand total
            const totalEl = block.querySelector(".dep_total_value");
            if (totalEl) {
                totalEl.textContent = formatPrice(total, currency_symbol, currency_position);
            }
        }
    }
}

// Run after DOM is ready (non-blocking — page renders first)
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", loadDependencyPrices);
} else {
    // DOM already parsed (e.g. module loaded late)
    loadDependencyPrices();
}
