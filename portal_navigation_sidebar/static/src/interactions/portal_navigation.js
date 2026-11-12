import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { PortalHomeCounters } from "@portal/interactions/portal_home_counters";

/**
 * Reveals the options the server could not decide on (no counter cached in
 * the session yet). Same rule as the portal home page: an option with a
 * counter is shown only when it has documents, except the ones the home page
 * always shows (Invoices and Orders, added by account and sale through
 * PortalHomeCounters.getCountersAlwaysDisplayed).
 *
 * The counters only tell whether there are documents (most are computed
 * with limit=1), so no number is displayed.
 */
export class PortalNavigation extends Interaction {
    static selector = ".o_portal_navigation";

    async willStart() {
        // Each app patches the prototype; the method does not use `this`.
        const alwaysDisplayed = PortalHomeCounters.prototype.getCountersAlwaysDisplayed.call(this);
        const hiddenItems = [...this.el.querySelectorAll("li.d-none[data-placeholder_count]")];
        this.alwaysDisplayedItems = hiddenItems.filter((item) =>
            alwaysDisplayed.includes(item.dataset.placeholder_count)
        );
        this.pendingItems = hiddenItems.filter((item) => !this.alwaysDisplayedItems.includes(item));
        this.counters = {};
        if (!this.pendingItems.length) {
            return;
        }
        // ODOO-20: /my/counters takes a dict {counter: category} instead of a
        // list (the category comes from the portal.entry record).
        this.counters = await this.waitFor(
            rpc("/my/counters", {
                counters: this.pendingItems.map((item) => item.dataset.placeholder_count),
            })
        );
    }

    start() {
        for (const item of this.alwaysDisplayedItems) {
            item.classList.remove("d-none");
        }
        for (const item of this.pendingItems) {
            if (this.counters[item.dataset.placeholder_count]) {
                item.classList.remove("d-none");
            }
        }
    }
}

registry.category("public.interactions").add("portal_navigation_sidebar.portal_navigation", PortalNavigation);
