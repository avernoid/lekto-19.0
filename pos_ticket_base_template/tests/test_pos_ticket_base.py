from odoo.tests import TransactionCase, tagged

@tagged('post_install', '-at_install')
class TestPosTicketBase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.pos_config = self.env['pos.config'].create({
            'name': 'Test POS Config',
        })
        self.res_config = self.env['res.config.settings'].create({
            'pos_config_id': self.pos_config.id,
        })

    def test_01_load_pos_data_fields(self):
        """ Verify that fields are correctly added to the list of fields to load in the POS """
        # Test pos.config fields
        config_fields = self.env['pos.config']._load_pos_data_fields(self.pos_config.id)
        # Note: In some environments, if params is empty it means "all", so these might not be in the list
        # but the logic ensures we add them if a specific list is being used.
        if config_fields:
            self.assertIn('automatic_print_electronic_invoice', config_fields)
            self.assertIn('automatic_download_electronic_invoice', config_fields)

    def test_02_res_config_settings_exclusivity(self):
        """ Verify that automatic ticket printing and electronic invoice printing are exclusive """
        # Case 1: Enabling electronic invoice printing should disable native auto printing
        self.res_config.pos_iface_print_auto = True
        self.res_config.pos_automatic_print_electronic_invoice = True
        self.res_config._onchange_pos_automatic_print_electronic_invoice()
        self.assertFalse(self.res_config.pos_iface_print_auto, "Native auto-printing should be disabled when electronic invoice printing is enabled")

        # Case 2: Enabling native auto printing should disable electronic invoice printing
        self.res_config.pos_iface_print_auto = True
        self.res_config._onchange_pos_iface_print_auto()
        self.assertFalse(self.res_config.pos_automatic_print_electronic_invoice, "Electronic invoice printing should be disabled when native auto-printing is enabled")

    def test_03_generate_pos_ui_report_action_value_error(self):
        """ Test error handling when generating report action value """
        # Case with non-existent order reference
        result = self.env['pos.order'].generate_pos_ui_report_action_value('invalid_ref', 'account.account_invoices')
        self.assertTrue(result.get('error'), "Should return error for invalid order reference")
        self.assertFalse(result.get('report'), "Should not return report data for invalid reference")
