from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.sale.tests.common import SaleCommon


@tagged("post_install", "-at_install")
class TestCorporateQuotationReport(SaleCommon):
    """Tests for the corporate quotation PDF report."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Configurar el bloque de pago HTML y el código de documento en la compañía
        cls.env.company.quotation_payment_block = (
            "<p>Cuenta BCP Soles: 123-456-789</p>"
            "<p>Cuenta BCP USD: 987-654-321</p>"
        )
        cls.env.company.quotation_document_code = "XX-YY-FT-000 Rev. 0"

        # Crear un contacto con datos completos (empresa + persona)
        cls.partner_company = cls.env["res.partner"].create({
            "name": "Empresa Test SAC",
            "is_company": True,
            "vat": "20123456789",
            "street": "Av. Principal 123",
            "city": "Lima",
            "phone": "+51 1 234 5678",
            "email": "empresa@test.com",
        })
        cls.partner_contact = cls.env["res.partner"].create({
            "name": "Juan Pérez",
            "parent_id": cls.partner_company.id,
            "email": "juan@test.com",
            "phone": "+51 999 888 777",
        })
        cls.partner_shipping = cls.env["res.partner"].create({
            "name": "Almacén Test",
            "parent_id": cls.partner_company.id,
            "type": "delivery",
            "street": "Calle Entrega 456",
            "city": "Arequipa",
        })

        # Cotización completa con todos los campos que usa el reporte
        cls.quotation = cls.env["sale.order"].create({
            "partner_id": cls.partner_contact.id,
            "partner_shipping_id": cls.partner_shipping.id,
            "client_order_ref": "PROY-2026-001",
            "note": "<p>Garantía de 12 meses.</p>",
            "delivery_lead_workdays": 15,
            "order_line": [
                Command.create({
                    "display_type": "line_section",
                    "name": "Equipos de Seguridad",
                }),
                Command.create({
                    "product_id": cls.product.id,
                    "product_uom_qty": 3.0,
                    "price_unit": 150.00,
                }),
                Command.create({
                    "display_type": "line_note",
                    "name": "Incluye accesorios.",
                }),
                Command.create({
                    "product_id": cls.service_product.id,
                    "product_uom_qty": 1.0,
                    "price_unit": 200.00,
                }),
            ],
        })

    # ------------------------------------------------------------------
    # 1. Campo quotation_payment_block en res.company
    # ------------------------------------------------------------------

    def test_01_payment_block_field_exists(self):
        """El campo HTML quotation_payment_block debe existir en res.company."""
        field = self.env["res.company"]._fields.get("quotation_payment_block")
        self.assertIsNotNone(field, "El campo quotation_payment_block no existe en res.company")
        self.assertEqual(field.type, "html")

    def test_01b_certification_logo_field_exists(self):
        """El campo Image quotation_certification_logo debe existir en res.company."""
        field = self.env["res.company"]._fields.get("quotation_certification_logo")
        self.assertIsNotNone(field, "El campo quotation_certification_logo no existe en res.company")
        # fields.Image es internamente binary con verificación de imagen
        self.assertEqual(field.type, "binary")

    def test_02_payment_block_stores_html(self):
        """El bloque de pago debe almacenar y devolver contenido HTML."""
        company = self.env.company
        self.assertIn("BCP Soles", company.quotation_payment_block)
        self.assertIn("BCP USD", company.quotation_payment_block)

    # ------------------------------------------------------------------
    # 2. Registro del reporte (ir.actions.report)
    # ------------------------------------------------------------------

    def test_03_report_action_registered(self):
        """El reporte debe estar registrado con el nombre técnico correcto."""
        report = self.env["ir.actions.report"].search([
            ("report_name", "=", "sale_corporate_quotation.report_corporate_quotation"),
        ])
        self.assertTrue(report, "El report action no está registrado")
        self.assertEqual(report.model, "sale.order")
        self.assertEqual(report.report_type, "qweb-pdf")

    def test_04_report_bound_to_sale_order(self):
        """El reporte debe estar vinculado (binding) al modelo sale.order."""
        report = self.env.ref(
            "sale_corporate_quotation.report_corporate_quotation_action"
        )
        self.assertEqual(report.binding_model_id.model, "sale.order")
        self.assertEqual(report.binding_type, "report")

    # ------------------------------------------------------------------
    # 3. Generación del PDF
    # ------------------------------------------------------------------

    def test_05_pdf_renders_complete_quotation(self):
        """El PDF debe generarse sin error para una cotización con todas las secciones."""
        report = self.env.ref(
            "sale_corporate_quotation.report_corporate_quotation_action"
        )
        pdf_content, content_type = report._render_qweb_pdf(
            report.report_name, self.quotation.ids,
        )
        self.assertTrue(pdf_content, "El PDF no se generó")
        self.assertGreater(len(pdf_content), 0, "El PDF está vacío")

    def test_06_pdf_renders_minimal_quotation(self):
        """El PDF debe generarse para una cotización mínima (sin nota, sin ref, sin envío)."""
        minimal_so = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "order_line": [
                Command.create({
                    "product_id": self.product.id,
                    "product_uom_qty": 1.0,
                }),
            ],
        })
        report = self.env.ref(
            "sale_corporate_quotation.report_corporate_quotation_action"
        )
        pdf_content, _ = report._render_qweb_pdf(
            report.report_name, minimal_so.ids,
        )
        self.assertTrue(pdf_content, "El PDF no se generó para cotización mínima")

    def test_07_pdf_renders_empty_order(self):
        """El PDF debe generarse sin error incluso para una orden sin líneas."""
        report = self.env.ref(
            "sale_corporate_quotation.report_corporate_quotation_action"
        )
        pdf_content, _ = report._render_qweb_pdf(
            report.report_name, self.empty_order.ids,
        )
        self.assertTrue(pdf_content, "El PDF no se generó para orden vacía")

    # ------------------------------------------------------------------
    # 4. Contenido HTML del reporte (verificación de secciones)
    # ------------------------------------------------------------------

    def _render_html(self, order):
        """Helper: renderiza el HTML del reporte para inspección."""
        report = self.env.ref(
            "sale_corporate_quotation.report_corporate_quotation_action"
        )
        html_content = report._render_qweb_html(
            report.report_name, order.ids,
        )[0]
        # Devuelve como string para facilitar asserts
        if isinstance(html_content, bytes):
            html_content = html_content.decode("utf-8")
        return html_content

    def test_08_html_contains_client_data(self):
        """El HTML debe contener los datos del cliente: RUC, nombre, contacto."""
        html = self._render_html(self.quotation)
        self.assertIn("20123456789", html, "Falta el RUC del cliente")
        self.assertIn("Empresa Test SAC", html, "Falta el nombre del cliente")
        self.assertIn("Juan Pérez", html, "Falta el nombre del contacto")

    def test_09_html_contains_project_code(self):
        """El código de proyecto (client_order_ref) debe aparecer en el reporte."""
        html = self._render_html(self.quotation)
        self.assertIn("PROY-2026-001", html, "Falta el código de proyecto")

    def test_10_html_contains_payment_block(self):
        """El bloque de pago HTML de la compañía debe renderizarse."""
        html = self._render_html(self.quotation)
        self.assertIn("BCP Soles", html, "Falta el bloque de cuentas bancarias")
        self.assertIn("BCP USD", html, "Falta el bloque de cuentas USD")

    def test_11_html_contains_delivery_lead_time(self):
        """El tiempo de entrega debe mostrar los días hábiles de delivery_lead_workdays."""
        html = self._render_html(self.quotation)
        # delivery_lead_workdays = 15 → "15 días hábiles..."
        self.assertIn("15", html)
        self.assertIn("días hábiles a partir de recibido el abono", html)

    def test_12_html_contains_terms(self):
        """Los términos y condiciones (note) deben aparecer en PARTE 4."""
        html = self._render_html(self.quotation)
        self.assertIn("Garantía de 12 meses", html)

    def test_13_html_sections_and_notes_rendered(self):
        """Las líneas de sección y nota deben renderizarse correctamente."""
        html = self._render_html(self.quotation)
        self.assertIn("Equipos de Seguridad", html, "Falta la línea de sección")
        self.assertIn("Incluye accesorios", html, "Falta la línea de nota")

    def test_14_html_contains_quotation_title(self):
        """El reporte debe tener el título COTIZACIÓN."""
        html = self._render_html(self.quotation)
        self.assertIn("COTIZACIÓN", html)

    def test_14b_html_contains_document_code(self):
        """El encabezado debe imprimir el código de documento configurado en la compañía."""
        html = self._render_html(self.quotation)
        self.assertIn("XX-YY-FT-000 Rev. 0", html, "Falta el código de documento en el encabezado")

    def test_14c_document_code_optional(self):
        """Sin código de documento configurado, el reporte se genera igual."""
        company_no_code = self.env["res.company"].create({
            "name": "Empresa Sin Código SAC",
        })
        order = self.env["sale.order"].with_company(company_no_code).create({
            "partner_id": self.partner.id,
            "company_id": company_no_code.id,
            "order_line": [
                Command.create({
                    "product_id": self.product.id,
                    "product_uom_qty": 1.0,
                }),
            ],
        })
        report = self.env.ref(
            "sale_corporate_quotation.report_corporate_quotation_action"
        )
        pdf_content, _ = report._render_qweb_pdf(report.report_name, order.ids)
        self.assertTrue(pdf_content, "El PDF no se generó sin código de documento")

    def test_15_html_four_parts_present(self):
        """Las 4 partes del reporte deben estar presentes."""
        html = self._render_html(self.quotation)
        self.assertIn("PARTE 1", html, "Falta PARTE 1")
        self.assertIn("PARTE 2", html, "Falta PARTE 2")
        self.assertIn("PARTE 3", html, "Falta PARTE 3")
        self.assertIn("PARTE 4", html, "Falta PARTE 4")

    # ------------------------------------------------------------------
    # 5. Plazo de entrega: se toma de sale_delivery_lead_workdays
    # ------------------------------------------------------------------

    def test_18_delivery_lead_workdays_field_available(self):
        """El reporte usa delivery_lead_workdays, provisto por la dependencia."""
        field = self.env["sale.order"]._fields.get("delivery_lead_workdays")
        self.assertIsNotNone(
            field,
            "El campo delivery_lead_workdays (sale_delivery_lead_workdays) no existe; "
            "la dependencia no está instalada",
        )

    # ------------------------------------------------------------------
    # 5b. Forma de Pago: usa 'note' (Descripción en la factura) con
    #     fallback al 'name' interno del término de pago
    # ------------------------------------------------------------------

    def test_19_payment_term_renders_note(self):
        """Con 'note' redactada, el PDF muestra la nota, no el name interno."""
        term = self.env["account.payment.term"].create({
            "name": "PT-INTERNO-50-50",
            "note": "<p>50% adelanto, 50% contra entrega</p>",
        })
        self.quotation.payment_term_id = term
        html = self._render_html(self.quotation)
        self.assertIn("50% adelanto, 50% contra entrega", html,
                      "El reporte no muestra la nota del término de pago")
        self.assertNotIn("PT-INTERNO-50-50", html,
                         "El reporte muestra el name interno en vez de la nota")
        # La nota se renderiza con la clase inline para no saltar de línea
        # respecto a la etiqueta "Forma de Pago:".
        self.assertIn("pay-term-inline", html,
                      "Falta la clase inline; la nota saltaría de línea")

    def test_20_payment_term_falls_back_to_name(self):
        """Sin 'note', el PDF cae al name interno del término de pago."""
        term = self.env["account.payment.term"].create({
            "name": "Contado",
            "note": False,
        })
        self.quotation.payment_term_id = term
        html = self._render_html(self.quotation)
        self.assertIn("Contado", html,
                      "El reporte no cae al name cuando la nota está vacía")

    # ------------------------------------------------------------------
    # 5c. Descripción de línea: nombre del producto sin duplicar
    # ------------------------------------------------------------------

    def test_22_product_name_not_duplicated_in_line(self):
        """El nombre del producto debe aparecer una sola vez por línea.

        'line.name' ya incluye el display_name del producto; el reporte debe
        replicar el widget del formulario y NO imprimirlo dos veces (una en
        negrita + otra dentro de la descripción).
        """
        product = self.env["product.product"].create({
            "name": "Casco de Seguridad XYZ",
            "description_sale": "Norma ANSI Z89.1 - Clase E",
        })
        order = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "order_line": [
                Command.create({
                    "product_id": product.id,
                    "product_uom_qty": 1.0,
                }),
            ],
        })
        html = self._render_html(order)
        # El nombre del producto aparece exactamente una vez (solo en negrita).
        self.assertEqual(
            html.count("Casco de Seguridad XYZ"), 1,
            "El nombre del producto se imprime más de una vez en la línea",
        )
        # La descripción de ventas sí debe seguir apareciendo.
        self.assertIn("Norma ANSI Z89.1 - Clase E", html,
                      "La descripción de ventas no aparece en la línea")

    # ------------------------------------------------------------------
    # 6. Reporte nativo intacto
    # ------------------------------------------------------------------

    def test_16_native_report_still_works(self):
        """El reporte nativo de ventas no debe verse afectado."""
        native_report = self.env.ref("sale.action_report_saleorder")
        self.assertTrue(native_report, "El reporte nativo no existe")
        pdf_content, _ = native_report._render_qweb_pdf(
            native_report.report_name, self.sale_order.ids,
        )
        self.assertTrue(pdf_content, "El reporte nativo dejó de funcionar")

    # ------------------------------------------------------------------
    # 7. Multi-compañía: cada empresa tiene su propio bloque
    # ------------------------------------------------------------------

    def test_21_payment_block_per_company(self):
        """Cada compañía debe tener su propio bloque de pago independiente."""
        company_2 = self.env["res.company"].create({
            "name": "Otra Empresa SAC",
            "quotation_payment_block": "<p>Cuenta BBVA: 111-222-333</p>",
        })
        self.assertIn("BBVA", company_2.quotation_payment_block)
        # La compañía original no se ve afectada
        self.assertNotIn("BBVA", self.env.company.quotation_payment_block)
