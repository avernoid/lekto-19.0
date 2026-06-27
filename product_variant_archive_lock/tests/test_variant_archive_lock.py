# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestVariantArchiveLock(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.attribute = cls.env['product.attribute'].create({
            'name': 'Color',
            'create_variant': 'always',
            'value_ids': [
                Command.create({'name': 'Red'}),
                Command.create({'name': 'Blue'}),
                Command.create({'name': 'Green'}),
            ],
        })
        cls.red, cls.blue, cls.green = cls.attribute.value_ids

    def _new_template(self, lock):
        """Plantilla con la línea de atributo Color = {Red, Blue}."""
        return self.env['product.template'].create({
            'name': 'T-Shirt',
            'variant_archive_lock': lock,
            'attribute_line_ids': [Command.create({
                'attribute_id': self.attribute.id,
                'value_ids': [Command.set((self.red + self.blue).ids)],
            })],
        })

    def _variant(self, tmpl, value):
        """Variante (incluida archivada) cuya combinación contiene `value`."""
        variants = tmpl.with_context(active_test=False).product_variant_ids
        return variants.filtered(
            lambda v: value in v.product_template_attribute_value_ids.product_attribute_value_id
        )

    def _add_green(self, tmpl):
        """Añade el valor Green -> dispara _create_variant_ids."""
        tmpl.attribute_line_ids.write({
            'value_ids': [Command.set((self.red + self.blue + self.green).ids)],
        })

    # ------------------------------------------------------------------
    # Baseline: comportamiento nativo (sin candado)
    # ------------------------------------------------------------------
    def test_native_reactivates_without_lock(self):
        tmpl = self._new_template(lock=False)
        self.assertEqual(len(tmpl.product_variant_ids), 2)

        red_variant = self._variant(tmpl, self.red)
        red_variant.action_archive()
        self.assertFalse(red_variant.active)
        self.assertTrue(red_variant.manually_archived)

        self._add_green(tmpl)

        # Sin candado, Odoo reactiva la variante archivada (comportamiento nativo).
        self.assertTrue(
            red_variant.active,
            "Sin el candado, la variante archivada debe reactivarse (nativo).",
        )

    # ------------------------------------------------------------------
    # Con candado: el archivado manual se respeta
    # ------------------------------------------------------------------
    def test_lock_keeps_manual_archive(self):
        tmpl = self._new_template(lock=True)
        red_variant = self._variant(tmpl, self.red)
        red_variant.action_archive()
        self.assertFalse(red_variant.active)

        self._add_green(tmpl)

        # La variante Green se crea y queda activa.
        green_variant = self._variant(tmpl, self.green)
        self.assertTrue(green_variant.active)
        # La variante Red archivada a mano SIGUE archivada.
        self.assertFalse(
            red_variant.active,
            "Con el candado, la variante archivada manualmente no debe reactivarse.",
        )
        # Blue nunca se tocó: sigue activa.
        self.assertTrue(self._variant(tmpl, self.blue).active)

    # ------------------------------------------------------------------
    # El re-archivado solo afecta a las marcadas manualmente
    # ------------------------------------------------------------------
    def test_lock_does_not_touch_auto_archived(self):
        """Una variante que queda inválida (no manual) se gestiona como nativo."""
        tmpl = self._new_template(lock=True)
        blue_variant = self._variant(tmpl, self.blue)
        self.assertFalse(blue_variant.manually_archived)

        # Quitar Blue de la línea: su variante deja de ser válida -> nativo la
        # archiva/elimina, sin marca manual.
        tmpl.attribute_line_ids.write({
            'value_ids': [Command.set(self.red.ids)],
        })
        # No debe haberse marcado como manual en ningún momento.
        self.assertFalse(
            blue_variant.exists() and blue_variant.manually_archived,
            "El archivado automático no debe marcarse como manual.",
        )

    # ------------------------------------------------------------------
    # Multi-atributo: el candado respeta la COMBINACIÓN exacta, no el valor
    # ------------------------------------------------------------------
    def test_lock_is_per_combination_not_per_value(self):
        """Archivar Azul-M no impide crear Azul-L (combinación nueva) al añadir
        una talla; solo Azul-M sigue archivada."""
        size = self.env['product.attribute'].create({
            'name': 'Size',
            'create_variant': 'always',
            'value_ids': [
                Command.create({'name': 'S'}),
                Command.create({'name': 'M'}),
                Command.create({'name': 'L'}),
            ],
        })
        s, m, l = size.value_ids

        tmpl = self.env['product.template'].create({
            'name': 'T-Shirt 2D',
            'variant_archive_lock': True,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': self.attribute.id,
                    'value_ids': [Command.set((self.red + self.blue).ids)],
                }),
                Command.create({
                    'attribute_id': size.id,
                    'value_ids': [Command.set((s + m).ids)],
                }),
            ],
        })
        # 2 colores x 2 tallas = 4 variantes
        self.assertEqual(len(tmpl.product_variant_ids), 4)

        def combo(color, size_val):
            variants = tmpl.with_context(active_test=False).product_variant_ids
            return variants.filtered(lambda v: (
                color in v.product_template_attribute_value_ids.product_attribute_value_id
                and size_val in v.product_template_attribute_value_ids.product_attribute_value_id
            ))

        blue_m = combo(self.blue, m)
        self.assertEqual(len(blue_m), 1)
        blue_m.action_archive()
        self.assertFalse(blue_m.active)

        # Añadir talla L -> nuevas combinaciones (Rojo-L, Azul-L)
        tmpl.attribute_line_ids.filtered(
            lambda al: al.attribute_id == size
        ).write({'value_ids': [Command.set((s + m + l).ids)]})

        # Azul-M sigue archivada (combinación que el usuario archivó)
        self.assertFalse(
            blue_m.active,
            "Azul-M archivada manualmente debe seguir archivada.",
        )
        # Azul-L es nueva y se crea activa (el candado es por combinación)
        blue_l = combo(self.blue, l)
        self.assertEqual(len(blue_l), 1)
        self.assertTrue(
            blue_l.active,
            "Azul-L es una combinación nueva: debe crearse activa.",
        )

    # ------------------------------------------------------------------
    # Desarchivar manualmente limpia la marca
    # ------------------------------------------------------------------
    def test_manual_unarchive_clears_flag(self):
        tmpl = self._new_template(lock=True)
        red_variant = self._variant(tmpl, self.red)
        red_variant.action_archive()
        self.assertTrue(red_variant.manually_archived)

        red_variant.action_unarchive()
        self.assertFalse(red_variant.manually_archived)
        self.assertTrue(red_variant.active)

        # Tras desarchivar, una regeneración la mantiene activa.
        self._add_green(tmpl)
        self.assertTrue(red_variant.active)
