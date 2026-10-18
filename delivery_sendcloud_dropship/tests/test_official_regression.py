from odoo.tests import tagged

from odoo.addons.delivery_sendcloud.tests.test_delivery_sendcloud import TestDeliverySendCloud


@tagged('post_install', '-at_install', '-standard', 'sendcloud_regression')
class TestOfficialSendcloudWithDropship(TestDeliverySendCloud):
    """The official connector tests, run with this module installed (they are at_install upstream,
    so they never go through SendCloudDropship). Not standard: three of them are broken upstream
    in 18.0 (they use stock.move.quantity_done). Run with --test-tags sendcloud_regression."""

    allow_inherited_tests_method = True  # the Odoo 18 loader only runs methods defined on the class
