from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
import base64

class TestTaskEvidence(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Product = self.env['product.product']
        self.Task = self.env['project.task']
        self.Evidence = self.env['project.task.evidence']

        # Create a product with evidence requirements
        self.product_required = self.Product.create({
            'name': 'Test Product Required',
            'evidence_required': True,
            'evidence_min_qty': 1,
            'evidence_max_qty': 2,
        })

        self.task = self.Task.create({
            'name': 'Test Task',
        })
        
        # Mock sale line linkage (simplified as we don't depend on sale execution here but model structure)
        # We need to simulate the sale_line_id logic if we want to test that constraint.
        # Since creating actual SO is heavy, we might check the constraint logic directly 
        # or mock the sale_line_id if possible. 
        # For this unit test, let's create a dummy linkage if the field exists.

    def test_evidence_constraints(self):
        """ Test evidence max quantity constraint """
        # Create a Sales Order Line mock is tricky without full sale flow, 
        # so we will rely on checking if the method logic works when manually invoked or 
        # simply test the Wizard validation which is easier to reach.
        
        wizard = self.env['project.task.evidence.wizard'].create({
            'task_id': self.task.id,
            'product_id': self.product_required.id,
            'name': 'Evidence 1',
            'image': b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==',
        })
        wizard.action_save()
        
        self.assertEqual(len(self.task.evidence_ids), 1)
        
        wizard2 = self.env['project.task.evidence.wizard'].create({
            'task_id': self.task.id,
            'product_id': self.product_required.id,
            'name': 'Evidence 2',
            'image': b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==',
        })
        wizard2.action_save()
        self.assertEqual(len(self.task.evidence_ids), 2)
        
        # Third one should fail
        wizard3 = self.env['project.task.evidence.wizard'].create({
            'task_id': self.task.id,
            'product_id': self.product_required.id,
            'name': 'Evidence 3',
            'image': b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==',
        })
        
        with self.assertRaises(ValidationError):
            wizard3.action_save()


    def test_product_constraint(self):
        """ Test product min/max constraint """
        with self.assertRaises(ValidationError):
            self.Product.create({
                'name': 'Invalid Product',
                'evidence_required': True,
                'evidence_min_qty': 5,
                'evidence_max_qty': 2,
            })
