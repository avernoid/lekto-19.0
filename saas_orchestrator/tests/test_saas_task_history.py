from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestSaasTaskHistory(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})
        cls.blueprint = cls.env['saas.product.blueprint'].create({
            'name': 'openclaw',
            'domain': 'orquestio.com',
        })
        cls.plan = cls.env['saas.product.plan'].create({
            'name': 'starter',
            'blueprint_id': cls.blueprint.id,
        })
        cls.tenant = cls.env['saas.tenant'].create({
            'name': 'tenant-th-001',
            'partner_id': cls.partner.id,
        })
        cls.instance = cls.env['saas.instance'].create({
            'name': 'inst-th-001',
            'tenant_id': cls.tenant.id,
            'plan_id': cls.plan.id,
            'state': 'draft',
        })
        cls.operation = cls.env['saas.product.operation'].create({
            'blueprint_id': cls.blueprint.id,
            'code': 'upgrade',
            'label': 'Upgrade',
            'script_path': '/opt/orquestio/scripts/upgrade.sh',
        })

    def test_create_history_with_all_new_fields(self):
        """Crear un record con todos los campos nuevos y verificar que persiste."""
        record = self.env['saas.task.history'].create({
            'instance_id': self.instance.id,
            'operation_id': self.operation.id,
            'task_type': 'upgrade',
            'payload': '{"target_version": "19.0"}',
            'state': 'queued',
            'ssm_command_id': 'cmd-abc-123',
            'orchestrator_task_id': 'uuid-deadbeef-0001',
        })
        record.flush_recordset()
        record.invalidate_recordset()
        self.assertEqual(record.operation_id, self.operation)
        self.assertEqual(record.ssm_command_id, 'cmd-abc-123')
        self.assertEqual(record.orchestrator_task_id, 'uuid-deadbeef-0001')
        self.assertEqual(record.task_type, 'upgrade')
        self.assertEqual(record.state, 'queued')
        self.assertTrue(record.created_at)

    def test_operation_id_is_nullable(self):
        """operation_id nullable: crear record sin operation debe funcionar (retrocompat)."""
        record = self.env['saas.task.history'].create({
            'instance_id': self.instance.id,
            'task_type': 'legacy-task',
            'state': 'completed',
        })
        self.assertFalse(record.operation_id)
        self.assertEqual(record.task_type, 'legacy-task')

    def test_ondelete_set_null_on_operation(self):
        """Al borrar la operation, el FK en task.history queda NULL (ondelete=set null)."""
        record = self.env['saas.task.history'].create({
            'instance_id': self.instance.id,
            'operation_id': self.operation.id,
            'task_type': 'upgrade',
        })
        record_id = record.id
        self.operation.unlink()
        record.invalidate_recordset()
        surviving = self.env['saas.task.history'].browse(record_id)
        self.assertTrue(surviving.exists())
        self.assertFalse(surviving.operation_id)

    def test_cascade_delete_from_instance(self):
        """Borrar una instance borra su task.history (ondelete=cascade)."""
        tmp_instance = self.env['saas.instance'].create({
            'name': 'inst-th-tmp',
            'tenant_id': self.tenant.id,
            'plan_id': self.plan.id,
            'state': 'draft',
        })
        record = self.env['saas.task.history'].create({
            'instance_id': tmp_instance.id,
            'task_type': 'restart',
        })
        record_id = record.id
        tmp_instance.unlink()
        self.assertFalse(
            self.env['saas.task.history'].search([('id', '=', record_id)])
        )

    def test_orchestrator_task_id_is_indexed(self):
        """El campo orchestrator_task_id debe tener index=True (metadata)."""
        field = self.env['saas.task.history']._fields['orchestrator_task_id']
        self.assertTrue(field.index)

    def test_result_s3_path_field_removed(self):
        """El campo vestigio result_s3_path ya no debe existir en el modelo."""
        self.assertNotIn(
            'result_s3_path',
            self.env['saas.task.history']._fields,
        )
        # Al pasarlo en create(), Odoo tira ValueError por campo inválido.
        with self.assertRaises(ValueError):
            self.env['saas.task.history'].create({
                'instance_id': self.instance.id,
                'result_s3_path': '/foo/bar',
            })
