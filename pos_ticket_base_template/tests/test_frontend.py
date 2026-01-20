from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestFrontend(TestPointOfSaleHttpCommon):
    def test_pos_ticket_base_tour(self):
        """ Run the JS tour to verify POS configuration loading """
        # We use the main_pos_config from the parent class
        self.main_pos_config.open_ui()
        
        # Run the tour using the standard helper
        # We use a long timeout for Odoo SH
        self.start_pos_tour("pos_ticket_base_tour", login="pos_admin", timeout=240)
