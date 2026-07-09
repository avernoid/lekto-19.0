from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPartnerIndustrySector(TransactionCase):
    """Behavioural tests for the single-field, inherit-from-parent design.

    The model keeps ONE stored ``industry_sector_id``. A child contact is
    pre-filled from its parent company on creation (and on import), but the
    value is a snapshot: it can be overridden per contact and does NOT auto-
    follow the parent afterwards. A mass action re-aligns a selection with
    the parent company's sector on demand.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Sector = cls.env["industry.sector"]
        cls.sector_a = Sector.create({"name": "Test Sector A"})
        cls.sector_b = Sector.create({"name": "Test Sector B"})
        cls.Partner = cls.env["res.partner"]
        cls.company = cls.Partner.create({
            "name": "Test Company",
            "is_company": True,
            "industry_sector_id": cls.sector_a.id,
        })

    # ── create(): inheritance ────────────────────────────────────────────
    def test_child_inherits_sector_on_create(self):
        child = self.Partner.create({
            "name": "Child no sector",
            "parent_id": self.company.id,
        })
        self.assertEqual(
            child.industry_sector_id, self.sector_a,
            "A child created without a sector should inherit the parent's.",
        )

    def test_child_keeps_own_sector_on_create(self):
        child = self.Partner.create({
            "name": "Child own sector",
            "parent_id": self.company.id,
            "industry_sector_id": self.sector_b.id,
        })
        self.assertEqual(
            child.industry_sector_id, self.sector_b,
            "An explicit sector on create must not be overwritten by inheritance.",
        )

    def test_create_without_parent_stays_empty(self):
        loner = self.Partner.create({"name": "No parent"})
        self.assertFalse(
            loner.industry_sector_id,
            "A contact with no parent and no sector must stay empty.",
        )

    def test_create_multi_inherits_per_record(self):
        other_company = self.Partner.create({
            "name": "Other Co",
            "is_company": True,
            "industry_sector_id": self.sector_b.id,
        })
        children = self.Partner.create([
            {"name": "C1", "parent_id": self.company.id},
            {"name": "C2", "parent_id": other_company.id},
            {"name": "C3", "parent_id": self.company.id,
             "industry_sector_id": self.sector_b.id},
        ])
        self.assertEqual(children[0].industry_sector_id, self.sector_a)
        self.assertEqual(children[1].industry_sector_id, self.sector_b)
        self.assertEqual(
            children[2].industry_sector_id, self.sector_b,
            "Per-record explicit value must be kept in a batch create (import).",
        )

    # ── override is a stable snapshot ────────────────────────────────────
    def test_override_is_stable_after_write(self):
        child = self.Partner.create({
            "name": "Child override",
            "parent_id": self.company.id,
        })
        self.assertEqual(child.industry_sector_id, self.sector_a)
        child.industry_sector_id = self.sector_b
        self.assertEqual(
            child.industry_sector_id, self.sector_b,
            "A manual override must survive (no compute resets it).",
        )

    def test_parent_change_does_not_resync_existing_child(self):
        child = self.Partner.create({
            "name": "Child snapshot",
            "parent_id": self.company.id,
        })
        self.assertEqual(child.industry_sector_id, self.sector_a)
        self.company.industry_sector_id = self.sector_b
        child.invalidate_recordset()
        self.assertEqual(
            child.industry_sector_id, self.sector_a,
            "Updating the parent must not silently change an existing child.",
        )

    # ── onchange: form pre-fill ──────────────────────────────────────────
    def test_onchange_prefills_from_parent(self):
        partner = self.Partner.new({"parent_id": self.company.id})
        partner._onchange_parent_id_industry_sector()
        self.assertEqual(
            partner.industry_sector_id, self.sector_a,
            "Setting the parent in the form should pre-fill the sector.",
        )

    def test_onchange_does_not_override_existing(self):
        partner = self.Partner.new({
            "parent_id": self.company.id,
            "industry_sector_id": self.sector_b.id,
        })
        partner._onchange_parent_id_industry_sector()
        self.assertEqual(
            partner.industry_sector_id, self.sector_b,
            "The onchange must not overwrite a sector the user already set.",
        )

    # ── mass action: realign with parent ─────────────────────────────────
    def test_mass_action_realigns_with_parent(self):
        child = self.Partner.create({
            "name": "Child to realign",
            "parent_id": self.company.id,
            "industry_sector_id": self.sector_b.id,
        })
        child.action_inherit_industry_from_parent()
        self.assertEqual(
            child.industry_sector_id, self.sector_a,
            "Mass action should overwrite the child's sector with the parent's.",
        )

    def test_mass_action_skips_record_without_parent(self):
        loner = self.Partner.create({
            "name": "No parent",
            "industry_sector_id": self.sector_b.id,
        })
        loner.action_inherit_industry_from_parent()
        self.assertEqual(
            loner.industry_sector_id, self.sector_b,
            "A record without a parent must be left untouched.",
        )

    def test_mass_action_skips_when_parent_has_no_sector(self):
        parent_no_sector = self.Partner.create({
            "name": "Parent no sector",
            "is_company": True,
        })
        child = self.Partner.create({
            "name": "Child of empty parent",
            "parent_id": parent_no_sector.id,
            "industry_sector_id": self.sector_b.id,
        })
        child.action_inherit_industry_from_parent()
        self.assertEqual(
            child.industry_sector_id, self.sector_b,
            "If the parent has no sector, the child must be left untouched.",
        )
