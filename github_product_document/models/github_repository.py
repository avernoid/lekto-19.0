import logging

from odoo import models

_logger = logging.getLogger(__name__)


class GithubRepository(models.Model):
    _inherit = 'github.repository'

    def _update_from_github_data(self, data):
        """Override to mark linked product variants as needing ZIP update."""
        res = super()._update_from_github_data(data)

        # Find product variants linked to any branch of this repository
        variants = self.env['product.product'].search([
            ('github_branch_id.repository_id', '=', self.id),
        ])
        if variants:
            variants.write({'github_doc_needs_update': True})
            _logger.info(
                "GITHUB DOC: Marked %d variant(s) as needing update for repo [%s].",
                len(variants), self.name,
            )

        return res
