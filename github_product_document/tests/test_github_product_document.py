# Copyright 2026 Ganemo
# License OPL-1

import base64
from unittest import mock

import odoo.tests

from odoo.addons.github_connector.tests.common import TestGithubConnectorCommon


FAKE_ZIP_CONTENT = b"PK\x03\x04fake_zip_bytes_for_testing"


@odoo.tests.tagged("post_install", "-at_install")
class TestGithubProductDocument(TestGithubConnectorCommon):
    """Tests for the github_product_document module.

    Covers: sync logic, staleness flag, cron, and the repo-sync hook.
    All GitHub API calls are mocked — no external requests are made.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create a product linked to a GitHub branch
        cls.product = cls.env['product.product'].create({
            'name': 'Test Module v13',
            'github_branch_id': cls.repository_ocb_13.id,
        })
        # A second product without a branch (control group)
        cls.product_no_branch = cls.env['product.product'].create({
            'name': 'Test Module No Branch',
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _mock_sync(self, product=None):
        """Run _sync_github_document with all GitHub API calls mocked."""
        product = product or self.product
        mock_gh_repo = mock.MagicMock()
        mock_gh_repo.get_archive_link.return_value = (
            "https://github.com/fake/archive/13.0.zip"
        )
        mock_connector = mock.MagicMock()
        mock_connector.get_repo.return_value = mock_gh_repo

        with mock.patch.object(
            type(self.oca), 'get_github_connector', return_value=mock_connector,
        ), mock.patch(
            'odoo.addons.github_product_document.models.product_product.requests.get',
        ) as mock_get:
            mock_response = mock.MagicMock()
            mock_response.content = FAKE_ZIP_CONTENT
            mock_response.raise_for_status = mock.MagicMock()
            mock_get.return_value = mock_response
            product._sync_github_document()

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------
    def test_sync_creates_product_document(self):
        """Syncing a variant with a branch should create a product.document."""
        self._mock_sync()
        doc = self.env['product.document'].search([
            ('res_model', '=', 'product.product'),
            ('res_id', '=', self.product.id),
        ], limit=1)
        self.assertTrue(doc, "product.document should be created after sync.")
        self.assertEqual(doc.name, 'OCB-13.0.zip')
        self.assertEqual(
            doc.datas,
            base64.b64encode(FAKE_ZIP_CONTENT),
        )
        self.assertEqual(doc.attached_on_sale, 'sale_order')

    def test_sync_updates_existing_document(self):
        """Running sync twice should update the existing document, not create a duplicate."""
        self._mock_sync()
        self._mock_sync()
        docs = self.env['product.document'].search([
            ('res_model', '=', 'product.product'),
            ('res_id', '=', self.product.id),
            ('name', 'like', 'OCB%'),
        ])
        self.assertEqual(
            len(docs), 1,
            "Only one product.document should exist after two syncs.",
        )

    def test_sync_resets_needs_update_flag(self):
        """After sync, the github_doc_needs_update flag must be False."""
        self.product.github_doc_needs_update = True
        self._mock_sync()
        self.assertFalse(
            self.product.github_doc_needs_update,
            "needs_update should be False after successful sync.",
        )

    def test_sync_skips_variant_without_branch(self):
        """Variant without a branch should be silently skipped."""
        self._mock_sync(self.product_no_branch)
        doc = self.env['product.document'].search([
            ('res_model', '=', 'product.product'),
            ('res_id', '=', self.product_no_branch.id),
        ], limit=1)
        self.assertFalse(
            doc,
            "No product.document should be created for a variant without a branch.",
        )

    def test_repo_sync_hook_marks_variants_stale(self):
        """When a repository is updated via _update_from_github_data,
        linked variants should be marked as needing update."""
        self.product.github_doc_needs_update = False
        # Simulate repository sync hook — data doesn't matter, just needs to call super
        self.repository_ocb._update_from_github_data({})
        self.assertTrue(
            self.product.github_doc_needs_update,
            "Variant should be marked needs_update after repo sync.",
        )

    def test_repo_sync_hook_does_not_affect_unlinked_variants(self):
        """Variants not linked to the synced repo should remain unaffected."""
        self.product_no_branch.github_doc_needs_update = False
        self.repository_ocb._update_from_github_data({})
        self.assertFalse(
            self.product_no_branch.github_doc_needs_update,
            "Unlinked variant should not be affected by repo sync.",
        )

    def test_cron_syncs_stale_variants(self):
        """The cron should sync all variants with needs_update = True."""
        self.product.github_doc_needs_update = True
        mock_gh_repo = mock.MagicMock()
        mock_gh_repo.get_archive_link.return_value = (
            "https://github.com/fake/archive/13.0.zip"
        )
        mock_connector = mock.MagicMock()
        mock_connector.get_repo.return_value = mock_gh_repo

        with mock.patch.object(
            type(self.oca), 'get_github_connector', return_value=mock_connector,
        ), mock.patch(
            'odoo.addons.github_product_document.models.product_product.requests.get',
        ) as mock_get:
            mock_response = mock.MagicMock()
            mock_response.content = FAKE_ZIP_CONTENT
            mock_response.raise_for_status = mock.MagicMock()
            mock_get.return_value = mock_response
            self.env['product.product']._cron_sync_github_documents()

        self.assertFalse(
            self.product.github_doc_needs_update,
            "Cron should have synced and reset the needs_update flag.",
        )
        doc = self.env['product.document'].search([
            ('res_model', '=', 'product.product'),
            ('res_id', '=', self.product.id),
        ], limit=1)
        self.assertTrue(doc, "Cron should have created the product.document.")

    def test_button_sync_works_for_recordset(self):
        """button_sync_github_doc should iterate over a multi-record recordset."""
        products = self.product | self.product_no_branch
        mock_gh_repo = mock.MagicMock()
        mock_gh_repo.get_archive_link.return_value = (
            "https://github.com/fake/archive/13.0.zip"
        )
        mock_connector = mock.MagicMock()
        mock_connector.get_repo.return_value = mock_gh_repo

        with mock.patch.object(
            type(self.oca), 'get_github_connector', return_value=mock_connector,
        ), mock.patch(
            'odoo.addons.github_product_document.models.product_product.requests.get',
        ) as mock_get:
            mock_response = mock.MagicMock()
            mock_response.content = FAKE_ZIP_CONTENT
            mock_response.raise_for_status = mock.MagicMock()
            mock_get.return_value = mock_response
            products.button_sync_github_doc()

        # Product with branch should have a document
        doc = self.env['product.document'].search([
            ('res_model', '=', 'product.product'),
            ('res_id', '=', self.product.id),
        ], limit=1)
        self.assertTrue(doc, "Product with branch should get a document via button.")
        # Product without branch should NOT have a document
        doc_no = self.env['product.document'].search([
            ('res_model', '=', 'product.product'),
            ('res_id', '=', self.product_no_branch.id),
        ], limit=1)
        self.assertFalse(doc_no, "Product without branch should be silently skipped.")

    # ------------------------------------------------------------------
    # Tests: Lines of Code Counter
    # ------------------------------------------------------------------
    def _create_test_zip_document(self, product):
        """Create a product.document with a real ZIP containing a Python file."""
        import io
        import zipfile

        py_content = (
            "# This is a test module\n"
            "import os\n"
            "\n"
            "def hello():\n"
            "    return 'world'\n"
            "\n"
            "def goodbye():\n"
            "    return 'farewell'\n"
        )

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('test_module/__init__.py', py_content)
            zf.writestr('test_module/__manifest__.py', "{'name': 'Test'}\n")
        zip_buffer.seek(0)

        return self.env['product.document'].create({
            'name': 'test-repo-18.0.zip',
            'datas': base64.b64encode(zip_buffer.read()),
            'type': 'binary',
            'res_model': 'product.product',
            'res_id': product.id,
        })

    def test_count_lines_of_code(self):
        """Counting lines should populate lines_of_code and timestamp."""
        self._create_test_zip_document(self.product)
        self.product.button_count_lines_of_code()
        self.assertGreater(
            self.product.lines_of_code, 0,
            "lines_of_code should be greater than 0 after counting.",
        )
        self.assertTrue(
            self.product.lines_of_code_date,
            "lines_of_code_date should be set after counting.",
        )

    def test_count_lines_without_zip(self):
        """Counting without a ZIP should not error and leave fields at default."""
        self.product.button_count_lines_of_code()
        self.assertEqual(
            self.product.lines_of_code, 0,
            "lines_of_code should remain 0 when no ZIP exists.",
        )
        self.assertFalse(
            self.product.lines_of_code_date,
            "lines_of_code_date should remain empty when no ZIP exists.",
        )

