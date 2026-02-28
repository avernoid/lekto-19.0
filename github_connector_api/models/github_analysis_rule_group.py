
from odoo import fields, models


class GithubAnalysisRule(models.Model):
    _name = "github.analysis.rule.group"
    _description = "Github Analysis Rule Group"

    name = fields.Char(required=True)
