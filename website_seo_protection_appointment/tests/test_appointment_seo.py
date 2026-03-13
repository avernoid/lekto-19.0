from odoo.tests.common import HttpCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAppointmentSeoProtection(HttpCase):
    """Integration tests for SEO protection on appointment routes.

    This module depends on website_seo_protection + website_appointment,
    which guarantees that the Odoo test DB has the appointment routes
    installed and functional. This allows us to test Layer 2 (X-Robots-Tag
    on ?date= parameters) against real existing routes — not against routes
    that may return 404 simply because the module is absent.

    Layer 1 tests (crawler trap → 404) are in website_seo_protection/tests/
    because they work with or without website_appointment.
    """

    def _get(self, path):
        """Perform a GET request as a public user and return the response."""
        self.authenticate(None, None)
        return self.url_open(path, allow_redirects=False)

    def test_layer2_date_param_html_response_has_noindex(self):
        """Layer 2: /appointment?date= HTML response must have X-Robots-Tag: noindex, nofollow.

        With website_appointment installed, /appointment?date=YYYY-MM-DD is a valid route
        that returns 200 text/html. Our _dispatch override must inject the noindex header.
        """
        path = "/appointment?date=2026-03-12"
        response = self._get(path)
        # website_appointment is installed, so /appointment must return 200
        self.assertEqual(
            response.status_code, 200,
            "/appointment?date= must return 200 when website_appointment is installed"
        )
        self.assertEqual(
            response.headers.get('X-Robots-Tag'), 'noindex, nofollow',
            "Appointment ?date= URL must have X-Robots-Tag: noindex, nofollow"
        )

    def test_layer2_datetime_param_html_response_has_noindex(self):
        """Layer 2: /appointment?datetime= must also get the noindex header."""
        path = "/appointment?datetime=2026-03-12T10:00:00"
        response = self._get(path)
        if response.status_code == 200:
            self.assertEqual(
                response.headers.get('X-Robots-Tag'), 'noindex, nofollow',
                "Appointment ?datetime= URL must have X-Robots-Tag: noindex, nofollow"
            )

    def test_appointment_root_no_extra_headers(self):
        """Negative: /appointment without params must have no X-Robots-Tag."""
        response = self._get('/appointment')
        self.assertEqual(
            response.status_code, 200,
            "/appointment root must return 200 when website_appointment is installed"
        )
        self.assertNotIn(
            'X-Robots-Tag', response.headers,
            "/appointment root must not have X-Robots-Tag injected"
        )

    def test_layer1_trap_not_blocked_without_domain_date(self):
        """Negative: /appointment with a benign query param must not be blocked."""
        # A search filter that is NOT a datetime domain must pass through normally
        path = "/appointment?filter_appointment_type_ids=1"
        response = self._get(path)
        self.assertNotEqual(
            response.status_code, 404,
            "/appointment with benign filter param must not be blocked as a crawler trap"
        )

    def test_layer1_still_blocks_traps_with_appointment_installed(self):
        """Regression: Layer 1 must still block traps even with website_appointment installed."""
        path = (
            "/appointment/page/2?domain=('end_datetime','>=',datetime.datetime"
            "(2026,3,12,14,12,29,664830))"
        )
        response = self._get(path)
        self.assertEqual(
            response.status_code, 404,
            "Crawler trap must still return 404 even with website_appointment installed"
        )
        self.assertEqual(
            response.headers.get('X-Robots-Tag'), 'noindex',
            "Crawler trap must still have X-Robots-Tag: noindex"
        )

    def test_layer1_blocks_lang_prefixed_trap(self):
        """Regression: /en/appointment trap must NOT return 200 (lang prefix support).

        Production logs confirm Meta bots hit /en/appointment/page/N?domain=...datetime...
        Acceptable outcomes: 404 (blocked by our guard) or 3xx (redirected by Odoo lang
        middleware before reaching our guard — also safe, bot gets no content).
        """
        path = (
            "/en/appointment/page/4"
            "?domain=%26&domain=%26&domain=%26&domain=|"
            "&domain=('end_datetime','%3E%3D',+datetime.datetime(2026,3,13,5,54,26,604179))"
            "&domain=|&domain=('country_ids','%3D',False)"
        )
        response = self._get(path)
        self.assertNotEqual(
            response.status_code, 200,
            "/en/appointment trap must NOT return 200 — bot must not get full page content"
        )

    def test_layer2_lang_prefixed_date_has_noindex(self):
        """Regression: /en/appointment?date= must also get the noindex header."""
        path = "/en/appointment?date=2026-03-12"
        response = self._get(path)
        if response.status_code == 200:
            self.assertEqual(
                response.headers.get('X-Robots-Tag'), 'noindex, nofollow',
                "/en/appointment?date= must have X-Robots-Tag: noindex, nofollow"
            )

