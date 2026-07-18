from odoo import fields, models


class StockKardexValued(models.Model):
    """Valued Kardex line, populated per run by the wizard (D7).

    Regular ``models.Model`` with stored columns so that opening/closing balances
    (which depend on ``date_from``) can be aggregated in the group header. NOT a
    ``_auto=False`` SQL view.

    Rows are owned by the user that generated them (``create_uid``) and wiped on the
    next run of that user (see the wizard). The balance columns (``bal_*``) and every
    unit-cost column carry ``aggregator=False`` because a naive ``sum`` of a running
    balance or a unit cost is meaningless (see D12/§7).
    """
    _name = 'stock.kardex.valued'
    _description = 'Valued Inventory Kardex (reconciled with the GL)'
    _order = 'product_id, date, id'
    _rec_name = 'document'

    # --- Identity -----------------------------------------------------------
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, index=True,
        help="Company whose stock valuation this Kardex line belongs to. The balance is "
             "computed at company level (one cost per product/company).")
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        help="Currency used to display the monetary values, taken from the company.")
    report_date_from = fields.Date(
        string='From',
        help="Start of the period this line was generated for (opening = state at the "
             "start of this date).")
    report_date_to = fields.Date(
        string='To',
        help="End of the period this line was generated for (closing = state at the end "
             "of this date).")
    product_tmpl_id = fields.Many2one(
        'product.template', string='Product Template', index=True,
        help="Product template. Used as the first grouping level; balances are valid under "
             "the canonical Template → Product grouping.")
    product_id = fields.Many2one(
        'product.product', string='Product', index=True,
        help="Product variant this movement or balance refers to.")
    date = fields.Datetime(
        string='Date', index=True,
        help="Date/time of the movement or revaluation event (empty for a pure opening "
             "balance row).")
    cost_method = fields.Selection([
        ('standard', 'Standard Price'),
        ('fifo', 'First In First Out (FIFO)'),
        ('average', 'Average Cost (AVCO)'),
    ], string='Cost Method', index=True,
        help="Costing method used to value this product at company level: Standard, FIFO "
             "or Average (AVCO). Each method is replayed with its own engine.")

    # --- Analysis dimensions (D12; referential -> hidden by default) ---------
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse (referential)',
        help="Referential label only. The Kardex balance is computed at COMPANY level "
             "(one cost per product/company, like Odoo's own valuation); the warehouse "
             "is never the basis of the balance. Do not read balances filtered by warehouse.")
    location_id = fields.Many2one(
        'stock.location', string='Source Location',
        help="Source location of the underlying stock move (analysis dimension only).")
    location_dest_id = fields.Many2one(
        'stock.location', string='Destination Location',
        help="Destination location of the underlying stock move (analysis dimension only).")
    picking_type_id = fields.Many2one(
        'stock.picking.type', string='Operation Type',
        help="Operation type (receipt, delivery, internal, …) of the underlying move. "
             "An Odoo operation, not a SUNAT code.")
    partner_id = fields.Many2one(
        'res.partner', string='Partner',
        help="Partner of the related transfer, when available (analysis dimension only).")
    product_categ_id = fields.Many2one(
        'product.category', string='Product Category', index=True,
        help="Product category, available as an analysis dimension and group-by.")
    line_kind = fields.Selection([
        ('opening', 'Opening'),
        ('in', 'Incoming'),
        ('out', 'Outgoing'),
        ('revaluation', 'Revaluation'),
    ], string='Line Kind', index=True,
        help="Nature of the line: an opening balance, an incoming movement, an outgoing "
             "movement, or a value revaluation (cost/standard-price change).")

    # --- Document / navigation ----------------------------------------------
    document = fields.Char(
        string='Document',
        help="Human-readable reference of the source document (transfer name or move "
             "reference; 'Revaluation' / 'Opening balance' for synthetic lines).")
    source_move_id = fields.Many2one(
        'stock.move', string='Stock Move',
        help="Stock move that produced this line, for navigation to the source movement.")
    picking_id = fields.Many2one(
        'stock.picking', string='Transfer',
        help="Transfer (picking) the source move belongs to, when available.")
    invoice_id = fields.Many2one(
        'account.move', string='Customer Invoice',
        help="Related customer invoice, when a link is available.")
    bill_id = fields.Many2one(
        'account.move', string='Vendor Bill',
        help="Related vendor bill, when a link is available.")

    # --- Opening (single cell per product) ----------------------------------
    ini_qty = fields.Float(
        string='Opening Qty', aggregator='sum',
        help="Quantity on hand at the start of the period (shown once per product).")
    ini_unit_cost = fields.Float(
        string='Opening Unit Cost', aggregator=False,
        help="Unit cost at the start of the period. Unit costs are never summed.")
    ini_value = fields.Monetary(
        string='Opening Value', currency_field='currency_id', aggregator='sum',
        help="Inventory value at the start of the period (shown once per product).")

    # --- Incoming -----------------------------------------------------------
    in_qty = fields.Float(
        string='In Qty', aggregator='sum',
        help="Incoming quantity of this movement (valued quantity).")
    in_unit_cost = fields.Float(
        string='In Unit Cost', aggregator=False,
        help="Unit cost of the incoming value (value / quantity). Never summed.")
    in_value = fields.Monetary(
        string='In Value', currency_field='currency_id', aggregator='sum',
        help="Incoming value added to the balance by this movement (for a revaluation "
             "line, the value delta).")

    # --- Outgoing -----------------------------------------------------------
    out_qty = fields.Float(
        string='Out Qty', aggregator='sum',
        help="Outgoing quantity of this movement (valued quantity).")
    out_unit_cost = fields.Float(
        string='Out Unit Cost', aggregator=False,
        help="Unit cost applied to the outgoing movement (re-derived from the running "
             "cost). Never summed.")
    out_value = fields.Monetary(
        string='Out Value', currency_field='currency_id', aggregator='sum',
        help="Outgoing value removed from the balance by this movement (COGS).")

    # --- Closing (single cell per product) ----------------------------------
    fin_qty = fields.Float(
        string='Closing Qty', aggregator='sum',
        help="Quantity on hand at the end of the period (shown once per product).")
    fin_unit_cost = fields.Float(
        string='Closing Unit Cost', aggregator=False,
        help="Unit cost at the end of the period. Never summed.")
    fin_value = fields.Monetary(
        string='Closing Value', currency_field='currency_id', aggregator='sum',
        help="Inventory value at the end of the period. It equals the stock valuation "
             "(total_value) at the 'To' date.")

    # --- Running balance (per row; never aggregated) ------------------------
    bal_qty = fields.Float(
        string='Balance Qty', aggregator=False,
        help="Running quantity on hand after this line. A per-row figure; never summed.")
    bal_unit_cost = fields.Float(
        string='Balance Unit Cost', aggregator=False,
        help="Running unit cost after this line. A per-row figure; never summed.")
    bal_value = fields.Monetary(
        string='Balance Value', currency_field='currency_id', aggregator=False,
        help="Running inventory value after this line. A per-row figure; never summed.")

    # --- Reconciliation vs a naive sum(move.value) ledger (D17/§10) ---------
    ple_bal_value = fields.Monetary(
        string='PLE Balance Value', currency_field='currency_id', aggregator=False,
        help="Running balance a naive sum(move.value) ledger (the SUNAT PLE) would show. "
             "It does NOT reconcile with the GL when the product has price/value revaluations.")
    recon_delta = fields.Monetary(
        string='Reconciliation Delta', currency_field='currency_id', aggregator=False,
        help="bal_value (correct, reconciles with the GL) minus ple_bal_value "
             "(sum(move.value) style). Non-zero means the official PLE diverges from the "
             "General Ledger for this product.")
