from psycopg2 import IntegrityError

from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestSaasProductOperation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.blueprint = cls.env['saas.product.blueprint'].create({
            'name': 'openclaw',
            'domain': 'orquestio.com',
        })
        cls.other_blueprint = cls.env['saas.product.blueprint'].create({
            'name': 'other-product',
            'domain': 'other.example.com',
        })

    def _create_operation(self, blueprint=None, **overrides):
        vals = {
            'blueprint_id': (blueprint or self.blueprint).id,
            'code': 'upgrade',
            'label': 'Upgrade',
            'script_path': '/opt/orquestio/scripts/upgrade.sh',
        }
        vals.update(overrides)
        return self.env['saas.product.operation'].create(vals)

    def test_create_operation_with_params(self):
        """Crear blueprint + operation + 2 params; verificar relaciones."""
        operation = self._create_operation()
        param_target = self.env['saas.product.operation.param'].create({
            'operation_id': operation.id,
            'name': 'target_version',
            'label': 'Target Version',
            'type': 'char',
        })
        param_force = self.env['saas.product.operation.param'].create({
            'operation_id': operation.id,
            'name': 'force',
            'label': 'Force',
            'type': 'boolean',
            'default_value': 'False',
        })

        self.assertIn(operation, self.blueprint.operation_ids)
        self.assertEqual(self.blueprint.operation_ids, operation)
        self.assertEqual(len(operation.param_ids), 2)
        self.assertEqual(
            set(operation.param_ids.mapped('name')),
            {'target_version', 'force'},
        )
        self.assertIn(param_target, operation.param_ids)
        self.assertIn(param_force, operation.param_ids)

    def test_unique_code_per_blueprint_constraint(self):
        """Dos operations con mismo code y blueprint debe fallar."""
        self._create_operation(code='restart')
        with mute_logger('odoo.sql_db'):
            with self.assertRaises(IntegrityError):
                with self.env.cr.savepoint():
                    self._create_operation(code='restart')

    def test_same_code_different_blueprints_allowed(self):
        """Mismo code en blueprints distintos debe funcionar."""
        op1 = self._create_operation(code='restart')
        op2 = self._create_operation(blueprint=self.other_blueprint, code='restart')
        self.assertNotEqual(op1.id, op2.id)
        self.assertEqual(op1.code, op2.code)
        self.assertNotEqual(op1.blueprint_id, op2.blueprint_id)

    def test_cascade_delete_operation_removes_params(self):
        """Borrar una operation borra sus params."""
        operation = self._create_operation()
        param = self.env['saas.product.operation.param'].create({
            'operation_id': operation.id,
            'name': 'foo',
            'label': 'Foo',
            'type': 'char',
        })
        param_id = param.id
        operation.unlink()
        remaining = self.env['saas.product.operation.param'].search(
            [('id', '=', param_id)]
        )
        self.assertFalse(remaining)

    def test_cascade_delete_blueprint_removes_operations_and_params(self):
        """Borrar blueprint borra operations y transitivamente params."""
        blueprint = self.env['saas.product.blueprint'].create({
            'name': 'temp-product',
            'domain': 'temp.example.com',
        })
        operation = self.env['saas.product.operation'].create({
            'blueprint_id': blueprint.id,
            'code': 'upgrade',
            'label': 'Upgrade',
            'script_path': '/opt/scripts/upgrade.sh',
        })
        param = self.env['saas.product.operation.param'].create({
            'operation_id': operation.id,
            'name': 'version',
            'label': 'Version',
            'type': 'char',
        })
        op_id = operation.id
        param_id = param.id

        blueprint.unlink()

        self.assertFalse(
            self.env['saas.product.operation'].search([('id', '=', op_id)])
        )
        self.assertFalse(
            self.env['saas.product.operation.param'].search([('id', '=', param_id)])
        )

    def test_default_values(self):
        """Defaults: timeout_seconds=300, requires_drain=False, visible_in_admin=True, visible_in_portal=False."""
        operation = self._create_operation()
        self.assertEqual(operation.timeout_seconds, 300)
        self.assertFalse(operation.requires_drain)
        self.assertTrue(operation.visible_in_admin)
        self.assertFalse(operation.visible_in_portal)
        self.assertEqual(operation.sequence, 10)
