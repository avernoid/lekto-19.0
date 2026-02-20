# Copyright 2023 Prometeo - Fernando
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import logging
from datetime import datetime
from unittest.mock import MagicMock, patch

from .common import TestGithubConnectorCommon

_logger = logging.getLogger(__name__)


class TestGithubSync(TestGithubConnectorCommon):
    def test_sync_repository_search_api(self):
        """Test that sync uses Search API and updates cursor."""
        # Configurar datos de prueba
        organization = self.oca
        organization.last_search_cursor = False
        organization.repository_sync_limit = 10

        # Mockear el objeto Github y su método search_repositories
        # No podemos usar 'responses' fácilmente porque search_repositories devuelve un objeto PaginatedList complejo
        # Es más fácil mockear la llamada al método del conector
        
        mock_gh_repo = MagicMock()
        mock_gh_repo.name = "test-repo-1"
        mock_gh_repo.full_name = "OCA/test-repo-1"
        mock_gh_repo.id = 12345
        mock_gh_repo.html_url = "https://github.com/OCA/test-repo-1"
        mock_gh_repo.description = "Test Repo"
        mock_gh_repo.pushed_at = datetime(2023, 10, 27, 12, 0, 0)
        mock_gh_repo.updated_at = datetime(2023, 10, 27, 12, 0, 0)
        mock_gh_repo.clone_url = "https://github.com/OCA/test-repo-1.git"
        mock_gh_repo.size = 100
        mock_gh_repo.stargazers_count = 10
        mock_gh_repo.watchers_count = 10
        mock_gh_repo.forks_count = 5
        mock_gh_repo.open_issues_count = 1
        mock_gh_repo.default_branch = "14.0"
        mock_gh_repo.topics = ["odoo"]
        # Mocking get_branches to avoid network calls during button_sync_branch
        mock_gh_repo.get_branches.return_value = []
        mock_gh_repo.get_teams.return_value = []

        # Patch del método get_github_connector para devolver nuestro mock
        with patch.object(type(organization), 'get_github_connector') as mock_get_connector:
            mock_gh_api = MagicMock()
            mock_get_connector.return_value = mock_gh_api
            
            # Configurar el search_repositories para devolver nuestra lista ficticia
            mock_gh_api.search_repositories.return_value = [mock_gh_repo]

            # Ejecutar la sincronización
            organization.button_sync_repository()

            # Verificaciones
            # 1. Se llamó a search_repositories con la query correcta?
            mock_gh_api.search_repositories.assert_called_once()
            call_args = mock_gh_api.search_repositories.call_args
            self.assertIn("query", call_args[1])
            self.assertIn("org:", call_args[1]['query'])

            # 2. Se creó el repositorio en Odoo?
            repo = self.env['github.repository'].search([('github_id_external', '=', '12345')])
            self.assertTrue(repo)
            self.assertEqual(repo.name, "test-repo-1")

            # 3. Se actualizó el cursor?
            self.assertTrue(organization.last_search_cursor)
            self.assertEqual(organization.last_search_cursor, datetime(2023, 10, 27, 12, 0, 0))

            _logger.info("Test Sync Search API Passed!")
