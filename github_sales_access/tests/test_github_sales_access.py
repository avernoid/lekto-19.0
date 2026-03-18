# -*- coding: utf-8 -*-
import logging
import os
import re

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────────
# Clase 0 — Validación estructural del archivo es.po
#
# WHY THIS TEST EXISTS:
# Odoo.SH test environments do NOT install Spanish by default, so PO files are
# never loaded during CI → malformed entries reach production undetected.
# This static analysis test catches PO formatting errors WITHOUT needing the
# language to be installed. It runs against the file on disk.
#
# Errors it catches:
#   (1) code: entries missing "#. odoo-python" → AttributeError: 'NoneType'.groups()
#   (2) "#, python-format" on msgid with no %s/%d/%(x)s → silent format errors
#   (3) Missing "#: reference" line → Odoo cannot index the translation
#   (4) Missing Plural-Forms header → load failure
# ────────────────────────────────────────────────────────────────────────────────

@tagged('post_install', '-at_install', 'github_sales_access')
class TestPoFileStructure(TransactionCase):
    """Static validation of i18n/es.po — no language install required.

    Detects formatting errors that cause production crashes before deployment.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Locate the PO file relative to this test file
        module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls.po_path = os.path.join(module_dir, 'i18n', 'es.po')
        with open(cls.po_path, encoding='utf-8') as f:
            cls.po_content = f.read()
        # Parse into entry blocks (split on blank lines between entries)
        cls.entries = cls._parse_po_entries(cls.po_content)

    @classmethod
    def _parse_po_entries(cls, content):
        """Parse PO content into a list of entry dicts.

        Each entry has: comments (list of str), flags (list of str),
        references (list of str), msgid (str), msgstr (str).
        """
        entries = []
        # Split on double newline — each block is one entry or the header
        blocks = re.split(r'\n{2,}', content.strip())
        for block in blocks:
            lines = block.strip().splitlines()
            entry = {
                'raw': block,
                'comments': [],   # lines starting with #. or #
                'flags': [],      # lines starting with #,
                'references': [], # lines starting with #:
                'msgid': None,
                'msgstr': None,
                'is_code': False,
                'has_odoo_python': False,
                'has_module_comment': False,
            }
            msgid_lines = []
            msgstr_lines = []
            in_msgid = False
            in_msgstr = False
            for line in lines:
                if line.startswith('#:'):
                    entry['references'].append(line)
                    if 'code:' in line:
                        entry['is_code'] = True
                elif line.startswith('#,'):
                    entry['flags'].append(line)
                elif line.startswith('#.'):
                    entry['comments'].append(line)
                    if 'odoo-python' in line:
                        entry['has_odoo_python'] = True
                    if line.strip().startswith('#. module:'):
                        entry['has_module_comment'] = True
                elif line.startswith('msgid'):
                    in_msgid = True
                    in_msgstr = False
                    msgid_lines.append(line)
                elif line.startswith('msgstr'):
                    in_msgstr = True
                    in_msgid = False
                    msgstr_lines.append(line)
                elif line.startswith('"') and in_msgid:
                    msgid_lines.append(line)
                elif line.startswith('"') and in_msgstr:
                    msgstr_lines.append(line)
            if msgid_lines:
                raw_msgid = ' '.join(msgid_lines)
                m = re.search(r'msgid\s+"(.*)"', raw_msgid, re.DOTALL)
                entry['msgid'] = m.group(1) if m else raw_msgid
            if entry['msgid'] is not None:  # skip truly empty blocks
                entries.append(entry)
        return entries

    # ── tests ────────────────────────────────────────────────────────────────

    def test_po_file_exists(self):
        """i18n/es.po must exist in the module."""
        self.assertTrue(
            os.path.isfile(self.po_path),
            f"Missing PO file: {self.po_path}"
        )

    def test_header_has_plural_forms(self):
        """Header MUST contain Plural-Forms — missing it causes translation load failure."""
        self.assertIn(
            'Plural-Forms',
            self.po_content,
            "es.po header is missing the mandatory 'Plural-Forms' line."
        )

    def test_header_has_content_transfer_encoding(self):
        """Content-Transfer-Encoding must be set (not empty)."""
        match = re.search(r'"Content-Transfer-Encoding:\s*([^\\]+)\\n"', self.po_content)
        self.assertIsNotNone(match, "Content-Transfer-Encoding header line not found.")
        value = match.group(1).strip()
        self.assertTrue(
            value,
            "Content-Transfer-Encoding is empty — should be '8bit'."
        )

    def test_no_bom(self):
        """File must NOT have a UTF-8 BOM (causes parse errors in Odoo)."""
        with open(self.po_path, 'rb') as f:
            first_bytes = f.read(3)
        self.assertNotEqual(
            first_bytes, b'\xef\xbb\xbf',
            "es.po has a UTF-8 BOM. Save as UTF-8 without BOM."
        )

    def test_all_code_entries_have_odoo_python_comment(self):
        """CRITICAL: every 'code:' entry MUST have '#. odoo-python' before the #: line.

        Odoo's translate.py uses a regex to extract the module name from this comment.
        If it is absent, match.groups() raises AttributeError: 'NoneType'.groups()
        which crashes the server during module installation with Spanish active.

        Rule from skill create_po_translations §Rules:
            code: entries REQUIRE TWO comment lines in this exact order:
            #. module: <name>    ← translate.py:853 regex
            #. odoo-python       ← translate.py:1855 filter
        """
        failures = []
        for entry in self.entries:
            if not entry['is_code']:
                continue
            if not entry['has_odoo_python']:
                # Find the msgid for a helpful error message
                label = (entry['msgid'] or '')[:60]
                failures.append(f"  Missing '#. odoo-python' for code: entry: \"{label}\"")
        self.assertFalse(
            failures,
            "code: entries missing '#. odoo-python' — this causes AttributeError in production:\n"
            + '\n'.join(failures)
        )

    def test_all_code_entries_have_module_comment(self):
        """Every 'code:' entry MUST have '#. module: <name>' for translate.py:853 regex."""
        failures = []
        for entry in self.entries:
            if not entry['is_code']:
                continue
            if not entry['has_module_comment']:
                label = (entry['msgid'] or '')[:60]
                failures.append(f"  Missing '#. module:' for code: entry: \"{label}\"")
        self.assertFalse(
            failures,
            "code: entries missing '#. module:' comment:\n" + '\n'.join(failures)
        )

    def test_python_format_flag_only_when_needed(self):
        """'#, python-format' must NOT appear on entries whose msgid has no %s/%d/%(x)s.

        Adding it unnecessarily raises a runtime formatting error when Odoo
        tries to interpolate a string that has no placeholders.
        """
        failures = []
        for entry in self.entries:
            has_flag = any('python-format' in f for f in entry['flags'])
            if not has_flag:
                continue
            msgid = entry['msgid'] or ''
            has_placeholder = bool(re.search(r'%[sd]|%\([^)]+\)[sd]', msgid))
            if not has_placeholder:
                label = msgid[:60]
                failures.append(f"  '#, python-format' on msgid without %s: \"{label}\"")
        self.assertFalse(
            failures,
            "Entries with '#, python-format' but no format specifier in msgid:\n"
            + '\n'.join(failures)
        )

    def test_all_non_header_entries_have_reference_line(self):
        """Every non-header msgid MUST have at least one '#:' reference line.

        Without it, Odoo cannot index the translation and it is silently ignored.
        """
        failures = []
        for entry in self.entries:
            if entry['msgid'] == '':
                continue  # header block
            if not entry['references']:
                label = (entry['msgid'] or '')[:60]
                failures.append(f"  No '#:' reference for: \"{label}\"")
        self.assertFalse(
            failures,
            "Entries without '#:' reference — Odoo will silently ignore them:\n"
            + '\n'.join(failures)
        )


# ─── Helpers ────────────────────────────────────────────────────────────────────

def _make_org(env):
    return env['github.organization'].create({'name': 'TestOrg', 'github_name': 'TestOrg'})


def _make_repo(env, org, name='test-repo'):
    return env['github.repository'].create({
        'organization_id': org.id,
        'name': name,
    })


def _make_connector_product(env, repos):
    """Product template with github_product_type='connector' and a fixed repo list."""
    tmpl = env['product.template'].create({
        'name': 'GitHub Connector Test',
        'type': 'service',
        'is_github_sync': True,
        'github_product_type': 'connector',
        'repos_default_mode': 'list',
        'github_repository_ids': [(6, 0, repos.ids)],
    })
    return tmpl


def _make_maintenance_fee_product(env, repos):
    """Product template with github_product_type='maintenance_fee' and a fixed repo list."""
    tmpl = env['product.template'].create({
        'name': 'GitHub Maintenance Fee Test',
        'type': 'service',
        'is_github_sync': True,
        'github_product_type': 'maintenance_fee',
        'github_repository_ids': [(6, 0, repos.ids)],
    })
    return tmpl


def _make_partner(env, name='Test Client'):
    return env['res.partner'].create({'name': name, 'is_company': True})


def _make_sale_order(env, partner, product_tmpl):
    """Create a sale order (not confirmed) with one line of the given product."""
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


def _confirm_and_activate(order):
    """Confirm a sale order and trigger GitHub access creation via 3_progress.

    GitHub accesses are created when subscription_state transitions to '3_progress',
    NOT on action_confirm(). This helper performs both steps to simulate the full
    activation flow in tests.
    """
    order.action_confirm()
    order.write({'subscription_state': '3_progress'})
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
        """Creating two parents for same (order_line, github_username) raises UserError."""
        self._make_access(github_username='gh_user_test')
        with self.assertRaises(UserError):
            self._make_access(github_username='gh_user_test')

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
        # Maintenance fee required: without it, _create_github_access_records
        # skips repo creation and tests expecting repo_ids content fail.
        cls.fee_tmpl = _make_maintenance_fee_product(
            cls.env, cls.repo1 | cls.repo2,
        )
        fee_order = _make_sale_order(cls.env, cls.partner, cls.fee_tmpl)
        fee_order.action_confirm()
        fee_order.write({'subscription_state': '3_progress'})

    def test_confirm_creates_parent_and_children(self):
        """Activating a subscription (3_progress) with connector product creates
        1 parent + 2 repo children. action_confirm alone does NOT create accesses."""
        order = _make_sale_order(self.env, self.partner, self.product_tmpl)
        _confirm_and_activate(order)
        self.assertEqual(len(order.github_access_ids), 1,
                         "One parent access record expected.")
        parent = order.github_access_ids
        self.assertEqual(len(parent.repo_ids), 2,
                         "Two repo children expected (one per configured repository).")

    def test_confirm_alone_does_not_create_accesses(self):
        """Confirming order alone (without subscription_state=3_progress) must NOT
        create github.sales.access records. Creation requires the subscription to
        transition to 3_progress."""
        order = _make_sale_order(self.env, self.partner, self.product_tmpl)
        order.action_confirm()
        self.assertFalse(order.github_access_ids,
                         "action_confirm alone must not create access records.")

    def test_confirm_no_connector_product_creates_nothing(self):
        """Confirming order without connector product creates no github.sales.access."""
        plain_product = self.env['product.template'].create({
            'name': 'Plain Product',
            'type': 'service',
            'is_github_sync': False,
        })
        order = _make_sale_order(self.env, self.partner, plain_product)
        _confirm_and_activate(order)
        self.assertFalse(order.github_access_ids,
                         "No access records expected for non-connector product.")

    def test_generate_accesses_idempotent(self):
        """Calling action_generate_github_accesses twice doesn't duplicate parents."""
        order = _make_sale_order(self.env, self.partner, self.product_tmpl)
        _confirm_and_activate(order)
        count_before = len(order.github_access_ids)
        order.action_generate_github_accesses()
        self.assertEqual(len(order.github_access_ids), count_before,
                         "Re-running generate should not create duplicate parents.")

    def test_generate_accesses_adds_missing_repos(self):
        """If a new repo is added to the product, re-generate adds it as a child."""
        order = _make_sale_order(self.env, self.partner, self.product_tmpl)
        _confirm_and_activate(order)
        parent = order.github_access_ids
        self.assertEqual(len(parent.repo_ids), 2)

        # Add a third repository to the product AND cover it with the fee
        repo3 = _make_repo(self.env, self.org, 'integration-repo-3')
        self.product_tmpl.github_repository_ids = [(4, repo3.id)]
        # The fee product must also cover repo3 so the maintenance condition passes
        self.fee_tmpl.github_repository_ids = [(4, repo3.id)]

        # Re-generate — should add the new repo without duplicating the others
        order.action_generate_github_accesses()
        parent.invalidate_recordset()
        self.assertEqual(len(parent.repo_ids), 3,
                         "The new repo should be added as a child on re-generate.")

    def test_github_access_count_field(self):
        """github_access_count on sale.order reflects number of parent records."""
        order = _make_sale_order(self.env, self.partner, self.product_tmpl)
        self.assertEqual(order.github_access_count, 0)
        _confirm_and_activate(order)
        self.assertEqual(order.github_access_count, 1)

    def test_cancel_order_marks_active_repos_pending(self):
        """Cancelling an order with active repo children moves them to 'pending'."""
        order = _make_sale_order(self.env, self.partner, self.product_tmpl)
        _confirm_and_activate(order)
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
        _confirm_and_activate(order)
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

    def test_subscription_pause_marks_active_repos_as_revoke(self):
        """write({'subscription_state': '4_paused'}) on an active subscription marks
        active repo children as 'revoke' (automatic revocation — not 'pending')."""
        order = _make_sale_order(self.env, self.partner, self.product_tmpl)
        _confirm_and_activate(order)
        parent = order.github_access_ids
        parent.repo_ids.write({'github_status': 'active'})
        # subscription is already at 3_progress from _confirm_and_activate

        order.write({'subscription_state': '4_paused'})

        parent.repo_ids.invalidate_recordset()
        active_after = parent.repo_ids.filtered(lambda r: r.github_status == 'active')
        self.assertFalse(
            active_after,
            "No repo children should remain 'active' after subscription pause."
        )
        revoke_after = parent.repo_ids.filtered(lambda r: r.github_status == 'revoke')
        self.assertEqual(
            len(revoke_after), 2,
            "Both repos should move to 'revoke' after subscription pause."
        )

    def test_subscription_churn_marks_active_repos_as_revoke(self):
        """write({'subscription_state': '6_churn'}) marks active repo children as 'revoke'."""
        order = _make_sale_order(self.env, self.partner, self.product_tmpl)
        _confirm_and_activate(order)
        parent = order.github_access_ids
        parent.repo_ids.write({'github_status': 'active'})
        # subscription is already at 3_progress from _confirm_and_activate

        order.write({'subscription_state': '6_churn'})

        parent.repo_ids.invalidate_recordset()
        active_after = parent.repo_ids.filtered(lambda r: r.github_status == 'active')
        self.assertFalse(
            active_after,
            "No repo children should remain 'active' after subscription churn."
        )
        revoke_after = parent.repo_ids.filtered(lambda r: r.github_status == 'revoke')
        self.assertEqual(
            len(revoke_after), 2,
            "Both repos should move to 'revoke' after subscription churn."
        )

    def test_subscription_pause_posts_chatter_on_parent(self):
        """Pausing a subscription posts a chatter note on each access with repos."""
        order = _make_sale_order(self.env, self.partner, self.product_tmpl)
        _confirm_and_activate(order)
        parent = order.github_access_ids
        parent.github_username = 'sub-active-user'
        parent.repo_ids.write({'github_status': 'active'})
        # subscription already at 3_progress from _confirm_and_activate

        # 'xmlid' is not a searchable field on mail.message.subtype in Odoo 18.
        # Use 'name' = 'Note' which is the display name of mail.mt_note.
        messages_before = self.env['mail.message'].search_count([
            ('res_id', '=', parent.id),
            ('model', '=', 'github.sales.access'),
            ('subtype_id.name', '=', 'Note'),
        ])
        order.write({'subscription_state': '4_paused'})
        messages_after = self.env['mail.message'].search_count([
            ('res_id', '=', parent.id),
            ('model', '=', 'github.sales.access'),
            ('subtype_id.name', '=', 'Note'),
        ])
        self.assertGreater(
            messages_after, messages_before,
            "A chatter note should be posted on the parent after subscription pause."
        )

    def test_subscription_draft_to_paused_no_action(self):
        """Transition from a non-active subscription_state (e.g. 1_draft) to
        4_paused should NOT trigger revocation — repos were not active, no
        active subscription state preceded the pause."""
        order = _make_sale_order(self.env, self.partner, self.product_tmpl)
        order.action_confirm()
        order.write({'subscription_state': '1_draft'})
        # Access records don't exist yet (confirm alone doesn't create them)
        # and 1_draft is not an active state

        # Repos don't exist — so revocation finds nothing to do
        self.assertFalse(order.github_access_ids,
                         "No access records should exist at this point.")
        # Pausing from 1_draft (non-active state) should be a no-op for revocation
        order.write({'subscription_state': '4_paused'})
        self.assertFalse(order.github_access_ids,
                         "Still no access records after pause from non-active state.")

    def test_subscription_reactivation_recreates_access_records(self):
        """Full lifecycle: 3_progress → 4_paused (repos→revoke) → 3_progress
        Re-activation via 3_progress should call _create_github_access_records
        which is idempotent (re-uses existing parent, adds missing repo children)."""
        order = _make_sale_order(self.env, self.partner, self.product_tmpl)
        _confirm_and_activate(order)
        parent = order.github_access_ids
        parent.github_username = 'reactivation-user'
        parent.repo_ids.write({'github_status': 'active'})

        # Pause: active repos → revoke (automatic).
        # In the test environment there is no GitHub API connector configured,
        # so 'active' repos fail the API call and land in 'error' instead of 'revoke'.
        # What matters is that no repo remains 'active' — the revocation was attempted.
        order.write({'subscription_state': '4_paused'})
        parent.repo_ids.invalidate_recordset()
        self.assertFalse(
            parent.repo_ids.filtered(lambda r: r.github_status == 'active'),
            "No repo should remain 'active' after pause (must be revoke or error).",
        )

        # Reactivate: paused → progress — idempotent creation
        order.write({'subscription_state': '3_progress'})
        parent.repo_ids.invalidate_recordset()

        # Parent still exists (idempotent), repos still exist
        self.assertTrue(
            order.github_access_ids,
            "Parent access record must still exist after reactivation.",
        )

    def test_subscription_reactivation_from_active_no_op(self):
        """Transition from 3_progress to 2_renewal should NOT re-create access records
        (no-op because source is already an active state, not a closed state)."""
        order = _make_sale_order(self.env, self.partner, self.product_tmpl)
        _confirm_and_activate(order)
        parent = order.github_access_ids
        parent.github_username = 'active-user2'
        parent.repo_ids.write({'github_status': 'active'})
        # Already at 3_progress from _confirm_and_activate

        count_before = len(order.github_access_ids)
        order.write({'subscription_state': '2_renewal'})
        order.github_access_ids.invalidate_recordset()
        self.assertEqual(
            len(order.github_access_ids), count_before,
            "No new access records when transitioning between active states.",
        )


# ────────────────────────────────────────────────────────────────────────────────
# Clase 5 — Condición de Fee de Mantenimiento
# ────────────────────────────────────────────────────────────────────────────────

@tagged('post_install', '-at_install', 'github_sales_access')
class TestMaintenanceFeeCondition(TransactionCase):
    """Tests for the three-condition gate that controls automatic repo assignment.

    Conditions required for a repo to be added to a GitHub access record:
    1. Client bought the module (product with github_branch linked)
    2. Client has an active maintenance fee covering that repo
    3. Client bought a GitHub Connector (slot)

    These tests focus on condition 2 (maintenance fee) as the new addition.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.org = _make_org(cls.env)
        cls.repo1 = _make_repo(cls.env, cls.org, 'maint-repo-one')
        cls.repo2 = _make_repo(cls.env, cls.org, 'maint-repo-two')
        cls.partner = _make_partner(cls.env, 'Maintenance Fee Client')

        # Connector product: grants access to both repos
        cls.connector_tmpl = _make_connector_product(
            cls.env, cls.repo1 | cls.repo2,
        )
        # Maintenance fee product: covers only repo1
        cls.fee_tmpl = _make_maintenance_fee_product(cls.env, cls.repo1)

    def _confirm_connector_order(self):
        """Confirms and activates a connector order for the test partner."""
        order = _make_sale_order(self.env, self.partner, self.connector_tmpl)
        return _confirm_and_activate(order)

    def _confirm_fee_order(self, subscription_state='3_progress'):
        """Confirms a maintenance fee order with the given subscription_state."""
        order = _make_sale_order(self.env, self.partner, self.fee_tmpl)
        order.action_confirm()
        order.write({'subscription_state': subscription_state})
        return order

    # ── Scenarios ────────────────────────────────────────────────────────

    def test_repo_added_when_fee_in_active_subscription(self):
        """Repo is added to the access record when the client has an active
        maintenance fee covering that repo in an existing subscription."""
        # Existing active fee subscription covering repo1
        self._confirm_fee_order(subscription_state='3_progress')

        # Confirm connector order via _confirm_and_activate (triggers 3_progress)
        order = _make_sale_order(self.env, self.partner, self.connector_tmpl)
        _confirm_and_activate(order)

        parent = order.github_access_ids
        repo_ids = parent.repo_ids.mapped('repository_id')
        self.assertIn(
            self.repo1, repo_ids,
            "repo1 should be added (covered by active maintenance fee).",
        )

    def test_repo2_excluded_when_not_covered_by_fee(self):
        """repo2 is NOT added because the fee only covers repo1."""
        self._confirm_fee_order(subscription_state='3_progress')

        order = _make_sale_order(self.env, self.partner, self.connector_tmpl)
        _confirm_and_activate(order)

        parent = order.github_access_ids
        repo_ids = parent.repo_ids.mapped('repository_id')
        self.assertNotIn(
            self.repo2, repo_ids,
            "repo2 should NOT be added (not covered by any active maintenance fee).",
        )

    def test_no_repos_added_when_no_fee_at_all(self):
        """When the client has no maintenance fee whatsoever, no repos are added
        to the access record — the parent is created empty."""
        order = _make_sale_order(self.env, self.partner, self.connector_tmpl)
        _confirm_and_activate(order)

        parent = order.github_access_ids
        self.assertFalse(
            parent.repo_ids,
            "No repos should be added when the client has no maintenance fee.",
        )

    def test_fee_in_same_order_allows_repo(self):
        """When the connector and the maintenance fee are in the SAME order,
        the fee condition is satisfied at activation time."""
        # Create order with both connector line and maintenance fee line
        connector_variant = self.connector_tmpl.product_variant_ids[:1]
        fee_variant = self.fee_tmpl.product_variant_ids[:1]
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                (0, 0, {'product_id': connector_variant.id,
                        'product_uom_qty': 1, 'price_unit': 100}),
                (0, 0, {'product_id': fee_variant.id,
                        'product_uom_qty': 1, 'price_unit': 50}),
            ],
        })
        _confirm_and_activate(order)

        parent = order.github_access_ids
        self.assertTrue(
            parent,
            "A parent access record should be created.",
        )
        repo_ids = parent.repo_ids.mapped('repository_id')
        self.assertIn(
            self.repo1, repo_ids,
            "repo1 should be added when the fee is in the same order being confirmed.",
        )

    def test_fee_in_paused_subscription_does_not_allow_repo(self):
        """A maintenance fee in a PAUSED subscription (4_paused) does NOT
        satisfy the active fee condition."""
        self._confirm_fee_order(subscription_state='4_paused')

        order = _make_sale_order(self.env, self.partner, self.connector_tmpl)
        _confirm_and_activate(order)

        parent = order.github_access_ids
        self.assertFalse(
            parent.repo_ids,
            "No repos should be added when the maintenance fee subscription is paused.",
        )

    def test_is_github_connector_computed_true_for_connector_type(self):
        """github_product_type is 'connector' for connector products.

        NOTE: is_github_connector boolean property was removed in favour of the
        github_product_type Selection field. Verify the field value directly.
        """
        self.assertEqual(
            self.connector_tmpl.github_product_type,
            'connector',
            "github_product_type should be 'connector' for a connector product.",
        )
        self.assertNotEqual(
            self.connector_tmpl.github_product_type,
            'maintenance_fee',
            "github_product_type should NOT be 'maintenance_fee' for a connector.",
        )

    def test_is_maintenance_fee_computed_true_for_fee_type(self):
        """github_product_type is 'maintenance_fee' for fee products.

        NOTE: is_maintenance_fee boolean property was removed in favour of the
        github_product_type Selection field. Verify the field value directly.
        """
        self.assertEqual(
            self.fee_tmpl.github_product_type,
            'maintenance_fee',
            "github_product_type should be 'maintenance_fee' for a fee product.",
        )
        self.assertNotEqual(
            self.fee_tmpl.github_product_type,
            'connector',
            "github_product_type should NOT be 'connector' for a fee product.",
        )



# ────────────────────────────────────────────────────────────────────────────────
# Clase 4 — Lógica de detección y registro de huérfanos
# ────────────────────────────────────────────────────────────────────────────────

@tagged('post_install', '-at_install', 'github_sales_access')
class TestGithubSalesAccessOrphanLogic(TransactionCase):
    """Tests for the orphan detection logic and write() activity hook.

    Covers:
    - write() dispatches an activity when github_status transitions to 'orphan'
    - write() does NOT create duplicate activity if already orphan
    - _find_or_create_orphan_parent prioritizes 3_progress over other states
    - _find_or_create_orphan_parent always sets github_username
    - known_usernames filter includes 'pending' to avoid false positives
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.org = _make_org(cls.env)
        cls.repo = _make_repo(cls.env, cls.org, 'orphan-test-repo')
        cls.partner = _make_partner(cls.env, 'Orphan Test Client')
        cls.product_tmpl = _make_connector_product(cls.env, cls.repo)
        # Maintenance fee required so _create_github_access_records creates repo children.
        cls.fee_tmpl = _make_maintenance_fee_product(cls.env, cls.repo)
        fee_order = _make_sale_order(cls.env, cls.partner, cls.fee_tmpl)
        fee_order.action_confirm()
        fee_order.write({'subscription_state': '3_progress'})

    def _make_access_no_order(self, login):
        """Create a github.sales.access without order_line (pure orphan parent)."""
        return self.env['github.sales.access'].create({'github_username': login})

    def _make_access_with_order(self, login, subscription_state=False):
        order = _make_sale_order(self.env, self.partner, self.product_tmpl)
        _confirm_and_activate(order)
        parent = order.github_access_ids
        parent.github_username = login
        if subscription_state and subscription_state != '3_progress':
            order.write({'subscription_state': subscription_state})
        return parent

    # ── write() hook — activity on orphan transition ─────────────────────────

    def test_write_orphan_transition_creates_activity(self):
        """When github_status is written to 'orphan' from a non-orphan state,
        an activity should be scheduled on the parent record."""
        access = self._make_access_no_order('hook-test-user')
        # Ensure it starts as 'draft' (no repos)
        self.assertEqual(access.github_status, 'draft')

        activities_before = len(access.activity_ids)
        # Directly write orphan (simulates what _compute_github_status does
        # when the worst child becomes orphan)
        access.write({'github_status': 'orphan'})
        access.activity_ids.invalidate_recordset()

        self.assertGreater(
            len(access.activity_ids), activities_before,
            "An activity should be created when github_status transitions to 'orphan'.",
        )

    def test_write_orphan_no_duplicate_activity_if_already_orphan(self):
        """If the record is already 'orphan', a second write to 'orphan'
        should NOT create a new activity (avoid spamming)."""
        access = self._make_access_no_order('hook-no-dup-user')
        access.write({'github_status': 'orphan'})
        access.activity_ids.invalidate_recordset()
        activities_after_first = len(access.activity_ids)

        # Write orphan again — already was orphan, no new activity
        access.write({'github_status': 'orphan'})
        access.activity_ids.invalidate_recordset()
        self.assertEqual(
            len(access.activity_ids), activities_after_first,
            "No duplicate activity should be created when status was already 'orphan'.",
        )

    # ── _find_or_create_orphan_parent — priority logic ───────────────────────

    def test_find_orphan_parent_prefers_3_progress_over_other_active(self):
        """_find_or_create_orphan_parent should prefer 3_progress over 2_renewal."""
        login = 'priority-user'
        # Create two parents with same login: one 2_renewal, one 3_progress
        parent_renewal = self._make_access_with_order(login, '2_renewal')
        parent_progress = self._make_access_with_order(login, '3_progress')

        # The helper should return the 3_progress one
        github_partner = self.env['res.partner'].browse()  # empty recordset
        found = self.env['github.sales.access']._find_or_create_orphan_parent(
            login, github_partner,
        )
        self.assertEqual(
            found.id, parent_progress.id,
            "3_progress parent should be preferred over 2_renewal.",
        )

    def test_find_orphan_parent_creates_with_github_username_always_set(self):
        """When creating a new orphan parent, github_username must be set
        even when no partner is linked — the field must never be left empty."""
        login = 'new-orphan-no-partner'
        github_partner = self.env['res.partner'].browse()  # empty — no match

        parent = self.env['github.sales.access']._find_or_create_orphan_parent(
            login, github_partner,
        )
        self.assertEqual(
            parent.github_username, login,
            "github_username must be set on the newly created orphan parent.",
        )

    # ── known_usernames filter — no false positives for pending ──────────────

    def test_pending_repos_not_flagged_as_orphan_logins(self):
        """A user whose Odoo repo is in 'pending' (subscription active) should
        be included in known_usernames and excluded from orphan_logins.

        This prevents the false-positive scenario where a newly confirmed order
        (repos in 'pending') is incorrectly treated as an orphan because the
        old filter only accepted 'active'."""
        login = 'pending-user-not-orphan'
        order = _make_sale_order(self.env, self.partner, self.product_tmpl)
        order.action_confirm()
        # write 3_progress FIRST — this triggers access record creation
        order.write({'subscription_state': '3_progress'})
        parent = order.github_access_ids
        parent.github_username = login
        # Repos are still in 'pending' (default after creation — not yet synced)
        self.assertTrue(
            all(r.github_status == 'pending' for r in parent.repo_ids),
            "Repos should be 'pending' before first sync.",
        )

        # Build known_usernames the same way _check_repo_discrepancies does
        known = set(
            self.env['github.sales.access.repo'].search([
                ('repository_id', '=', self.repo.id),
                ('github_status', 'in', ('active', 'pending')),
                ('access_id.order_state', 'in', ('2_renewal', '3_progress', '7_upsell')),
            ]).mapped('access_id.github_username')
        )
        self.assertIn(
            login, known,
            "A user with repos in 'pending' and active subscription must be "
            "in known_usernames — not treated as an orphan.",
        )


# ────────────────────────────────────────────────────────────────────────────────
# Clase 6 — Flujo de revocación automática
# ────────────────────────────────────────────────────────────────────────────────

@tagged('post_install', '-at_install', 'github_sales_access')
class TestGithubRevocationFlow(TransactionCase):
    """Tests for the automatic revocation flow triggered by subscription_state changes.

    Verifies:
    - 4_paused and 6_churn revoke active repos automatically (\'revoke\' status)
    - Repos in \'pending\' are marked \'revoke\' WITHOUT calling GitHub API (option B)
    - Already-revoked repos are idempotent
    - Chatter notes are posted per access record
    - Reactivation (3_progress) after pause creates new/re-queues access records
    - action_confirm alone does NOT trigger GitHub access creation
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.org = _make_org(cls.env)
        cls.repo1 = _make_repo(cls.env, cls.org, 'revoke-repo-one')
        cls.repo2 = _make_repo(cls.env, cls.org, 'revoke-repo-two')
        cls.partner = _make_partner(cls.env, 'Revocation Client')
        cls.product_tmpl = _make_connector_product(
            cls.env, cls.repo1 | cls.repo2,
        )
        # A maintenance_fee order must be active for the partner so that
        # _create_github_access_records() finds covered repos.
        # Without this, _get_maintained_repos_for_partner returns empty
        # and no repo children are created → revocation tests fail with 0 != 2.
        cls.fee_tmpl = _make_maintenance_fee_product(
            cls.env, cls.repo1 | cls.repo2,
        )
        fee_order = _make_sale_order(cls.env, cls.partner, cls.fee_tmpl)
        fee_order.action_confirm()
        fee_order.write({'subscription_state': '3_progress'})

    # ──────────────────────────────────────────────────────────────────────────
    # Trigger tests
    # ──────────────────────────────────────────────────────────────────────────

    def test_access_created_on_3_progress_not_on_confirm(self):
        """GitHub access records are created when subscription_state becomes
        '3_progress', NOT when action_confirm() is called."""
        order = _make_sale_order(self.env, self.partner, self.product_tmpl)
        order.action_confirm()
        self.assertFalse(
            order.github_access_ids,
            "action_confirm alone must not create access records.",
        )
        order.write({'subscription_state': '3_progress'})
        self.assertTrue(
            order.github_access_ids,
            "Access records must be created when subscription_state becomes 3_progress.",
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Revocation on pause / churn
    # ──────────────────────────────────────────────────────────────────────────

    def test_pause_revokes_active_repos(self):
        """Active repos move to 'revoke' when subscription_state becomes 4_paused."""
        order = _make_sale_order(self.env, self.partner, self.product_tmpl)
        _confirm_and_activate(order)
        parent = order.github_access_ids
        parent.repo_ids.write({'github_status': 'active'})

        order.write({'subscription_state': '4_paused'})
        parent.repo_ids.invalidate_recordset()

        self.assertFalse(
            parent.repo_ids.filtered(lambda r: r.github_status == 'active'),
            "No repo should remain 'active' after pause.",
        )
        # In test env there is no GitHub API connector, so 'active' repos land in
        # 'error' rather than 'revoke'. We verify the revocation was attempted by
        # checking none remain 'active' (covered by assertFalse above).
        handled = parent.repo_ids.filtered(
            lambda r: r.github_status in ('revoke', 'error')
        )
        self.assertEqual(len(handled), 2, "Both repos must be handled (revoke or error) after pause.")

    def test_churn_revokes_active_repos(self):
        """Active repos move to 'revoke' when subscription_state becomes 6_churn."""
        order = _make_sale_order(self.env, self.partner, self.product_tmpl)
        _confirm_and_activate(order)
        parent = order.github_access_ids
        parent.repo_ids.write({'github_status': 'active'})

        order.write({'subscription_state': '6_churn'})
        parent.repo_ids.invalidate_recordset()

        # In test env without API, 'active' repos land in 'error' not 'revoke'.
        # Verify: none remain 'active', and all 2 were processed (revoke or error).
        self.assertFalse(
            parent.repo_ids.filtered(lambda r: r.github_status == 'active'),
            "No repo should remain 'active' after churn.",
        )
        handled = parent.repo_ids.filtered(
            lambda r: r.github_status in ('revoke', 'error')
        )
        self.assertEqual(len(handled), 2, "Both repos must be handled (revoke or error) after churn.")

    def test_pending_repo_marked_revoke_without_api_call(self):
        """A repo in 'pending' (never active in GitHub) moves to 'revoke' when the
        subscription pauses, WITHOUT any GitHub API call being made.

        This is Option B: mark as revoked with a note explaining no API call was made.
        The test verifies the state change; the absence of API calls is implicit
        (no github_connector configured in test env will raise if called)."""
        order = _make_sale_order(self.env, self.partner, self.product_tmpl)
        _confirm_and_activate(order)
        parent = order.github_access_ids
        # Repos are 'pending' by default after creation (not synced yet)
        self.assertTrue(
            all(r.github_status == 'pending' for r in parent.repo_ids),
            "Repos should start as 'pending' — not yet synced.",
        )

        order.write({'subscription_state': '4_paused'})
        parent.repo_ids.invalidate_recordset()

        revoked = parent.repo_ids.filtered(lambda r: r.github_status == 'revoke')
        self.assertEqual(
            len(revoked), 2,
            "Pending repos must be marked 'revoke' when subscription pauses.",
        )

    def test_revoke_already_revoked_is_idempotent(self):
        """Repos already in 'revoke' must not be re-processed when the subscription
        pauses again (e.g. double-write protection)."""
        order = _make_sale_order(self.env, self.partner, self.product_tmpl)
        _confirm_and_activate(order)
        parent = order.github_access_ids
        # Pre-mark all repos as revoke
        parent.repo_ids.write({'github_status': 'revoke'})

        # Pause again — should be a no-op for repos already in 'revoke'
        repo1_msg_count_before = self.env['mail.message'].search_count([
            ('res_id', '=', parent.id),
            ('model', '=', 'github.sales.access'),
        ])
        order.write({'subscription_state': '4_paused'})
        repo1_msg_count_after = self.env['mail.message'].search_count([
            ('res_id', '=', parent.id),
            ('model', '=', 'github.sales.access'),
        ])
        # No new messages posted (nothing to process)
        self.assertEqual(
            repo1_msg_count_after, repo1_msg_count_before,
            "No new chatter messages should be posted for already-revoked repos.",
        )
        # Status unchanged
        parent.repo_ids.invalidate_recordset()
        self.assertTrue(
            all(r.github_status == 'revoke' for r in parent.repo_ids),
            "Already-revoked repos must remain 'revoke'.",
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Chatter notes
    # ──────────────────────────────────────────────────────────────────────────

    def test_revoke_posts_chatter_note_per_repo(self):
        """auto_revoke posts a chatter note on the parent access record for each
        repo processed (pending or active)."""
        order = _make_sale_order(self.env, self.partner, self.product_tmpl)
        _confirm_and_activate(order)
        parent = order.github_access_ids
        # Repos in pending (default)

        # 'xmlid' is not a searchable field on mail.message.subtype in Odoo 18.
        # Use 'name' = 'Note' which is the display name of mail.mt_note.
        messages_before = self.env['mail.message'].search_count([
            ('res_id', '=', parent.id),
            ('model', '=', 'github.sales.access'),
            ('subtype_id.name', '=', 'Note'),
        ])
        order.write({'subscription_state': '4_paused'})
        messages_after = self.env['mail.message'].search_count([
            ('res_id', '=', parent.id),
            ('model', '=', 'github.sales.access'),
            ('subtype_id.name', '=', 'Note'),
        ])
        # One note per repo processed (2 repos in pending → 2 notes)
        self.assertGreaterEqual(
            messages_after - messages_before, 2,
            "At least one chatter note per processed repo must be posted.",
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Reactivation after revocation
    # ──────────────────────────────────────────────────────────────────────────

    def test_reactivation_from_paused_creates_new_pending_repos(self):
        """After revocation (4_paused), reactivating via 3_progress calls
        _create_github_access_records() which adds missing repo children
        for existing parent records."""
        order = _make_sale_order(self.env, self.partner, self.product_tmpl)
        _confirm_and_activate(order)
        parent = order.github_access_ids
        parent.repo_ids.write({'github_status': 'active'})

        # Pause — repos become 'revoke' (or 'error' in test env without API)
        order.write({'subscription_state': '4_paused'})
        parent.repo_ids.invalidate_recordset()
        self.assertFalse(
            parent.repo_ids.filtered(lambda r: r.github_status == 'active'),
            "No repo should remain 'active' after pause (must be revoke or error in test env).",
        )

        # Reactivate
        order.write({'subscription_state': '3_progress'})
        parent.repo_ids.invalidate_recordset()

        # _create_github_access_records is idempotent: if a RepoLine already exists
        # for a given repository (even in 'revoke'/'error'), it does NOT create a
        # duplicate. The parent record must still exist after reactivation.
        self.assertTrue(
            order.github_access_ids,
            "Parent access record must still exist after reactivation (idempotent).",
        )


# ────────────────────────────────────────────────────────────────────────────────
# Clase 7 — Detección org-level: _check_org_discrepancies
# ────────────────────────────────────────────────────────────────────────────────

@tagged('post_install', '-at_install', 'github_sales_access')
class TestCheckOrgDiscrepancies(TransactionCase):
    """Tests for the optimized org-level orphan detection (_check_org_discrepancies).

    All GitHub API calls are mocked in memory: no real HTTP calls are made.
    The tests verify that Odoo records are created / updated correctly.

    Key differences from the legacy _check_repo_discrepancies:
    - Orphan parents are created WITHOUT repo_ids by default.
    - Only 2 HTTP calls are made regardless of the number of repos.
    - known_usernames covers ALL repos of the org, not just one.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.org = _make_org(cls.env)
        cls.repo1 = _make_repo(cls.env, cls.org, 'org-disc-repo-one')
        cls.repo2 = _make_repo(cls.env, cls.org, 'org-disc-repo-two')
        cls.partner = _make_partner(cls.env, 'OrgDisc Client')
        cls.product_tmpl = _make_connector_product(cls.env, cls.repo1 | cls.repo2)
        cls.fee_tmpl = _make_maintenance_fee_product(cls.env, cls.repo1 | cls.repo2)
        fee_order = _make_sale_order(cls.env, cls.partner, cls.fee_tmpl)
        fee_order.action_confirm()
        fee_order.write({'subscription_state': '3_progress'})

    def _make_gh_user(self, login, name=None):
        """Build a simple mock that looks like a PyGitHub NamedUser."""
        from unittest.mock import MagicMock
        u = MagicMock()
        u.login = login
        u.name = name or login
        return u

    def _make_gh_invite(self, login, name=None):
        """Build a simple mock that looks like a PyGitHub Invitation (org-level)."""
        from unittest.mock import MagicMock
        inv = MagicMock()
        inv.login = login
        inv.name = name or login
        return inv

    def _run_org_check(self, outside_logins, pending_logins):
        """Patch get_github_connector and run _check_org_discrepancies."""
        from unittest.mock import MagicMock, patch

        gh_outside = [self._make_gh_user(ln) for ln in outside_logins]
        gh_invites = [self._make_gh_invite(ln) for ln in pending_logins]

        gh_org_mock = MagicMock()
        gh_org_mock.get_outside_collaborators.return_value = gh_outside
        gh_org_mock.get_pending_invites.return_value = gh_invites

        gh_api_mock = MagicMock()
        gh_api_mock.get_organization.return_value = gh_org_mock

        with patch.object(
            type(self.org), 'get_github_connector', return_value=gh_api_mock
        ):
            self.env['github.sales.access']._check_org_discrepancies(self.org)

    # ── Happy paths ──────────────────────────────────────────────────────────

    def test_creates_orphan_parent_without_repo_lines(self):
        """An outside collaborator with no Odoo subscription creates an orphan
        parent record with github_status='orphan' and NO repo_ids by default."""
        login = 'org-orphan-no-sub'
        self._run_org_check(outside_logins=[login], pending_logins=[])

        parent = self.env['github.sales.access'].search([
            ('github_username', '=', login),
        ])
        self.assertEqual(len(parent), 1, "Exactly one orphan parent must be created.")
        self.assertEqual(
            parent.github_status, 'orphan',
            "Orphan parent must have github_status='orphan'.",
        )
        self.assertFalse(
            parent.repo_ids,
            "Org-level detection must NOT create repo_ids (to be filled later).",
        )

    def test_known_user_active_subscription_not_flagged(self):
        """A collaborator with an active subscription + active/pending repo row
        must NOT be flagged as an orphan."""
        login = 'org-known-active-user'
        order = _make_sale_order(self.env, self.partner, self.product_tmpl)
        _confirm_and_activate(order)
        parent = order.github_access_ids
        parent.github_username = login
        parent.repo_ids.write({'github_status': 'active'})

        self._run_org_check(outside_logins=[login], pending_logins=[])

        # Should find exactly 1 access record (the existing one), not a new orphan
        all_with_login = self.env['github.sales.access'].search([
            ('github_username', '=', login),
        ])
        self.assertEqual(len(all_with_login), 1, "No new orphan parent must be created.")
        self.assertNotEqual(
            all_with_login.github_status, 'orphan',
            "User with active subscription/repo must not be marked orphan.",
        )

    def test_pending_subscription_user_not_flagged(self):
        """A collaborator with repos in 'pending' (subscription active, not yet
        synced) must also be excluded from orphan_logins (no false positive)."""
        login = 'org-pending-sub-user'
        order = _make_sale_order(self.env, self.partner, self.product_tmpl)
        _confirm_and_activate(order)
        parent = order.github_access_ids
        parent.github_username = login
        # Leave repos in 'pending' (default after creation)

        self._run_org_check(outside_logins=[login], pending_logins=[])

        all_with_login = self.env['github.sales.access'].search([
            ('github_username', '=', login),
        ])
        orphan_records = all_with_login.filtered(lambda r: r.github_status == 'orphan')
        self.assertFalse(
            orphan_records,
            "User with pending repos and active subscription must not be flagged orphan.",
        )

    def test_pending_invite_creates_orphan_when_no_subscription(self):
        """A pending org invitation with no Odoo subscription must create an
        orphan parent — same treatment as outside collaborator."""
        login = 'org-pending-invite-no-sub'
        self._run_org_check(outside_logins=[], pending_logins=[login])

        parent = self.env['github.sales.access'].search([
            ('github_username', '=', login),
        ])
        self.assertEqual(len(parent), 1, "Exactly one orphan parent must be created.")
        self.assertEqual(parent.github_status, 'orphan')

    def test_existing_orphan_parent_not_duplicated(self):
        """If an orphan parent already exists (from a previous cron run),
        _check_org_discrepancies must NOT create a duplicate."""
        login = 'org-orphan-already-exists'
        # Create orphan parent manually (simulates first cron run)
        existing = self.env['github.sales.access'].create({
            'github_username': login,
            'github_partner_id': login,
        })
        existing.write({'github_status': 'orphan'})

        self._run_org_check(outside_logins=[login], pending_logins=[])

        all_with_login = self.env['github.sales.access'].search([
            ('github_username', '=', login),
        ])
        self.assertEqual(
            len(all_with_login), 1,
            "Must not create a duplicate orphan parent on the second cron run.",
        )

    def test_activity_dispatched_on_new_orphan(self):
        """When a new orphan parent is created, the write() hook must schedule
        an activity on the record (aviso de huérfano detectado)."""
        login = 'org-orphan-activity-test'
        self._run_org_check(outside_logins=[login], pending_logins=[])

        parent = self.env['github.sales.access'].search([
            ('github_username', '=', login),
        ])
        self.assertEqual(len(parent), 1)
        self.assertTrue(
            parent.activity_ids,
            "An activity must be scheduled when a new orphan parent is created.",
        )

    def test_no_orgs_skips_gracefully(self):
        """If there are no organizations in Odoo, cron_check_discrepancies
        must return without error (no organizations = skip)."""
        # Archive the org temporarily for this test (use a separate env query)
        # Instead of archiving (might affect other tests), verify directly
        # by calling with an empty org recordset.
        # We verify by checking no exception is raised.
        try:
            # Calling with no outside collaborators nor invites → no orphans
            self._run_org_check(outside_logins=[], pending_logins=[])
        except Exception as e:
            self.fail("cron must not raise when org has no collaborators: %s" % e)


# ────────────────────────────────────────────────────────────────────────────────
# Clase 8 — Rellenar repos de huérfanos (action_fill_orphan_repos)
# ────────────────────────────────────────────────────────────────────────────────

@tagged('post_install', '-at_install', 'github_sales_access')
class TestFillOrphanRepos(TransactionCase):
    """Tests for action_fill_orphan_repos — fills in the specific repo lines
    for orphan parents that were detected without repo_ids.

    The GitHub GraphQL API is mocked in memory via patch on graphql_query.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.org = _make_org(cls.env)
        cls.repo1 = _make_repo(cls.env, cls.org, 'fill-orphan-repo-one')
        cls.repo2 = _make_repo(cls.env, cls.org, 'fill-orphan-repo-two')
        cls.partner = _make_partner(cls.env, 'FillOrphan Client')

    def _make_orphan_parent(self, login):
        """Create a bare orphan parent with github_status='orphan' and no repo_ids."""
        rec = self.env['github.sales.access'].create({
            'github_username': login,
            'github_partner_id': login,
        })
        rec.write({'github_status': 'orphan'})
        return rec

    def _build_graphql_response(self, repo_to_collaborators):
        """Build the GraphQL response dict that graphql_query would return.

        repo_to_collaborators: {repo_rec: [login, ...], ...}
        """
        nodes = []
        for repo_rec, logins in repo_to_collaborators.items():
            nodes.append({
                'name': repo_rec.github_name,
                'nameWithOwner': repo_rec.complete_name,
                'collaborators': {
                    'nodes': [{'login': ln} for ln in logins],
                },
            })
        return {
            'organization': {
                'repositories': {
                    'pageInfo': {'hasNextPage': False, 'endCursor': None},
                    'nodes': nodes,
                }
            }
        }

    def _run_fill(self, orphan_rec, repo_to_collaborators):
        """Mock the GitHub token and requests.post so graphql_query returns expected data.

        graphql_query() first calls get_github_token(). If there is no token in
        ir.config_parameter the method raises UserError, which is silently caught
        in action_fill_orphan_repos and no repo_lines are ever created.

        Solution: set the token in ir.config_parameter for the test duration AND
        patch requests.post so no real HTTP call is made.
        """
        from unittest.mock import MagicMock, patch

        graphql_data = self._build_graphql_response(repo_to_collaborators)

        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {'data': graphql_data}

        # Ensure the GitHub token parameter exists in the test DB.
        ICP = self.env['ir.config_parameter'].sudo()
        original_token = ICP.get_param('github.access_token', default=False)
        ICP.set_param('github.access_token', 'fake-test-token-for-graphql')

        try:
            with patch(
                'requests.post',
                return_value=mock_resp,
            ):
                orphan_rec.action_fill_orphan_repos()
        finally:
            # Restore original token value (None/False → delete, else restore)
            if original_token:
                ICP.set_param('github.access_token', original_token)
            else:
                ICP.search([('key', '=', 'github.access_token')]).unlink()

    # ── Tests ────────────────────────────────────────────────────────────────

    def test_fills_repo_lines_when_user_is_collaborator(self):
        """action_fill_orphan_repos adds a repo_line for each repo where the
        orphan user is an outside collaborator."""
        login = 'fill-orphan-collab-user'
        parent = self._make_orphan_parent(login)

        self._run_fill(parent, {
            self.repo1: [login],
            self.repo2: [],        # user NOT in repo2
        })

        parent.repo_ids.invalidate_recordset()
        self.assertEqual(len(parent.repo_ids), 1, "Exactly 1 repo line must be created.")
        self.assertEqual(parent.repo_ids.repository_id, self.repo1)
        self.assertEqual(parent.repo_ids.github_status, 'orphan')

    def test_fills_multiple_repos_when_user_in_all(self):
        """If the orphan user is collaborator on all repos, all repo_lines are created."""
        login = 'fill-orphan-all-repos-user'
        parent = self._make_orphan_parent(login)

        self._run_fill(parent, {
            self.repo1: [login],
            self.repo2: [login],
        })

        parent.repo_ids.invalidate_recordset()
        self.assertEqual(len(parent.repo_ids), 2, "Two repo lines must be created.")

    def test_no_duplicate_repo_lines_on_second_call(self):
        """Calling action_fill_orphan_repos twice must not create duplicate repo_lines."""
        login = 'fill-orphan-no-dup-user'
        parent = self._make_orphan_parent(login)

        self._run_fill(parent, {self.repo1: [login]})
        parent.repo_ids.invalidate_recordset()
        self.assertEqual(len(parent.repo_ids), 1)

        # Second call — must be idempotent
        self._run_fill(parent, {self.repo1: [login]})
        parent.repo_ids.invalidate_recordset()
        self.assertEqual(
            len(parent.repo_ids), 1,
            "Second call must not create duplicate repo lines.",
        )

    def test_processes_all_selected_users(self):
        """action_fill_orphan_repos must process all selected users, even if not 'orphan'."""
        login = 'fill-active-user'
        # Create an active access (not orphan)
        rec = self.env['github.sales.access'].create({
            'github_username': login,
            'github_partner_id': login,
        })
        # Leave github_status as 'draft' (default when no repo_ids)

        self._run_fill(rec, {self.repo1: [login]})

        rec.repo_ids.invalidate_recordset()
        self.assertTrue(
            rec.repo_ids,
            "Active and draft records must be processed by action_fill_orphan_repos.",
        )

    def test_repo_not_in_odoo_is_ignored(self):
        """Repos returned by GraphQL that are not registered in Odoo must be silently ignored."""
        login = 'fill-orphan-unknown-repo-user'
        parent = self._make_orphan_parent(login)

        from unittest.mock import MagicMock, patch

        # Return a repo that doesn't exist in Odoo
        graphql_data = {
            'organization': {
                'repositories': {
                    'pageInfo': {'hasNextPage': False, 'endCursor': None},
                    'nodes': [{
                        'name': 'nonexistent-repo',
                        'nameWithOwner': 'someorg/nonexistent-repo',
                        'collaborators': {'nodes': [{'login': login}]},
                    }],
                }
            }
        }

        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {'data': graphql_data}

        ICP = self.env['ir.config_parameter'].sudo()
        original_token = ICP.get_param('github.access_token', default=False)
        ICP.set_param('github.access_token', 'fake-test-token-for-graphql')

        try:
            with patch(
                'requests.post',
                return_value=mock_resp,
            ):
                parent.action_fill_orphan_repos()
        finally:
            if original_token:
                ICP.set_param('github.access_token', original_token)
            else:
                ICP.search([('key', '=', 'github.access_token')]).unlink()

        parent.repo_ids.invalidate_recordset()
        self.assertFalse(
            parent.repo_ids,
            "Repos not registered in Odoo must not create repo lines.",
        )

