# Copyright 2020-2022 Tecnativa - Víctor Martínez
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
import shutil
import tempfile
import responses
from unittest import mock
from contextlib import contextmanager
from odoo.tests.common import TransactionCase


class TestGithubConnectorCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.info_keys = [
            "code_count",
            "documentation_count",
            "empty_count",
            "string_count",
            "scanned_files",
        ]
        cls.model_gos = cls.env["github.organization.serie"]
        cls.model_gr = cls.env["github.repository"]
        cls.model_grb = cls.env["github.repository.branch"]
        cls.oca = cls.env.ref("github_connector_api.oca_organization", raise_if_not_found=False)
        if not cls.oca:
            cls.oca = cls.env["github.organization"].create({
                "name": "OCA",
                "github_name": "OCA",
            })
        cls.serie_13 = cls.env.ref(
            "github_connector_api.oca_organization_serie_13", raise_if_not_found=False
        )
        if not cls.serie_13:
            cls.serie_13 = cls.env["github.organization.serie"].create({
                "name": "13.0",
                "sequence": 10,
                "organization_id": cls.oca.id,
            })
        # Crear la organización OCA si no existe
        cls.repository_ocb = cls.model_gr.create(
            {
                "name": "OCB",
                "organization_id": cls.oca.id,
                "github_id_external": 20558462,
            }
        )
        cls.repository_interface_github = cls.model_gr.create(
            {
                "name": "interface-github",
                "organization_id": cls.oca.id,
                "github_id_external": 70173147,
            }
        )
        # repository branch
        cls.repository_ocb_13 = cls.model_grb.create(
            {
                "name": cls.serie_13.name,
                "organization_id": cls.oca.id,
                "repository_id": cls.repository_ocb.id,
                "organization_serie_id": cls.serie_13.id,
            }
        )
        cls.repository_interface_github_13 = cls.model_grb.create(
            {
                "name": cls.serie_13.name,
                "organization_id": cls.oca.id,
                "repository_id": cls.repository_interface_github.id,
                "organization_serie_id": cls.serie_13.id,
            }
        )
        cls.github_source_code_local_path = tempfile.mkdtemp()
        cls.env["ir.config_parameter"].set_param("github.access_token", "test")
        cls.env["ir.config_parameter"].set_param("github_source_code_local_path", cls.github_source_code_local_path)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.github_source_code_local_path, ignore_errors=True)
        super().tearDownClass()

    @contextmanager
    def mock_github_requests(self, rsps):
        def bypass_send(session, request, **kwargs):
            adapter = session.get_adapter(url=request.url)
            return adapter.send(request, **kwargs)

        with mock.patch("requests.Session.send", side_effect=bypass_send, autospec=True):
            yield

    def _download_and_analyze(self, repo_branch):
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            mock_ctx = self.mock_github_requests(self, rsps) if isinstance(self, type) else self.mock_github_requests(rsps)
            with mock_ctx:
                if isinstance(self, type):
                    self._set_github_responses(self, rsps)
                else:
                    self._set_github_responses(rsps)
                if repo_branch.state == "to_download":
                    repo_branch._download_code()
                repo_branch.analyze_code_one()
            
    def _set_github_responses(self, rsps):
        # This method should be overridden in child classes or defined here to add responses to rsps
        pass
