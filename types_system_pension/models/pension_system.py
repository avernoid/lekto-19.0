from odoo import fields, models


class PensionSystem(models.Model):
    _name = 'pension.system'
    _description = 'Pension System'

    code = fields.Char(
        string='Code',
        help="Official SUNAT/SBS code that identifies this pension system. Used in payroll reporting and electronic filings."
    )
    pension_system = fields.Char(
        string='Pension Regime',
        help="Full official name of the pension regime as registered with the Peruvian authority (e.g., 'Sistema Nacional de Pensiones - SNP')."
    )
    name = fields.Char(
        string='Abbreviation',
        help="Short name or abbreviation used to identify this pension system in employee records and payroll reports (e.g., SNP, AFP Integra)."
    )
    private_sector = fields.Boolean(
        string='Private Sector',
        help="Check if this pension system applies to private-sector employees. Used to filter applicable regimes during payroll setup."
    )
    public_sector = fields.Boolean(
        string='Public Sector',
        help="Check if this pension system applies to public-sector employees. Used to filter applicable regimes during payroll setup."
    )
    other_entities = fields.Boolean(
        string='Other Entities',
        help="Check if this pension system applies to employees of other entities not classified as strictly private or public sector."
    )
    cuspp = fields.Boolean(
        string='Requires CUSPP',
        help="Enable if affiliates of this pension system receive a CUSPP (Código Único de Sistema Privado de Pensiones) code. "
             "When enabled, the CUSPP Active flag on the employee will be set automatically."
    )
    comis_pension_ids = fields.One2many(
        comodel_name='comis.system.pension',
        inverse_name='pension_id',
        string='Commission Rates',
        help="Historical commission rates for this pension system (AFP). Each line covers a date range with specific rates "
             "for fund, bonus, mixed-flow, flow, and balance commission types."
    )
