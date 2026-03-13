from odoo.tests.common import HttpCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestEcommerceSeoProtection(HttpCase):
    """Integration tests for website_seo_protection in an eCommerce context.

    With website_sale installed, routes like /shop and /shop/product/... are
    active. This module ensures that:

    1. The appointment crawler guard does NOT block eCommerce routes, even
       if a domain= query param contains a datetime-like value.
    2. Standard /shop pages are not modified (no unexpected X-Robots-Tag).
    3. Layer 1 still correctly blocks /appointment traps (regression).

    Pattern: same as website_seo_protection_appointment — glue module that
    auto-installs when website_seo_protection + website_sale are both present,
    enabling tests against real routes.
    """

    def _get(self, path):
        """Perform a GET request as a public user and return the response."""
        self.authenticate(None, None)
        return self.url_open(path, allow_redirects=False)

    # -------------------------------------------------------------------------
    # Negative tests: guard must NOT block eCommerce routes
    # -------------------------------------------------------------------------

    def test_shop_not_blocked(self):
        """Negative: /shop must return 200, not 404 (not an appointment path)."""
        response = self._get('/shop')
        self.assertEqual(
            response.status_code, 200,
            "/shop must be accessible — it is not an appointment path"
        )

    def test_shop_with_domain_not_blocked(self):
        """Negative: /shop?domain=... must NOT be blocked even if it resembles an appointment trap.

        The guard only targets paths matching /appointment. Any other path
        (including /shop) must pass through untouched regardless of query params.
        """
        path = "/shop?domain=('create_date','>=',datetime.datetime(2026,3,12,0,0,0))"
        response = self._get(path)
        self.assertNotEqual(
            response.status_code, 404,
            "/shop with domain=datetime(...) must NOT be blocked — only /appointment is targeted"
        )

    def test_shop_with_domain_has_no_robots_header(self):
        """/shop?domain= must not get an X-Robots-Tag injected by our module."""
        path = "/shop?domain=('create_date','>=',datetime.datetime(2026,3,12,0,0,0))"
        response = self._get(path)
        if response.status_code == 200:
            self.assertNotIn(
                'X-Robots-Tag', response.headers,
                "/shop must not have X-Robots-Tag injected by the SEO protection guard"
            )

    def test_shop_page_not_blocked(self):
        """Negative: /shop/page/2 must not be affected."""
        response = self._get('/shop/page/2')
        # 200 or 404 (if only 1 page of products) — just must NOT be our guard's 404
        # We check by ensuring X-Robots-Tag: noindex is not the cause
        self.assertNotEqual(
            response.headers.get('X-Robots-Tag'), 'noindex',
            "/shop/page/2 must not get X-Robots-Tag: noindex from our guard"
        )

    # -------------------------------------------------------------------------
    # Regression: Layer 1 must still block /appointment trap
    # -------------------------------------------------------------------------

    def test_layer1_still_blocks_appointment_trap_with_shop_installed(self):
        """Regression: /appointment trap must still return 404 even with website_sale installed."""
        path = (
            "/appointment/page/2"
            "?domain=('end_datetime','>=',datetime.datetime(2026,3,12,14,12,29,664830))"
        )
        response = self._get(path)
        self.assertEqual(
            response.status_code, 404,
            "Crawler trap must still return 404 even when website_sale is installed"
        )
        self.assertEqual(
            response.headers.get('X-Robots-Tag'), 'noindex',
            "Blocked crawler trap must still have X-Robots-Tag: noindex"
        )
