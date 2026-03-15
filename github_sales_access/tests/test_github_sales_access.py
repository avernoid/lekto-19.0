# -*- coding: utf-8 -*-
import logging

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)


# ─── Helpers ────────────────────────────────────────────────────────────────────

def _make_org(env):
    return env['github.organization'].create({'name': 'TestOrg'})


def _make_repo(env, org, name='test-repo'):
    return env['github.repository'].create({
        'organization_id': org.id,
        'name': name,
    })


def _make_connector_product(env, repos):
    """Product template with is_github_connector=True and a fixed repo list."""
    tmpl = env['product.template'].create({
        'name': 'GitHub Connector Test',
        'type': 'service',
        'is_github_connector': True,
        'repos_default_mode': 'list',
        'github_repository_ids': [(6, 0, repos.ids)],
    })
    return tmpl


def _make_partner(env, name='Test Client'):
    return env['res.partner'].create({'name': name, 'is_company': True})


def _make_sale_order(env, partner, product_tmpl):
    """Create a confirmed sale order with one line of the given product."""
    variant = product_tmpl.product_variant_ids[:1]
    order = env['sale.order'].create({
        'partner_id': partner.id,
        'order_line': [(0, 0, {
            'product_id': variant.id,
            'product_uom_qty': 1,
            'price_unit': 100,
        })],
    })
    return order


# ────────────────────────────────────────────────────────────────────────────────
# Clase 1 — Modelo padre github.sales.access
# ────────────────────────────────────────────────────────────────────────────────

@tagged('post_install', '-at_install', 'github_sales_access')
class TestGithubSalesAccessModel(TransactionCase):
    """Tests for the github.sales.access (parent) model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.org = _make_org(cls.env)
        cls.repo1 = _make_repo(cls.env, cls.org, 'repo-one')
        cls.repo2 = _make_repo(cls.env, cls.org, 'repo-two')
        cls.repo3 = _make_repo(cls.env, cls.org, 'repo-three')
        cls.partner = _make_partner(cls.env)
        cls.product_tmpl = _make_connector_product(
            cls.env, cls.repo1 | cls.repo2,
        )
        cls.order = _make_sale_order(cls.env, cls.partner, cls.product_tmpl)
        cls.order_line = cls.order.order_line[:1]

    def _make_access(self, **kw):
        vals = {'order_line_id': self.order_line.id}
        vals.update(kw)
        return self.env['github.sales.access'].create(vals)

    def _make_repo_line(self, access, repo, status='pending'):
        return self.env['github.sales.access.repo'].create({
            'access_id': access.id,
            'repository_id': repo.id,
            'github_status': status,
        })

    # ── Tests ────────────────────────────────────────────────────────────────

    def test_status_draft_when_no_children(self):
        """Parent with no child repos → github_status == 'draft'."""
        access = self._make_access()
        self.assertEqual(access.github_status, 'draft',
                         "Parent without children should be 'draft'.")

    def test_status_computed_as_worst_child(self):
        """Worst status wins: active + pending + error → error."""
        access = self._make_access()
        self._make_repo_line(access, self.repo1, 'active')
        self._make_repo_line(access, self.repo2, 'pending')
        # Add third repo just for this test
        repo3 = _make_repo(self.env, self.org, 'repo-error')
        self._make_repo_line(access, repo3, 'error')
        access.invalidate_recordset()
        self.assertEqual(access.github_status, 'error',
                         "Worst status among children should propagate to parent.")

    def test_status_orphan_wins_over_error(self):
        """orphan has lowest priority — should beat error."""
        access = self._make_access()
        self._make_repo_line(access, self.repo1, 'error')
        repo_orphan = _make_repo(self.env, self.org, 'repo-orphan')
        self._make_repo_line(access, repo_orphan, 'orphan')
        access.invalidate_recordset()
        self.assertEqual(access.github_status, 'orphan',
                         "'orphan' should be the worst possible status.")

    def test_status_active_when_all_active(self):
        """If all children are active → parent is active."""
        access = self._make_access()
        self._make_repo_line(access, self.repo1, 'active')
        self._make_repo_line(access, self.repo2, 'active')
        access.invalidate_recordset()
        self.assertEqual(access.github_status, 'active')

    def test_repo_count(self):
        """repo_count reflects the number of child records."""
        access = self._make_access()
        self.assertEqual(access.repo_count, 0)
        self._make_repo_line(access, self.repo1)
        self._make_repo_line(access, self.repo2)
        access.invalidate_recordset()
        self.assertEqual(access.repo_count, 2)

    def test_display_name_with_username_and_order(self):
        """display_name shows 'username — order_name' when order_line set."""
        access = self._make_access(github_username='octocat')
        self.order.action_confirm()
        self.assertIn('octocat', access.display_name)
        self.assertIn(self.order.name, access.display_name)

    def test_display_name_without_username(self):
        """display_name falls back to 'Sin usuario' when no username."""
        access = self._make_access()
        self.assertIn('Sin usuario', access.display_name)

    def test_unique_access_constraint(self):
        """Creating two parents for same (order_line, github_partner) raises UserError."""
        github_partner = self.env['res.partner'].create({
            'name': 'GH User', 'github_name': 'gh_user_test'
        })
        self._make_access(github_partner_id=github_partner.id)
        with self.assertRaises(UserError):
            self._make_access(github_partner_id=github_partner.id)

    def test_sync_all_repos_requires_username(self):
        """action_sync_all_repos raises UserError when no github_username is set."""
        access = self._make_access()
        self._make_repo_line(access, self.repo1)
        with self.assertRaises(UserError):
            access.action_sync_all_repos()

    def test_revoke_all_repos_no_crash_when_empty(self):
        """action_revoke_all_repos on a parent with no repos doesn't raise."""
        access = self._make_access()
        # Should not raise — just nothing to revoke
        access.action_revoke_all_repos()


# ────────────────────────────────────────────────────────────────────────────────
# Clase 2 — Modelo hijo github.sales.access.repo
# ────────────────────────────────────────────────────────────────────────────────

@tagged('post_install', '-at_install', 'github_sales_access')
class TestGithubSalesAccessRepoModel(TransactionCase):
    """Tests for the github.sales.access.repo (child) model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.org = _make_org(cls.env)
        cls.repo = _make_repo(cls.env, cls.org, 'repo-child-test')
        cls.partner = _make_partner(cls.env, 'Child Test Client')
        cls.product_tmpl = _make_connector_product(cls.env, cls.repo)
        cls.order = _make_sale_order(cls.env, cls.partner, cls.product_tmpl)
        cls.access = cls.env['github.sales.access'].create({
            'order_line_id': cls.order.order_line[:1].id,
            'github_username': 'test-login',
        })

    def test_unique_repo_per_access_constraint(self):
        """Cannot create two child rows for the same (access_id, repository_id)."""
        self.env['github.sales.access.repo'].create({
            'access_id': self.access.id,
            'repository_id': self.repo.id,
        })
        with self.assertRaises(Exception):
            self.env['github.sales.access.repo'].create({
                'access_id': self.access.id,
                'repository_id': self.repo.id,
            })

    def test_display_name_combines_login_and_repo(self):
        """Child display_name should include the GitHub login and repo name."""
        child = self.env['github.sales.access.repo'].create({
            'access_id': self.access.id,
            'repository_id': self.repo.id,
        })
        self.assertIn('test-login', child.display_name)
        self.assertIn(self.repo.name, child.display_name)


# ────────────────────────────────────────────────────────────────────────────────
# Clase 3 — Integración con sale.order
# ────────────────────────────────────────────────────────────────────────────────

@tagged('post_install', '-at_install', 'github_sales_access')
class TestSaleOrderGithubIntegration(TransactionCase):
    """Tests for the sale.order ↔ github.sales.access integration."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.org = _make_org(cls.env)
        cls.repo1 = _make_repo(cls.env, cls.org, 'integration-repo-1')
        cls.repo2 = _make_repo(cls.env, cls.org, 'integration-repo-2')
        cls.partner = _make_partner(cls.env, 'Integration Client')
        cls.product_tmpl = _make_connector_product(
            cls.env, cls.repo1 | cls.repo2,
        )

    def test_confirm_creates_parent_and_children(self):
        """Confirming order with connector product creates 1 parent + 2 repo children."""
        order = _make_sale_order(self.env, self.partner, self.product_tmpl)
        order.action_confirm()
        self.assertEqual(len(order.github_access_ids), 1,
                         "One parent access record expected.")
        parent = order.github_access_ids
        self.assertEqual(len(parent.repo_ids), 2,
                         "Two repo children expected (one per configured repository).")

    def test_confirm_no_connector_product_creates_nothing(self):
        """Confirming order without connector product creates no github.sales.access."""
        plain_product = self.env['product.template'].create({
            'name': 'Plain Product',
            'type': 'service',
            'is_github_connector': False,
        })
        order = _make_sale_order(self.env, self.partner, plain_product)
        order.action_confirm()
        self.assertFalse(order.github_access_ids,
                         "No access records expected for non-connector product.")

    def test_generate_accesses_idempotent(self):
        """Calling action_generate_github_accesses twice doesn't duplicate parents."""
        order = _make_sale_order(self.env, self.partner, self.product_tmpl)
        order.action_confirm()
        count_before = len(order.github_access_ids)
        order.action_generate_github_accesses()
        self.assertEqual(len(order.github_access_ids), count_before,
                         "Re-running generate should not create duplicate parents.")

    def test_generate_accesses_adds_missing_repos(self):
        """If a new repo is added to the product, re-generate adds it as a child."""
        order = _make_sale_order(self.env, self.partner, self.product_tmpl)
        order.action_confirm()
        parent = order.github_access_ids
        self.assertEqual(len(parent.repo_ids), 2)

        # Add a third repository to the product
        repo3 = _make_repo(self.env, self.org, 'integration-repo-3')
        self.product_tmpl.github_repository_ids = [(4, repo3.id)]

        # Re-generate — should add the new repo without duplicating the others
        order.action_generate_github_accesses()
        parent.invalidate_recordset()
        self.assertEqual(len(parent.repo_ids), 3,
                         "The new repo should be added as a child on re-generate.")

    def test_github_access_count_field(self):
        """github_access_count on sale.order reflects number of parent records."""
        order = _make_sale_order(self.env, self.partner, self.product_tmpl)
        self.assertEqual(order.github_access_count, 0)
        order.action_confirm()
        self.assertEqual(order.github_access_count, 1)

    def test_cancel_order_marks_active_repos_pending(self):
        """Cancelling an order with active repo children moves them to 'pending'."""
        order = _make_sale_order(self.env, self.partner, self.product_tmpl)
        order.action_confirm()
        parent = order.github_access_ids
        # Manually set repos to active
        parent.repo_ids.write({'github_status': 'active'})

        order.action_cancel()

        parent.repo_ids.invalidate_recordset()
        active_after = parent.repo_ids.filtered(
            lambda r: r.github_status == 'active'
        )
        self.assertFalse(active_after,
                         "No repo children should remain 'active' after order cancel.")
        pending_after = parent.repo_ids.filtered(
            lambda r: r.github_status == 'pending'
        )
        self.assertEqual(len(pending_after), 2,
                         "Both repos should move to 'pending' after cancel.")

    def test_cancel_order_creates_activity_on_parent(self):
        """Cancelling order with active repos schedules a to-do activity on the parent."""
        order = _make_sale_order(self.env, self.partner, self.product_tmpl)
        order.action_confirm()
        parent = order.github_access_ids
        parent.github_username = 'active-user'
        parent.repo_ids.write({'github_status': 'active'})

        activities_before = len(parent.activity_ids)
        order.action_cancel()
        parent.activity_ids.invalidate_recordset()
        self.assertGreater(
            len(parent.activity_ids), activities_before,
            "An activity should be created on the parent access record after cancel."
        )
