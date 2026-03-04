from odoo import api, fields, models


class EpsCredit(models.Model):
    _name = "eps.credit"
    _description = "EPS credit"

    since = fields.Date(
        string='Since', 
        required=True,
        help="Start date of the EPS credit period."
    )
    until = fields.Date(
        string='Until',
        required=True,
        help="End date of the EPS credit period."
    )
    affiliated_workers = fields.Integer(
        string='Number of EPS Affiliated Workers',
        readonly=False,
        help="Total number of workers affiliated to the EPS during this period."
    )
    computable_remuneration_health_input = fields.Float(
        string='Computable Remuneration Health Input (All EPS Affiliates)',
        help="Total computable remuneration for health contributions of all EPS affiliated workers."
    )
    eps_credit = fields.Integer(
        string='EPS Credit',
        readonly=False,
        help="Calculated EPS credit amount based on health contributions."
    )
    eps_service_cost = fields.Float(
        string='EPS Service Cost of Affiliated Workers (Includes Tax)',
        help="Cost of the EPS service billed for the workers during the period, including applicable taxes."
    )
    uit = fields.Float(
        string='Tax Unit (UIT)',
        readonly=False,
        help="Tax Unit (UIT) value applicable for the period's calculations."
    )
    uit_limit_affiliated_workers = fields.Float(
        string='10% Tax Unit Limit x Number of EPS Affiliated Workers',
        readonly=False,
        help="Calculated limit based on 10% of the Tax Unit per affiliated worker."
    )
    adjustment = fields.Float(
        string='Adjustment',
        help="Manual adjustment for the final EPS credit if necessary."
    )
    final_eps_credit = fields.Float(
        string='Final EPS Credit',
        readonly=False,
        help="Final EPS credit applicable after considering limits and adjustments."
    )
    
    @api.depends('since', 'until')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f'[{record.since} - {record.until}]'

    def compute_fields(self):
        affiliated_workers = self.env['hr.employee'].search([
            ('current_version_id.active', '=', True),
            ('current_version_id.active_employee', '=', True),
        ])

        affiliated_workers = affiliated_workers.filtered(lambda w: w.current_version_id.is_current)

        workers = affiliated_workers.filtered(lambda w: w.health_regime_id.code == '01')
        self.affiliated_workers = len(workers)

        amount = 0
        for worker in workers:
            for slip in worker.slip_ids:
                if self.since <= slip.date_start_dt <= self.until and slip.state == 'done':
                    for line in slip.line_ids:
                        if line.code == 'ESA_100':
                            amount += line.amount
        self.computable_remuneration_health_input = amount

        self.eps_credit = round(self.computable_remuneration_health_input * 0.09 * 0.25)

        uit_record = self.env['various.data.uit'].search([('is_active', '=', True)], limit=1)
        self.uit = uit_record.uit_amount if uit_record else 0.0

        self.uit_limit_affiliated_workers = self.uit * 0.1 * self.affiliated_workers

        final_eps_credit = min(
            self.eps_credit,
            self.eps_service_cost if self.eps_service_cost != 0.0 else self.eps_credit,
            self.uit_limit_affiliated_workers
        )
        self.final_eps_credit = self.adjustment if self.adjustment != 0.0 else final_eps_credit

            

