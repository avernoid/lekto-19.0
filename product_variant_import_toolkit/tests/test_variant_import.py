import base64

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestVariantImport(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        PA = cls.env['product.attribute']
        PAV = cls.env['product.attribute.value']
        cls.size = PA.create({'name': 'TSize', 'create_variant': 'always'})
        cls.color = PA.create({'name': 'TColor', 'create_variant': 'always'})
        cls.s = PAV.create({'name': 'TS', 'attribute_id': cls.size.id})
        cls.m = PAV.create({'name': 'TM', 'attribute_id': cls.size.id})
        cls.red = PAV.create({'name': 'TRed', 'attribute_id': cls.color.id})
        cls.blue = PAV.create({'name': 'TBlue', 'attribute_id': cls.color.id})

    def _run(self, csv_text, **opts):
        wizard = self.env['product.variant.import'].create(dict({
            'data_file': base64.b64encode(csv_text.encode('utf-8')),
            'filename': 'test.csv',
        }, **opts))
        wizard.action_import()
        return wizard

    # ------------------------------------------------------------------
    def test_dual_external_id(self):
        csv = (
            "id,template_id,name,import_attribute_values,default_code,list_price\n"
            "t.var_s_red,t.tmpl_shirt,Toolkit Shirt,\"TSize:TS,TColor:TRed\",TS-S-R,50\n"
            "t.var_m_blue,t.tmpl_shirt,Toolkit Shirt,\"TSize:TM,TColor:TBlue\",TS-M-B,50\n"
        )
        self._run(csv)
        tmpl = self.env.ref('t.tmpl_shirt')
        self.assertEqual(tmpl._name, 'product.template')
        self.assertEqual(len(tmpl.product_variant_ids), 2)
        var = self.env.ref('t.var_s_red')
        self.assertEqual(var._name, 'product.product')
        self.assertEqual(var.default_code, 'TS-S-R')
        self.assertEqual(var.product_tmpl_id, tmpl)
        # No leftover empty variant.
        self.assertFalse(tmpl.product_variant_ids.filtered(
            lambda v: not v.product_template_attribute_value_ids))

    def test_claim_archived_variant(self):
        # Pre-existing template + auto-generated variant (no external ID), archived.
        tmpl = self.env['product.template'].create({'name': 'Claim Shirt'})
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': tmpl.id, 'attribute_id': self.size.id,
            'value_ids': [(6, 0, [self.s.id])]})
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': tmpl.id, 'attribute_id': self.color.id,
            'value_ids': [(6, 0, [self.red.id])]})
        variant = tmpl.product_variant_ids
        self.assertEqual(len(variant), 1)
        variant.active = False
        self.assertFalse(self.env['ir.model.data'].search(
            [('model', '=', 'product.product'), ('res_id', '=', variant.id)]))

        csv = (
            "id,name,import_attribute_values,default_code\n"
            "c.var_claimed,Claim Shirt,\"TSize:TS,TColor:TRed\",CLAIMED\n"
        )
        self._run(csv, claim_existing=True)

        variant.invalidate_recordset()
        self.assertTrue(variant.active, "claimed variant must be reactivated")
        self.assertEqual(variant.default_code, 'CLAIMED')
        self.assertEqual(self.env.ref('c.var_claimed'), variant)
        # Still exactly one variant for that combination (no duplicate created).
        self.assertEqual(len(tmpl.with_context(active_test=False).product_variant_ids), 1)

    def test_price_extra(self):
        csv = (
            "name,import_attribute_values,price_extra:TColor\n"
            "PE Shirt,\"TSize:TS,TColor:TRed\",25\n"
            "PE Shirt,\"TSize:TM,TColor:TRed\",25\n"
        )
        self._run(csv)
        tmpl = self.env['product.template'].search([('name', '=', 'PE Shirt')])
        ptav_red = tmpl.attribute_line_ids.product_template_value_ids.filtered(
            lambda p: p.product_attribute_value_id == self.red)
        self.assertEqual(ptav_red.price_extra, 25.0)

    def test_freeze_non_cartesian(self):
        csv = (
            "name,import_attribute_values\n"
            "Freeze Shirt,\"TSize:TS,TColor:TRed\"\n"
            "Freeze Shirt,\"TSize:TM,TColor:TBlue\"\n"
        )
        self._run(csv, freeze_others=True)
        tmpl = self.env['product.template'].search([('name', '=', 'Freeze Shirt')])
        combos = set(tmpl.product_variant_ids.mapped('combination_indices'))
        # Only the two imported combinations remain active (S-Blue / M-Red frozen).
        self.assertEqual(len(tmpl.product_variant_ids), 2)
        s_blue = (self._ptav(tmpl, self.s) | self._ptav(tmpl, self.blue))._ids2str()
        self.assertNotIn(s_blue, combos)

    def _ptav(self, tmpl, pav):
        return tmpl.attribute_line_ids.product_template_value_ids.filtered(
            lambda p: p.product_attribute_value_id == pav)
