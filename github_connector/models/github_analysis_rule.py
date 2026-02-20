
import os
import pathspec
from pygount import SourceAnalysis

from odoo import fields, models


class GithubAnalysisRule(models.Model):
    _name = "github.analysis.rule"
    _description = "Github Analysis Rule"

    name = fields.Char(required=True)
    group_id = fields.Many2one(
        string="Group", comodel_name="github.analysis.rule.group", required=True
    )
    """
    Example paths: https://git-scm.com/docs/gitignore#_pattern_format
    """
    paths = fields.Text(
        help="Define with pathspec especification",
        default="*",
        required=True,
    )

    def _set_spec(self, lines):
        return pathspec.PathSpec.from_lines("gitignore", lines)

    def _get_matches(self, path):
        """
        Get all matches from rule paths (multiple per line allow in rule)
        in a local path
        """
        matches = []
        for root, _dirs, files in os.walk(path):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), path)
                matches.append(rel_path)
        
        # pathspec >= 0.12.0
        return self._set_spec(self.paths.splitlines()).match_files(matches)

    def _analysis_file(self, path):
        file_res = SourceAnalysis.from_file(path, "")
        return {
            "path": file_res._path,
            "language": file_res._language,
            "code": file_res._code,
            "documentation": file_res._documentation,
            "empty": file_res._empty,
            "string": file_res._string,
        }
