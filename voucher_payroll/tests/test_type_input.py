from odoo.tests.common import TransactionCase


class TestTypeInputs(TransactionCase):

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        user_admin = self.env.ref("base.user_admin")
        self.env = self.env(user=user_admin)
        self.TypeInputs = self.env["type.inputs"]
        self.type_input1 = self.TypeInputs.create({
            "name": "Input 1",
            "code": "001",
            "description": "Description 1"
        })
        print("Setup done  ************************")

    def test_fields_values(self):
        "Check field values"
        self.assertEqual(self.type_input1.name, "Input 1")
        self.assertEqual(self.type_input1.code, "001")
        self.assertEqual(self.type_input1.description, "Description 1")
        print("Test fields values done +++++++++++++++++++++++++")
