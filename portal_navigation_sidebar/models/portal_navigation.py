import logging
from urllib.parse import urlsplit

from lxml import html as lxml_html

from odoo import api, models, tools
from odoo.http import request

_logger = logging.getLogger(__name__)

# XPath test for one CSS class inside a space-separated class attribute.
_HAS_CLASS = "contains(concat(' ', normalize-space(@class), ' '), ' %s ')"


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
        if not request or getattr(request, 'portal_navigation_probe', False) or self.env.user._is_public():
            return []
        website = getattr(request, 'website', None)
        try:
            with self.env.cr.savepoint():
                catalog = self._get_catalog(
                    self.env.lang,
                    website.id if website else False,
                    tuple(sorted(self.env.user.all_group_ids.ids)),
                )
        except Exception:
            # A broken third-party card must never break the portal pages:
            # the page shows without the sidebar, and nothing is cached so
            # the next request tries again.
            _logger.exception("Portal navigation: could not read the portal home page")
            return []
        entries = self._build_entries(
            catalog,
            request.session.get('portal_counters', {}),
            self._strip_lang_prefix(request.httprequest.path),
        )
        if require_active and not any(entry['active'] for entry in entries):
            return []
        return entries

    @tools.ormcache('lang', 'website_id', 'groups_key', cache='templates')
    def _get_catalog(self, lang, website_id, groups_key):
        """Options of the portal home page, as an immutable tuple of dicts.

        Users that share language, website and groups see the same cards, so
        they share the cache entry. The 'templates' cache is cleared whenever
        a view changes or a module is installed, which is exactly when the
        cards can change.

        ODOO-20: replace the rendering + parsing by the ``portal.entry``
        records that ``_prepare_portal_layout_values`` already returns as
        ``portal_cards`` (see doc/UPGRADE_20.md).
        """
        return tuple(self._parse_home_entries(self._render_home()))

    @api.model
    def _render_home(self):
        """Render /my exactly as ``CustomerPortal.home()`` does.

        Uses the controller instance Odoo routes /my to, so the values added
        by every installed app's override are there.

        ODOO-20: delete this method, see doc/UPGRADE_20.md.
        """
        controller = self._get_portal_controller()
        values = controller._prepare_portal_layout_values()
        values.update(controller._prepare_home_portal_values([]))
        values['request'] = request
        # The home page renders the layouts again: they must not ask for the
        # menu while it is being built.
        request.portal_navigation_probe = True
        try:
            return request.env['ir.ui.view']._render_template('portal.portal_my_home', values)
        finally:
            request.portal_navigation_probe = False

    @api.model
    def _get_portal_controller(self):
        """The controller instance routed for /my, with all its overrides."""
        for rule in request.env['ir.http'].routing_map().iter_rules():
            if rule.rule == '/my':
                return rule.endpoint.func.__self__
        raise LookupError("No controller is routed for /my")

    @api.model
    def _parse_home_entries(self, home_html):
        """Extract the cards of the rendered /my page.

        Relies only on the markup of ``portal.portal_docs_entry``: one
        ``.o_portal_index_card`` per option, inside a ``.o_portal_category``
        container whose id names the category.

        * Alert cards ("Quotations to review"...) are skipped: they point to a
          filtered view of an option that already has its own card.
        * Cards without counter that the home page hides are skipped too.
        * Cards with a counter are kept: their visibility depends on the
          documents of each user and is decided per request.
        """
        if not home_html:
            return []
        tree = lxml_html.fromstring(str(home_html))
        entries = []
        seen_urls = set()
        for card in tree.xpath('//div[%s]' % (_HAS_CLASS % 'o_portal_index_card')):
            links = card.xpath('.//a[@href]')
            if not links:
                continue
            link = links[0]
            url = link.get('href')
            if 'alert' in link.get('class', '').split() or url in seen_urls:
                continue
            counters = card.xpath('.//*[@data-placeholder_count]')
            placeholder_count = counters[0].get('data-placeholder_count') if counters else False
            if not placeholder_count and 'd-none' in card.get('class', '').split():
                continue
            category = card.xpath('ancestor::div[%s][1]' % (_HAS_CLASS % 'o_portal_category'))
            icons = card.xpath('.//div[%s]//img/@src' % (_HAS_CLASS % 'o_portal_icon'))
            seen_urls.add(url)
            entries.append({
                'name': (link.get('title') or link.text_content()).strip(),
                'url': url,
                'icon': icons[0] if icons else False,
                'placeholder_count': placeholder_count,
                'category': (category[0].get('id') or '').removeprefix('portal_') if category else 'common_category',
                'always_visible': not placeholder_count,
            })
        return entries

    @api.model
    def _build_entries(self, catalog, counters_cache, path):
        """Decide visibility and the active option for one request.

        :param catalog: entries from ``_get_catalog``: dicts with ``name``,
            ``url``, ``icon``, ``placeholder_count``, ``category`` and
            ``always_visible`` (shown whatever the documents). This is the
            contract both versions share: in 20 only the catalog source changes.
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
        links of the home page (/es/my/invoices): it is ignored on both sides.
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
