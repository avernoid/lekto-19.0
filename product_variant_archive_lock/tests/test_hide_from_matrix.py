# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestHideFromMatrix(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.color = cls.env['product.attribute'].create({
            'name': 'Color',
            'create_variant': 'always',
            'value_ids': [
                Command.create({'name': 'Red'}),
                Command.create({'name': 'Blue'}),
            ],
        })
        cls.size = cls.env['product.attribute'].create({
            'name': 'Size',
            'create_variant': 'always',
            'value_ids': [
                Command.create({'name': 'S'}),
                Command.create({'name': 'M'}),
            ],
        })
        # Color line first (sequence 1) -> columns; Size line second -> rows.
        cls.template = cls.env['product.template'].create({
            'name': 'Grid T-Shirt',
            'product_add_mode': 'matrix',
            'attribute_line_ids': [
                Command.create({
                    'sequence': 1,
                    'attribute_id': cls.color.id,
                    'value_ids': [Command.set(cls.color.value_ids.ids)],
                }),
                Command.create({
                    'sequence': 2,
                    'attribute_id': cls.size.id,
                    'value_ids': [Command.set(cls.size.value_ids.ids)],
                }),
            ],
        })

    # ------------------------------------------------------------------ helpers
    def _ptav(self, value_name):
        return self.template.attribute_line_ids.product_template_value_ids.filtered(
            lambda p: p.name == value_name
        )

    def _columns(self, matrix):
        # header[0] is the template name; the rest are the column headers
        return [h.get('name') for h in matrix['header'][1:]]

    def _rows(self, matrix):
        return [row[0].get('name') for row in matrix['matrix']]

    def _variants_with(self, value_name):
        variants = self.template.with_context(active_test=False).product_variant_ids
        return variants.filtered(
            lambda v: value_name in v.product_template_attribute_value_ids.mapped('name')
        )

    # ------------------------------------------------------------------ tests
    def test_baseline_matrix(self):
        """Without any hidden value: Color = columns, Size = rows."""
        matrix = self.template._get_template_matrix()
        self.assertEqual(set(self._columns(matrix)), {'Red', 'Blue'})
        self.assertEqual(set(self._rows(matrix)), {'S', 'M'})

    def test_hide_column_value(self):
        """Hiding a value of the first line removes its column."""
        self._ptav('Blue').hide_from_matrix = True
        matrix = self.template._get_template_matrix()
        self.assertEqual(set(self._columns(matrix)), {'Red'})
        self.assertNotIn('Blue', self._columns(matrix))
        # rows are untouched
        self.assertEqual(set(self._rows(matrix)), {'S', 'M'})

    def test_hide_row_value(self):
        """Hiding a value of a non-first line removes its rows."""
        self._ptav('M').hide_from_matrix = True
        matrix = self.template._get_template_matrix()
        self.assertEqual(set(self._rows(matrix)), {'S'})
        # columns untouched
        self.assertEqual(set(self._columns(matrix)), {'Red', 'Blue'})

    def test_variants_not_archived(self):
        """Hiding a value must NOT archive its variants, even after a
        variant regeneration."""
        self._ptav('Blue').hide_from_matrix = True
        blue_variants = self._variants_with('Blue')
        self.assertTrue(blue_variants)
        self.assertTrue(all(blue_variants.mapped('active')))
        # ptav_active stays True (we never touch it)
        self.assertTrue(self._ptav('Blue').ptav_active)

        # Force a regeneration: variants must remain active.
        self.template._create_variant_ids()
        self.assertTrue(all(self._variants_with('Blue').mapped('active')))

    def test_only_active_unaffected_without_context(self):
        """Outside the matrix context, _only_active must still include hidden
        values, so variant generation/exclusions are not impacted."""
        self._ptav('Blue').hide_from_matrix = True
        values = self.template.attribute_line_ids.product_template_value_ids._only_active()
        self.assertIn('Blue', values.mapped('name'))
        # With the matrix flag, it is filtered out.
        values_matrix = values.with_context(matrix_hide_values=True)._only_active()
        self.assertNotIn('Blue', values_matrix.mapped('name'))

    def test_hide_whole_line_does_not_crash(self):
        """Hiding every value of a line yields an empty matrix, no crash."""
        (self._ptav('Red') | self._ptav('Blue')).hide_from_matrix = True
        matrix = self.template._get_template_matrix()
        self.assertEqual(matrix['matrix'], [])
        self.assertEqual(self._columns(matrix), [])

    def test_setting_persists_after_attribute_edit(self):
        """The flag survives editing the product's attributes (unlike the
        native ptav_active toggle, which would be reactivated)."""
        self._ptav('Blue').hide_from_matrix = True
        # Edit the other line (add nothing new, just rewrite value_ids).
        self.template.attribute_line_ids.filtered(
            lambda al: al.attribute_id == self.size
        ).write({'value_ids': [Command.set(self.size.value_ids.ids)]})
        self.assertTrue(self._ptav('Blue').hide_from_matrix)
        matrix = self.template._get_template_matrix()
        self.assertNotIn('Blue', self._columns(matrix))
