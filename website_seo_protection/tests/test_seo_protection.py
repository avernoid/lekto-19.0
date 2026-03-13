from odoo.tests.common import HttpCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSeoProtection(HttpCase):
    """Test the SEO protection layers implemented in website_seo_protection.

    Layer 1: Appointment URLs with ?domain=datetime(...) must return HTTP 404.
    Layer 3 (negative): Non-appointment URLs must be unaffected (no extra headers injected).
    """

    def _get(self, path):
        """Perform a GET request as a public user and return the response."""
        self.authenticate(None, None)
        return self.url_open(path, allow_redirects=False)

    def test_layer1_trap_a_domain_datetime_returns_404(self):
        """Trap A: ?domain= with datetime.datetime(...) → must get HTTP 404."""
        path = (
            "/appointment?domain=('end_datetime','>=',datetime.datetime"
            "(2026,3,12,14,12,29,664830))"
        )
        response = self._get(path)
        self.assertEqual(
            response.status_code, 404,
            "Crawler trap URL with ?domain=datetime(...) must return 404"
        )
        self.assertEqual(
            response.headers.get('X-Robots-Tag'), 'noindex',
            "Crawler trap URL must have X-Robots-Tag: noindex"
        )

    def test_layer1_trap_a_encoded_colon_returns_404(self):
        """Trap A variant: URL-encoded colon (%3a) in ?domain= → must get HTTP 404."""
        # %3a = ':' which appears in timestamps like 2026-03-13 05:32:11
        path = "/appointment/page/2?domain=('end_datetime','>=','2026%3a12%3a29')"
        response = self._get(path)
        self.assertEqual(
            response.status_code, 404,
            "Crawler trap URL with URL-encoded colon must return 404"
        )

    def test_layer1_lang_prefix_en_appointment_trap_is_blocked(self):
        """Regression: /en/appointment trap must NOT return 200 (lang prefix support).

        Production logs from 2026-03-13 show Meta bot (57.141.4.x) hitting
        /en/appointment/page/N?domain=...datetime.datetime(...)... and receiving 200.
        After the regex fix, these must NOT return 200.
        Acceptable outcomes: 404 (blocked by our guard) or 3xx (redirected by Odoo
        lang middleware before reaching our guard — also safe for bots).
        """
        path = (
            "/en/appointment/page/4"
            "?domain=%26&domain=('end_datetime',+datetime.datetime(2026,3,13,5,54,26,604179))"
        )
        response = self._get(path)
        self.assertNotEqual(
            response.status_code, 200,
            "/en/appointment trap must NOT return 200 — bot must not get content"
        )

    def test_no_extra_headers_on_non_appointment_routes(self):
        """Negative: routes outside /appointment must not be blocked.

        /web/login always exists in any Odoo install (no website_appointment needed).
        It must never return 404 from our guard, and must not have our X-Robots-Tag.
        """
        response = self._get('/web/login')
        self.assertNotEqual(
            response.status_code, 404,
            "/web/login must not be blocked by the appointment crawler guard"
        )
        self.assertNotEqual(
            response.headers.get('X-Robots-Tag'), 'noindex, nofollow',
            "/web/login must not have the appointment X-Robots-Tag injected"
        )

    def test_layer1_non_appointment_domain_not_blocked(self):
        """Negative: ?domain=datetime on a non-appointment route must NOT return 404.

        Uses the website homepage (/) which is always available when 'website' is installed.
        We must not block this route even though it contains ?domain=datetime.
        """
        path = "/?domain=('some_field','=',datetime.datetime(2026,3,12))"
        response = self._get(path)
        # The homepage with a benign ?domain= param must never be blocked by our guard
        self.assertNotEqual(
            response.status_code, 404,
            "Non-appointment homepage route with ?domain=datetime must NOT be blocked"
        )
        # Our header must not be injected on non-appointment routes
        self.assertNotEqual(
            response.headers.get('X-Robots-Tag'), 'noindex',
            "Non-appointment routes must not get the crawler-trap noindex header"
        )

