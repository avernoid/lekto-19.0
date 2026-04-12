from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.saas_orchestrator.models.utils import (
    SLUG_MAX_LENGTH,
    SLUG_MIN_LENGTH,
    SLUG_REGEX,
    build_instance_name,
    sanitize_slug,
)


@tagged('post_install', '-at_install')
class TestSlugSanitization(TransactionCase):

    def _assert_valid_slug(self, slug):
        self.assertIsNotNone(SLUG_REGEX.match(slug),
                             f"Slug {slug!r} does not match API regex")
        self.assertGreaterEqual(len(slug), SLUG_MIN_LENGTH,
                                f"Slug {slug!r} shorter than min length")
        self.assertLessEqual(len(slug), SLUG_MAX_LENGTH,
                             f"Slug {slug!r} longer than max length")

    # ------------------------------------------------------------------
    # sanitize_slug
    # ------------------------------------------------------------------
    def test_basic_spaces(self):
        self.assertEqual(sanitize_slug('Acme Corp'), 'acme-corp')

    def test_accents_stripped(self):
        self.assertEqual(sanitize_slug('Café Olé'), 'cafe-ole')

    def test_enye_and_special_chars(self):
        self.assertEqual(sanitize_slug('Niño & Cía'), 'nino-cia')

    def test_surrounding_whitespace(self):
        self.assertEqual(sanitize_slug('  hello  world  '), 'hello-world')

    def test_uppercase(self):
        self.assertEqual(sanitize_slug('UPPER'), 'upper')

    def test_only_special_chars_uses_fallback(self):
        self.assertEqual(sanitize_slug('!@#'), 'item')

    def test_empty_string_uses_fallback(self):
        self.assertEqual(sanitize_slug(''), 'item')

    def test_none_uses_fallback(self):
        self.assertEqual(sanitize_slug(None), 'item')

    def test_short_string_padded_with_fallback(self):
        self.assertEqual(sanitize_slug('a'), 'a-item')

    def test_long_string_truncated_to_max(self):
        result = sanitize_slug('a' * 100)
        self.assertEqual(len(result), SLUG_MAX_LENGTH)

    def test_leading_trailing_hyphens_stripped(self):
        self.assertEqual(sanitize_slug('---hello---'), 'hello')

    def test_consecutive_hyphens_collapsed(self):
        self.assertEqual(sanitize_slug('hello---world'), 'hello-world')

    def test_all_outputs_match_regex(self):
        for raw in [
            'Acme Corp', 'Café Olé', 'Niño & Cía', '  hello  world  ',
            'UPPER', '!@#', '', None, 'a', 'a' * 100,
            '---hello---', 'hello---world',
        ]:
            result = sanitize_slug(raw)
            self._assert_valid_slug(result)

    # ------------------------------------------------------------------
    # build_instance_name
    # ------------------------------------------------------------------
    def test_build_normal(self):
        result = build_instance_name('Acme Corp', 'OpenClaw', 42)
        self.assertEqual(result, 'acme-corp-openclaw-42')
        self._assert_valid_slug(result)

    def test_build_with_accents(self):
        result = build_instance_name('Café Olé', 'OpenClaw', 1)
        self.assertEqual(result, 'cafe-ole-openclaw-1')
        self._assert_valid_slug(result)

    def test_build_long_partner_name(self):
        result = build_instance_name('A' * 100, 'OpenClaw', 1)
        self.assertLessEqual(len(result), SLUG_MAX_LENGTH)
        self.assertTrue(result.endswith('-openclaw-1'),
                        f"Expected to end with -openclaw-1, got {result!r}")
        self._assert_valid_slug(result)

    def test_build_empty_partner(self):
        result = build_instance_name('', 'OpenClaw', 1)
        self._assert_valid_slug(result)

    def test_build_empty_blueprint(self):
        result = build_instance_name('Acme', '', 1)
        self._assert_valid_slug(result)
