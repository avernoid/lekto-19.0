import json
import inspect
from odoo.tests.common import HttpCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSeoProtection(HttpCase):
    """Test the SEO protection layers in website_seo_protection.

    Uses _pre_dispatch (Layer 1: block traps) and _post_dispatch (Layer 2: headers).
    _dispatch is intentionally NOT overridden so this module never appears
    in downstream error tracebacks.
    """

    def _get(self, path):
        """Perform a GET request as a public user and return the response."""
        self.authenticate(None, None)
        return self.url_open(path, allow_redirects=False)

    def test_layer1_trap_a_domain_datetime_returns_404(self):
        """Trap A: ?domain= with datetime.datetime(...) -> must get HTTP 404."""
        path = (
            "/appointment?domain=('end_datetime','>=',datetime.datetime"
            "(2026,3,12,14,12,29,664830))"
        )
        response = self._get(path)
        self.assertEqual(
            response.status_code, 404,
            "Crawler trap URL with ?domain=datetime(...) must return 404"
        )

    def test_layer1_trap_a_encoded_colon_returns_404(self):
        """Trap A variant: URL-encoded colon (%3a) in ?domain= -> must get HTTP 404."""
        path = "/appointment/page/2?domain=('end_datetime','>=','2026%3a12%3a29')"
        response = self._get(path)
        self.assertEqual(
            response.status_code, 404,
            "Crawler trap URL with URL-encoded colon must return 404"
        )

    def test_layer1_lang_prefix_en_appointment_trap_is_blocked(self):
        """Regression: /en/appointment trap must NOT return 200 (lang prefix support)."""
        path = (
            "/en/appointment/page/4"
            "?domain=%26&domain=('end_datetime',+datetime.datetime(2026,3,13,5,54,26,604179))"
        )
        response = self._get(path)
        self.assertNotEqual(
            response.status_code, 200,
            "/en/appointment trap must NOT return 200 -- bot must not get content"
        )

    def test_no_extra_headers_on_non_appointment_routes(self):
        """Negative: routes outside /appointment must not be blocked."""
        response = self._get('/web/login')
        self.assertNotEqual(
            response.status_code, 404,
            "/web/login must not be blocked by the appointment crawler guard"
        )

    def test_layer1_non_appointment_domain_not_blocked(self):
        """Negative: ?domain=datetime on a non-appointment route must NOT return 404."""
        path = "/?domain=('some_field','=',datetime.datetime(2026,3,12))"
        response = self._get(path)
        self.assertNotEqual(
            response.status_code, 404,
            "Non-appointment homepage route with ?domain=datetime must NOT be blocked"
        )

    def test_rpc_endpoint_does_not_crash_with_attributeerror(self):
        """Regression: _post_dispatch must not crash when response is a dict.

        JSON-RPC endpoints return a plain dict, not a werkzeug Response.
        The isinstance() guard in _post_dispatch prevents AttributeError.
        """
        self.authenticate(None, None)
        payload = json.dumps({
            "jsonrpc": "2.0",
            "method": "call",
            "id": 1,
            "params": {
                "model": "res.lang",
                "method": "get_installed",
                "args": [],
                "kwargs": {},
            },
        }).encode()
        response = self.url_open(
            '/web/dataset/call_kw',
            data=payload,
            headers={'Content-Type': 'application/json'},
        )
        self.assertNotEqual(
            response.status_code, 500,
            "JSON-RPC call must not return HTTP 500 due to AttributeError on dict response."
        )

    def test_dispatch_not_overridden(self):
        """Structural: _dispatch must NOT be overridden by website_seo_protection.

        This is the core architectural invariant: by not overriding _dispatch,
        this module never appears in downstream error tracebacks (e.g. when a
        module with a bad PO file is installed). Errors from other modules
        will correctly show those modules as the source, not website_seo_protection.
        """
        from odoo.addons.website_seo_protection.models import ir_http as our_module

        # _dispatch must NOT be defined in our IrHttp class dict (only in parent)
        self.assertNotIn(
            '_dispatch',
            our_module.IrHttp.__dict__,
            "_dispatch must NOT be overridden by website_seo_protection. "
            "Override _dispatch puts this module in every HTTP error traceback, "
            "confusing developers about the real error source. "
            "Use _pre_dispatch (Layer 1) and _post_dispatch (Layer 2) instead."
        )

        # _pre_dispatch and _post_dispatch MUST be defined (our hooks)
        self.assertIn(
            '_pre_dispatch',
            our_module.IrHttp.__dict__,
            "_pre_dispatch must be overridden for Layer 1 (crawler trap blocking)"
        )
        self.assertIn(
            '_post_dispatch',
            our_module.IrHttp.__dict__,
            "_post_dispatch must be overridden for Layer 2 (X-Robots-Tag headers)"
        )
