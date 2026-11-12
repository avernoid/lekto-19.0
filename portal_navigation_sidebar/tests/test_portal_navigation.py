from types import SimpleNamespace
from unittest.mock import patch

from lxml import html as lxml_html

from odoo.tests import HttpCase, TransactionCase, tagged
from odoo.tools import mute_logger

from odoo.addons.mail.tests.common import mail_new_test_user

NAVIGATION_MODULE = 'odoo.addons.portal_navigation_sidebar.models.portal_navigation'

# Same markup portal.portal_docs_entry produces in 19, one card per case.
HOME_HTML = """
<div class="o_portal_my_home"><div class="o_portal_docs row g-2">
  <div class="o_portal_category row g-2 mt-3" id="portal_alert_category">
    <div class="o_portal_index_card col-12 order-0">
      <a href="/my/quotes" title="Quotations to review" class="d-flex alert alert-primary">
        <span class="fw-bold" data-placeholder_count="quotation_count"></span>
      </a>
    </div>
  </div>
  <div class="o_portal_category row g-2 mt-3" id="portal_client_category">
    <div class="o_portal_index_card d-none col-md-6 order-2">
      <a href="/my/orders" title="Your Orders" class="d-flex bg-100">
        <div class="o_portal_icon d-none"><img src="/sale/static/src/img/bag.svg"/></div>
        <span class="d-none" data-placeholder_count="order_count"></span>
      </a>
    </div>
    <div class="o_portal_index_card d-none col-md-6 order-2">
      <a href="/my/hidden" title="Hidden by the home page" class="d-flex bg-100"></a>
    </div>
  </div>
  <div class="o_portal_category row g-2 mt-3" id="portal_common_category">
    <div class="o_portal_index_card col-md-6 order-2">
      <a href="/my/addresses" title="Addresses" class="d-flex bg-100"></a>
    </div>
    <div class="o_portal_index_card col-md-6 order-2">
      <a href="/my/addresses" title="Duplicated card" class="d-flex bg-100"></a>
    </div>
  </div>
</div></div>
"""


@tagged('post_install', '-at_install')
class TestPortalNavigationRules(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Navigation = cls.env['portal.navigation']

    def test_parse_keeps_one_entry_per_real_option(self):
        entries = self.Navigation._parse_home_entries(HOME_HTML)
        self.assertEqual(entries, [
            {
                'name': 'Your Orders',
                'url': '/my/orders',
                'icon': '/sale/static/src/img/bag.svg',
                'placeholder_count': 'order_count',
                'category': 'client_category',
                'always_visible': False,
            },
            {
                'name': 'Addresses',
                'url': '/my/addresses',
                'icon': False,
                'placeholder_count': False,
                'category': 'common_category',
                'always_visible': True,
            },
        ], "Alert cards, cards the home page hides and duplicated urls must not reach the menu")

    def test_counter_options_wait_for_documents(self):
        catalog = self.Navigation._parse_home_entries(HOME_HTML)

        entries = self.Navigation._build_entries(catalog, {}, '/my/addresses')
        self.assertEqual(
            [(e['url'], e['visible'], e['active'], e['group_start']) for e in entries],
            [('/my/orders', False, False, False), ('/my/addresses', True, True, True)],
            "Without a cached counter the option stays hidden until /my/counters answers",
        )

        entries = self.Navigation._build_entries(catalog, {'order_count': True}, '/my/addresses')
        self.assertTrue(entries[0]['visible'], "A counter cached as non-empty shows the option on load")

        entries = self.Navigation._build_entries(catalog, {'order_count': False}, '/my/orders/page/2')
        self.assertTrue(
            entries[0]['visible'] and entries[0]['active'],
            "The current option is always shown, even with no documents left",
        )

    def test_active_option_is_the_longest_matching_path(self):
        urls = ['/my/invoices', '/my/invoices/overdue', '/my/orders?sortby=date']
        get_active = self.Navigation._get_active_url
        self.assertEqual(get_active(urls, '/my/invoices'), '/my/invoices')
        self.assertEqual(get_active(urls, '/my/invoices/page/3'), '/my/invoices')
        self.assertEqual(get_active(urls, '/my/invoices/overdue/page/2'), '/my/invoices/overdue')
        self.assertEqual(get_active(urls, '/my/orders'), '/my/orders?sortby=date', "The query string is ignored")
        self.assertFalse(get_active(urls, '/my/invoices_report'), "A longer sibling path is not a match")

    def test_language_prefix_is_ignored_on_both_sides(self):
        # The website writes /es/ in the links of the home page and in the
        # current URL; seen on a real portal in Spanish.
        fake_request = SimpleNamespace(lang=SimpleNamespace(url_code='es'))
        with patch('odoo.addons.portal_navigation_sidebar.models.portal_navigation.request', fake_request):
            path = self.Navigation._strip_lang_prefix('/es/my/orders/page/2')
            self.assertEqual(path, '/my/orders/page/2')
            self.assertEqual(
                self.Navigation._get_active_url(['/es/my/tickets', '/es/my/orders'], path), '/es/my/orders',
            )
            self.assertEqual(self.Navigation._strip_lang_prefix('/estate/my'), '/estate/my')

    def test_catalog_is_rendered_once_until_templates_change(self):
        renders = []

        def render_home(navigation):
            renders.append(1)
            return HOME_HTML

        self.env.registry.clear_cache('templates')
        with patch.object(type(self.Navigation), '_render_home', render_home):
            args = ('en_US', False, (-1,))
            first = self.Navigation._get_catalog(*args)
            self.Navigation._get_catalog(*args)
            self.assertEqual(len(renders), 1, "Second call must come from the cache")
            self.assertEqual([e['url'] for e in first], ['/my/orders', '/my/addresses'])

            self.Navigation._get_catalog('es_PE', False, (-1,))
            self.assertEqual(len(renders), 2, "Another language renders its own catalog")

            self.env.registry.clear_cache('templates')
            self.Navigation._get_catalog(*args)
            self.assertEqual(len(renders), 3, "A view or module change renders the catalog again")

    def test_pages_outside_portal_layout_only_get_the_menu_on_an_option(self):
        """/my/payment_method skips portal_layout: the frontend layout asks
        with require_active, so the menu shows there and never on a shop or
        blog page of the same logged-in user."""
        portal_user = mail_new_test_user(self.env, login='portal_nav_rules', groups='base.group_portal')
        navigation = self.Navigation.with_user(portal_user)
        catalog = tuple(self.Navigation._parse_home_entries(HOME_HTML))

        def fake_request(path):
            return SimpleNamespace(
                httprequest=SimpleNamespace(path=path), session={}, website=None, lang=None,
            )

        with patch.object(type(self.Navigation), '_get_catalog', lambda *args: catalog):
            with patch(NAVIGATION_MODULE + '.request', fake_request('/my/addresses')):
                entries = navigation._get_navigation_entries(require_active=True)
                self.assertEqual([e['url'] for e in entries if e['active']], ['/my/addresses'])
            with patch(NAVIGATION_MODULE + '.request', fake_request('/shop')):
                self.assertEqual(navigation._get_navigation_entries(require_active=True), [])
                self.assertEqual(
                    len(navigation._get_navigation_entries()), 2,
                    "Portal layout pages keep the menu even when no option matches",
                )
            fake = fake_request('/my/addresses')
            fake.portal_navigation_probe = True
            with patch(NAVIGATION_MODULE + '.request', fake):
                self.assertEqual(
                    navigation._get_navigation_entries(), [],
                    "While the home page is rendered to build the menu, its layouts get no menu",
                )


@tagged('post_install', '-at_install')
class TestPortalNavigationPages(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_user = mail_new_test_user(
            cls.env, login='portal_nav_user', password='portal_nav_user', groups='base.group_portal',
        )

    def setUp(self):
        super().setUp()
        self.env.registry.clear_cache('templates')

    def _get_navigation(self, url):
        response = self.url_open(url)
        self.assertEqual(response.status_code, 200)
        return lxml_html.fromstring(response.content).xpath("//nav[hasclass('o_portal_navigation')]")

    def test_list_page_shows_home_options_with_current_one_active(self):
        self.authenticate('portal_nav_user', 'portal_nav_user')
        navigation = self._get_navigation('/my/security')
        self.assertEqual(len(navigation), 1)
        links = {link.get('href'): link for link in navigation[0].xpath('.//a')}
        self.assertIn('/my/addresses', links, "Options come from the cards of the real home page")
        self.assertIn('/my/security', links)
        self.assertEqual(links['/my/security'].get('aria-current'), 'page')
        self.assertIsNone(links['/my/addresses'].get('aria-current'))

    def test_mobile_button_names_the_current_section_and_opens_the_panel(self):
        self.authenticate('portal_nav_user', 'portal_nav_user')
        navigation = self._get_navigation('/my/security')[0]
        toggle = navigation.xpath(".//button[hasclass('o_portal_navigation_toggle')]")[0]
        active_name = navigation.xpath('.//a[@aria-current="page"]')[0].get('title')
        self.assertEqual(toggle.text_content().strip(), active_name)
        panel_id = toggle.get('data-bs-target').lstrip('#')
        panel = navigation.xpath('.//*[@id=$id]', id=panel_id)
        self.assertEqual(len(panel), 1)
        self.assertTrue(panel[0].xpath('.//a[@aria-current="page"]'), "The panel holds the options")

    def test_portal_page_without_layout_values_gets_the_menu(self):
        # /my/addresses renders portal_layout without calling
        # _prepare_portal_layout_values, like many custom portal pages.
        self.authenticate('portal_nav_user', 'portal_nav_user')
        navigation = self._get_navigation('/my/addresses')
        self.assertEqual(len(navigation), 1)
        self.assertEqual(navigation[0].xpath('.//a[@aria-current="page"]/@href'), ['/my/addresses'])

    def test_home_page_keeps_its_cards_only(self):
        self.authenticate('portal_nav_user', 'portal_nav_user')
        self.assertFalse(self._get_navigation('/my'), "The home page already is the menu")

    @mute_logger('odoo.addons.portal_navigation_sidebar.models.portal_navigation')
    def test_broken_home_page_never_breaks_the_list_page(self):
        self.authenticate('portal_nav_user', 'portal_nav_user')
        with patch.object(
            type(self.env['portal.navigation']), '_render_home', side_effect=ValueError('broken card'),
        ):
            self.assertFalse(self._get_navigation('/my/security'), "The page shows without the menu")
        self.assertTrue(self._get_navigation('/my/security'), "The failure is not cached: next request has the menu")
