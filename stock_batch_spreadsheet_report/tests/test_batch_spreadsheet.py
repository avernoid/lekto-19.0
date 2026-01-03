from odoo.tests.common import TransactionCase, new_test_user
from odoo.exceptions import AccessError

class TestBatchSpreadsheet(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create a user with Inventory User access
        cls.stock_user = new_test_user(cls.env, login='stock_test_user', groups='stock.group_stock_user')
        
        # Create a dummy Spreadsheet record to serve as the template's data
        cls.spreadsheet = cls.env['stock.batch.spreadsheet'].create({
            'name': 'Template Spreadsheet',
            'spreadsheet_data': b'{}', # Dummy empty JSON
        })

        # Create a Spreadsheet Template
        cls.template = cls.env['stock.batch.spreadsheet.template'].create({
            'name': 'Test Template',
            'spreadsheet_id': cls.spreadsheet.id,
        })
        
        # Create a Picking Type and assign the template
        cls.picking_type = cls.env['stock.picking.type'].create({
            'name': 'Test Operation Type',
            'code': 'internal',
            'sequence_code': 'TEST',
            'batch_spreadsheet_template_id': cls.template.id,
        })
        
        # Create a Batch Picking associated with this Picking Type
        cls.batch = cls.env['stock.picking.batch'].create({
            'user_id': cls.stock_user.id,
            'company_id': cls.env.company.id,
            'picking_type_id': cls.picking_type.id,
        })

    def test_01_lazy_creation(self):
        """Test that a report is automatically created if it doesn't exist."""
        # 1. Verify initial state: 0 reports
        self.assertEqual(self.batch.spreadsheet_count, 0)
        
        # 2. Simulate clicking the "Reports" button (lazy creation)
        # We simulate the logic inside action_view_spreadsheet_reports
        # Ideally we should call the method, but it returns an action. 
        # For a unit test, we can check the side effect.
        
        # Let's ensure we have a template available or the logic handles it.
        # The detailed logic requires a template to exist. The module picks the first one or default.
        
        # Call the method as the stock user
        action = self.batch.with_user(self.stock_user).action_view_spreadsheet_reports()
        self.batch.invalidate_recordset()
        
        # 3. Verify side effect: 1 report should be created
        self.assertEqual(self.batch.spreadsheet_count, 1, "A spreadsheet should have been lazy-created.")
        report = self.batch.spreadsheet_ids[0]
        self.assertTrue(report.exists())
        self.assertEqual(report.batch_id, self.batch)
        
        # 4. Verify the action returned opens the created report
        self.assertEqual(action['tag'], 'action_stock_batch_spreadsheet')
        self.assertEqual(action['params']['spreadsheet_id'], report.id)

    def test_02_archive_reset_workflow(self):
        """Test the 'Reset' workflow: Archive -> Create New."""
        # 1. Create first report
        self.batch.with_user(self.stock_user).action_view_spreadsheet_reports()
        self.batch.invalidate_recordset()
        report_1 = self.batch.spreadsheet_ids[0]
        self.assertTrue(report_1.active)
        
        # 2. Archive it (Move to Trash)
        report_1.action_archive()
        self.assertFalse(report_1.active)
        
        # 3. Verify Smart Button count is 0 (it ignores archived)
        self.batch.invalidate_recordset() # Refresh cache
        self.assertEqual(self.batch.spreadsheet_count, 0, "Archived reports should not count towards the smart button.")
        
        # 4. Click button again -> Create NEW report
        self.batch.with_user(self.stock_user).action_view_spreadsheet_reports()
        self.batch.invalidate_recordset()
        
        self.assertEqual(self.batch.spreadsheet_count, 1)
        report_2 = self.batch.spreadsheet_ids.filtered(lambda r: r.active)
        
        self.assertEqual(len(report_2), 1)
        self.assertNotEqual(report_1.id, report_2.id, "A fresh report instance should be created.")

    def test_03_cascade_deletion(self):
        """Test that deleting the Batch deletes the reports."""
        # 1. Create a report
        self.batch.with_user(self.stock_user).action_view_spreadsheet_reports()
        self.batch.invalidate_recordset()
        report = self.batch.spreadsheet_ids[0]
        report_id = report.id
        
        # 2. Delete the Batch
        self.batch.unlink()
        
        # 3. Verify report is gone
        search_report = self.env['stock.batch.spreadsheet'].search([('id', '=', report_id)])
        self.assertFalse(search_report.exists(), "Report should be cascade-deleted with the Batch.")

    def test_04_open_existing_report(self):
        """Test that if a report exists, it just opens it without creating duplicate."""
        # 1. Create first report
        self.batch.with_user(self.stock_user).action_view_spreadsheet_reports()
        self.batch.invalidate_recordset()
        self.assertEqual(self.batch.spreadsheet_count, 1)
        report_id = self.batch.spreadsheet_ids[0].id
        
        # 2. Click button again
        action = self.batch.with_user(self.stock_user).action_view_spreadsheet_reports()
        self.batch.invalidate_recordset()
        
        # 3. Verify NO new report created
        self.assertEqual(self.batch.spreadsheet_count, 1)
        self.assertEqual(action['tag'], 'action_stock_batch_spreadsheet')
        self.assertEqual(action['params']['spreadsheet_id'], report_id, "Should open the existing report.")
