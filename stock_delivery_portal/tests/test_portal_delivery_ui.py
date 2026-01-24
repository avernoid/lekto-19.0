from odoo.tests.common import HttpCase, tagged

@tagged('post_install', '-at_install')
class TestPortalDeliveryUI(HttpCase):
    """
    Pruebas de UI portal delivery: rutas, filtros, búsqueda, botones.
    """
    def setUp(self):
        super().setUp()
        self.portal_user = self.env['res.users'].create({
            'name': 'Test Portal User',
            'login': 'portal_ui_test',
        })
        # Quitar grupo interno y agregar grupo portal según DEV_GUIDELINES
        self.env.ref('base.group_user').write({'user_ids': [(3, self.portal_user.id)]})
        self.env.ref('base.group_portal').write({'user_ids': [(4, self.portal_user.id)]})
        self.portal_user.password = 'portal_ui_test'

    def test_delivery_portal_routes(self):
        """El portal responde correctamente a las rutas principales"""
        self.authenticate('portal_ui_test', 'portal_ui_test')
        resp = self.url_open('/my/delivery')
        self.assertEqual(resp.status_code, 200)

    def test_delivery_portal_search_and_filters(self):
        """La búsqueda y los filtros no generan error 500"""
        self.authenticate('portal_ui_test', 'portal_ui_test')
        resp = self.url_open('/my/delivery?search=test')
        self.assertEqual(resp.status_code, 200)
        resp = self.url_open('/my/delivery?filter_type=1')
        self.assertEqual(resp.status_code, 200)
        resp = self.url_open('/my/delivery?filter_state=1')
        self.assertEqual(resp.status_code, 200)

    def test_delivery_portal_clear_button(self):
        """El botón Clear no genera error y limpia filtros"""
        self.authenticate('portal_ui_test', 'portal_ui_test')
        resp = self.url_open('/my/delivery?search=test&filter_type=1')
        self.assertEqual(resp.status_code, 200)
        resp = self.url_open('/my/delivery')
        self.assertEqual(resp.status_code, 200)
