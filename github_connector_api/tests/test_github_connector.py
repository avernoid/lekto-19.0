# Copyright 2021-2022 Tecnativa - Víctor Martínez
# Copyright 2021 Tecnativa - João Marques
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json

import responses

from odoo.tools.misc import file_path
import odoo.tests

from .common import TestGithubConnectorCommon


@odoo.tests.tagged("post_install", "-at_install")
class TestGithubConnector(TestGithubConnectorCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # 1. Create User
        cls.portal_user = cls.env['res.users'].create({
            'name': 'Test Portal', 
            'login': 'test_portal_login'
        })
        
        # 2. GROUP CLEANUP (Critical)
        # Remove 'Internal User' (added by default)
        group_user = cls.env.ref('base.group_user')
        group_portal = cls.env.ref('base.group_portal')
        cls.portal_user.write({'groups_id': [(3, group_user.id), (4, group_portal.id)]})

        # Activate Spanish for translation tests (if needed later)
        cls.env['res.lang']._activate_lang('es_ES')
        cls.portal_user.lang = 'es_ES'

    def setUp(self):
        super().setUp()
        with open(
            file_path(
                "github_connector_api/tests/res/github_user_OCA-git-bot_response.json"
            )
        ) as jsonfile:
            self.user_data = json.loads(jsonfile.read())
        


    def test_partner_get_from_id_or_create(self):
        with responses.RequestsMock() as rsps:
            with self.mock_github_requests(rsps):
                rsps.add(
                    responses.GET,
                    "https://api.github.com:443/users/OCA-git-bot",
                    json=self.user_data,
                    status=200,
                )
                rsps.add(
                    responses.GET,
                    "https://api.github.com:443/user/8723280",
                    json=self.user_data,
                    status=200,
                )
                rsps.add(
                    responses.GET,
                    "https://api.github.com:443/orgs/OCA-git-bot",
                    json={
                        "message": "Not Found",
                    },
                    status=404,
                )
                partner_model = self.env["res.partner"]
                partner = partner_model.create_from_name("OCA-git-bot")
                self.assertEqual(partner.github_name, "OCA-git-bot")
                # Check create process not really create new record
                res = partner_model.get_from_id_or_create(data={"login": "OCA-git-bot"})
                self.assertEqual(partner.id, res.id)
                # Try to archive record and try to create again
                partner.active = False
                res = partner_model.get_from_id_or_create(data={"login": "OCA-git-bot"})
                self.assertEqual(partner.id, res.id)
