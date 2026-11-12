import logging
from urllib.parse import urlsplit

from odoo import api, models
from odoo.http import request

_logger = logging.getLogger(__name__)


class PortalNavigation(models.AbstractModel):
    _name = 'portal.navigation'
    _description = 'Portal Navigation Sidebar'

    @api.model
    def _get_navigation_entries(self, require_active=False):
        """Sidebar entries for the current request, called by the layouts.

        :param bool require_active: only return entries when the current page
            is one of the options. Used for pages that do not use
            ``portal.portal_layout`` (e.g. /my/payment_method), so that the
            menu never shows on unrelated website pages.
        :return: list of dicts (see ``_build_entries``), empty when there is
            nothing to show
        """
        if not request or self.env.user._is_public():
            return []
        try:
            with self.env.cr.savepoint():
                catalog = self._get_catalog()
        except Exception:
            # A broken third-party override must never break the portal
            # pages: the page shows without the sidebar.
            _logger.exception("Portal navigation: could not read the portal home page options")
            return []
        entries = self._build_entries(
            catalog,
            request.session.get('portal_counters', {}),
            self._strip_lang_prefix(request.httprequest.path),
        )
        if require_active and not any(entry['active'] for entry in entries):
            return []
        return entries

    @api.model
    def _get_catalog(self):
        """Options of the portal home page, from the ``portal.entry`` records.

        Same records and order as ``CustomerPortal._prepare_portal_layout_values``
        (``portal_cards``): alerts excluded ("Quotations to review"... point to
        a filtered view of an option that has its own card) and cards the
        website editor hid (``show_in_portal``) too.

        * Cards with a counter are kept: their visibility depends on the
          documents of each user and is decided per request.
        * Cards without counter follow the home page:
          ``_filter_visible_portal_cards`` decides (config cards, payment
          methods when the user has tokens...).

        Not cached: the search is cheap and the business rules depend on each
        user.
        """
        cards = self.env['portal.entry'].search([
            ('show_in_portal', '=', True), ('category', '!=', 'alert'),
        ]).sorted()
        visible_cards = cards._filter_visible_portal_cards()
        catalog, seen_urls = [], set()
        for card in cards:
            if not card.url or card.url in seen_urls or not (card.placeholder_count or card in visible_cards):
                continue
            seen_urls.add(card.url)
            catalog.append({
                'name': card.name,
                'url': card.url,
                'icon': card.image and '/web/image/portal.entry/%s/image' % card.id,
                'placeholder_count': card.placeholder_count or False,
                'category': card.category or 'common_category',
                'always_visible': card in visible_cards,
            })
        return catalog

    @api.model
    def _build_entries(self, catalog, counters_cache, path):
        """Decide visibility and the active option for one request.

        :param catalog: entries from ``_get_catalog``: dicts with ``name``,
            ``url``, ``icon``, ``placeholder_count``, ``category`` and
            ``always_visible`` (shown whatever the documents). The 19 version
            builds the same dicts from the rendered home page.
        :param dict counters_cache: ``request.session['portal_counters']``,
            filled by /my/counters with ``{counter: has documents}``
        :param str path: current path, without language prefix
        :return: list of dicts with the catalog keys plus:
            ``visible`` (shown on load; the others wait for /my/counters),
            ``active`` (current option) and ``group_start`` (first option of a
            new category, to draw a separator)
        """
        active_url = self._get_active_url([entry['url'] for entry in catalog], path)
        entries = []
        previous_category = None
        for entry in catalog:
            active = entry['url'] == active_url
            entries.append(dict(
                entry,
                active=active,
                visible=active or entry['always_visible'] or bool(counters_cache.get(entry['placeholder_count'])),
                group_start=previous_category is not None and entry['category'] != previous_category,
            ))
            previous_category = entry['category']
        return entries

    @api.model
    def _get_active_url(self, urls, path):
        """Return the url whose path is the longest prefix of ``path``.

        /my/invoices matches /my/invoices and /my/invoices/page/2, but not
        /my/invoices_report. The website writes the language prefix in the
        links of the portal (/es/my/invoices): it is ignored on both sides.
        """
        best_url, best_length = False, 0
        for url in urls:
            url_path = self._strip_lang_prefix(urlsplit(url).path).rstrip('/')
            if not url_path:
                continue
            if (path == url_path or path.startswith(url_path + '/')) and len(url_path) > best_length:
                best_url, best_length = url, len(url_path)
        return best_url

    @api.model
    def _strip_lang_prefix(self, path):
        """Remove the website language prefix (/es/my/orders -> /my/orders)."""
        lang = request and getattr(request, 'lang', None)
        url_code = lang and lang.url_code
        if url_code and path.startswith('/%s/' % url_code):
            return path[len(url_code) + 1:]
        return path
