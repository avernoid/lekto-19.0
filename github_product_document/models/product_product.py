import base64
import io
import logging
import os
import tempfile
import zipfile

import requests

from odoo import _, fields, models

_logger = logging.getLogger(__name__)

try:
    from pygount import SourceAnalysis
except ImportError:
    _logger.debug("Cannot import 'pygount' python library.")
    SourceAnalysis = None


class ProductProduct(models.Model):
    _inherit = 'product.product'

    github_branch_id = fields.Many2one(
        comodel_name='github.repository.branch',
        string='GitHub Branch',
        help='Link this product variant to a specific GitHub repository branch. '
             'When set, you can click "Sync GitHub Doc" to download the source code '
             'as a ZIP file and store it as a product.document. The ZIP will be '
             'delivered to the customer when they confirm a sale order containing '
             'this variant. Example: Link variant "18.0" to branch "18.0" of '
             'your module repository.',
    )
    github_doc_needs_update = fields.Boolean(
        string='GitHub Doc Needs Update',
        default=False,
        help='When True, indicates that the linked GitHub repository has been '
             'updated since the last ZIP was generated. The scheduled action '
             '"GitHub: Update Stale Product Documents" (runs every 12 hours) '
             'will automatically download a fresh ZIP and reset this flag to False. '
             'You can also manually click "Sync GitHub Doc" to update immediately.',
    )
    lines_of_code = fields.Integer(
        string='Lines of Code',
        readonly=True,
        help='Total lines of source code counted from the GitHub ZIP archive '
             'stored in this variant. Updated when you click "Count Lines of Code". '
             'Uses pygount to identify and count code lines (excludes comments, '
             'blanks, and binary files).',
    )
    lines_of_code_date = fields.Datetime(
        string='Last Code Count',
        readonly=True,
        help='Date and time of the last successful lines-of-code count.',
    )

    def button_sync_github_doc(self):
        """Sync GitHub document for selected variants. Works from form or list view."""
        for variant in self:
            variant._sync_github_document()

    def _sync_github_document(self):
        """Download ZIP from GitHub and create/update product.document."""
        self.ensure_one()
        branch = self.github_branch_id
        if not branch:
            _logger.info(
                "GITHUB DOC: Variant [%s] has no branch linked. Skipping.",
                self.display_name,
            )
            return

        repo = branch.repository_id
        org = repo.organization_id

        # Get GitHub connector and fetch the archive URL
        gh_api = org.get_github_connector()
        try:
            gh_repo = gh_api.get_repo('%s/%s' % (org.github_name, repo.name))
            archive_url = gh_repo.get_archive_link('zipball', branch.name)
        except Exception as e:
            _logger.error(
                "GITHUB DOC: Failed to get archive link for [%s/%s:%s]. Error: %s",
                org.github_name, repo.name, branch.name, str(e),
            )
            return

        # Download the ZIP content
        try:
            response = requests.get(archive_url, timeout=120)
            response.raise_for_status()
            zip_content = response.content
        except Exception as e:
            _logger.error(
                "GITHUB DOC: Failed to download ZIP for [%s:%s]. Error: %s",
                repo.name, branch.name, str(e),
            )
            return

        zip_base64 = base64.b64encode(zip_content)
        file_name = '%s-%s.zip' % (repo.name, branch.name)

        _logger.info(
            "GITHUB DOC: Downloaded [%s] (%d bytes)",
            file_name, len(zip_content),
        )

        # Search for existing product.document for this variant
        ProductDocument = self.env['product.document']
        existing_doc = ProductDocument.search([
            ('res_model', '=', 'product.product'),
            ('res_id', '=', self.id),
            ('name', 'like', '%s%%' % repo.name),
        ], limit=1)

        doc_vals = {
            'name': file_name,
            'datas': zip_base64,
            'type': 'binary',
            'attached_on_sale': 'sale_order',
            'res_model': 'product.product',
            'res_id': self.id,
        }

        if existing_doc:
            existing_doc.write({
                'name': file_name,
                'datas': zip_base64,
            })
            _logger.info(
                "GITHUB DOC: Updated existing document [%s] for variant [%s].",
                file_name, self.display_name,
            )
        else:
            ProductDocument.create(doc_vals)
            _logger.info(
                "GITHUB DOC: Created new document [%s] for variant [%s].",
                file_name, self.display_name,
            )

        self.github_doc_needs_update = False

    def _cron_sync_github_documents(self):
        """Cron method: sync all variants with stale GitHub documents."""
        variants = self.search([
            ('github_doc_needs_update', '=', True),
            ('github_branch_id', '!=', False),
        ])
        _logger.info(
            "GITHUB DOC CRON: Found %d variants needing update.", len(variants),
        )
        for variant in variants:
            try:
                variant._sync_github_document()
            except Exception as e:
                _logger.error(
                    "GITHUB DOC CRON: Error syncing variant [%s]: %s",
                    variant.display_name, str(e),
                )

    def button_count_lines_of_code(self):
        """Count lines of code from the stored ZIP in product.document."""
        for variant in self:
            variant._count_lines_of_code()

    def _count_lines_of_code(self):
        """Extract ZIP from product.document, count code lines with pygount."""
        self.ensure_one()
        if not SourceAnalysis:
            _logger.error(
                "GITHUB DOC: pygount is not installed. Cannot count lines."
            )
            return

        # Find the product.document ZIP for this variant
        doc = self.env['product.document'].search([
            ('res_model', '=', 'product.product'),
            ('res_id', '=', self.id),
            ('name', 'like', '%.zip'),
        ], limit=1)

        if not doc or not doc.datas:
            _logger.info(
                "GITHUB DOC: No ZIP document found for variant [%s]. "
                "Run 'Sync GitHub Doc' first.",
                self.display_name,
            )
            return

        # Decode and extract ZIP to a temporary directory
        try:
            zip_data = base64.b64decode(doc.datas)
            with tempfile.TemporaryDirectory() as tmp_dir:
                with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                    zf.extractall(tmp_dir)

                # Count code lines with pygount
                total_code = 0
                for root, _dirs, files in os.walk(tmp_dir):
                    if '/.git' in root or '\\.git' in root:
                        continue
                    for filename in files:
                        if filename == '.gitignore':
                            continue
                        filepath = os.path.join(root, filename)
                        try:
                            analysis = SourceAnalysis.from_file(filepath, "")
                            total_code += analysis._code
                        except Exception:
                            continue

                self.write({
                    'lines_of_code': total_code,
                    'lines_of_code_date': fields.Datetime.now(),
                })
                _logger.info(
                    "GITHUB DOC: Counted %d lines of code for variant [%s].",
                    total_code, self.display_name,
                )
        except zipfile.BadZipFile:
            _logger.error(
                "GITHUB DOC: Invalid ZIP file for variant [%s].",
                self.display_name,
            )

