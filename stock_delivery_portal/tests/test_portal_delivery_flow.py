from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

class TestPortalDeliveryFlow(TransactionCase):
    """
    Pruebas de flujo de entregas para el portal de delivery.
    """
    def setUp(self):
        super().setUp()
        self.Picking = self.env['stock.picking']
        self.User = self.env['res.users']
        self.DeliveryState = self.env['stock.delivery.state']
        self.PickingType = self.env['stock.picking.type']

        # Crear usuario portal
        self.portal_user = self.User.create({
            'name': 'Portal Delivery User',
            'login': 'portal_delivery',
        })
        self.env.ref('base.group_user').write({'user_ids': [(3, self.portal_user.id)]})
        self.env.ref('base.group_portal').write({'user_ids': [(4, self.portal_user.id)]})
        self.portal_user.password = 'portal_delivery'

        # Crear tipo de picking y estado
        self.picking_type = self.PickingType.create({
            'name': 'Portal Type',
            'sequence_code': 'PTEST',
            'code': 'outgoing',
        })
        self.delivery_state = self.DeliveryState.create({'name': 'Entregado', 'is_result_state': True})

        # Crear partner de prueba
        self.partner = self.env['res.partner'].create({
            'name': 'Test Partner',
        })
        # Crear picking asignado al usuario portal (delivery_partner_id)
        self.picking = self.Picking.create({
            'name': 'TESTPICK',
            'picking_type_id': self.picking_type.id,
            'delivery_state_id': self.delivery_state.id,
            'partner_id': self.partner.id,
            'delivery_partner_id': self.portal_user.partner_id.id,
        })

        # Crear picking NO asignado al usuario portal para probar restricción
        self.other_partner = self.env['res.partner'].create({'name': 'Other Partner'})
        self.other_picking = self.Picking.create({
            'name': 'OTHERPICK',
            'picking_type_id': self.picking_type.id,
            'delivery_state_id': self.delivery_state.id,
            'partner_id': self.partner.id,
            'delivery_partner_id': self.other_partner.id,
        })

    def test_portal_can_see_picking(self):
        """El usuario portal puede ver el picking asignado como delivery_partner"""
        pickings = self.Picking.with_user(self.portal_user).search([('id', '=', self.picking.id)])
        self.assertTrue(pickings, 'El usuario portal no puede ver el picking')

    def test_delivery_state_result(self):
        """El estado de entrega se marca como resultado correctamente"""
        self.assertTrue(self.picking.delivery_state_id.is_result_state)

    def test_portal_cannot_modify_other_picking(self):
        """El usuario portal no puede modificar pickings que NO le pertenecen (delivery_partner_id distinto)"""
        from odoo.exceptions import AccessError
        with self.assertRaises(AccessError):
            self.other_picking.with_user(self.portal_user).write({'name': 'NOPE'})
