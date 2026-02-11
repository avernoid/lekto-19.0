from odoo import api, models, fields, _

   
class StockPicking(models.Model):
    _inherit = 'stock.picking'    
    
    transfer_document_type_id = fields.Many2one(
        comodel_name='l10n_latam.document.type',
        string='Transfer Doc Type',
        help='This document type is used for PLE 13.1 validation. If left blank, Odoo will attempt to fill it from the Remission Guide, Purchase/Sales Order, or default to 00.'
    )
    serie_transfer_document = fields.Char(
        string='Transfer Doc Series',
        help='This series is used for PLE 13.1 validation. If left blank, Odoo will attempt to fill it from the Remission Guide, Purchase/Sales Order, or default to 00.',
        compute='_compute_transfer_data_picking',
        inverse='_set_transfer_data_picking',
        store=True,
    )
    number_transfer_document = fields.Char(
        string='Transfer Doc Number',
        help='This number is used for PLE 13.1 validation. If left blank, Odoo will attempt to fill it from the Remission Guide, Purchase/Sales Order, or default to 00.',
        compute='_compute_transfer_data_picking',
        inverse='_set_transfer_data_picking',
        store=True,
    )
    
    def _set_transfer_data_picking(self):
        pass

    @api.depends('purchase_id.invoice_ids.ref', 'sale_id.invoice_ids.name')
    def _compute_transfer_data_picking(self):
        for picking in self:
            serie_transfer_document = None
            number_transfer_document = None
            transfer_document_type_id = None
            invoice = []
            flag = 1
            if picking.purchase_id:
                invoice = picking.purchase_id.invoice_ids
            elif picking.sale_id:
                flag = 2
                invoice = picking.sale_id.invoice_ids

            for rec in invoice:
                if flag == 1:
                    doc_source = False
                    # Priority 1: l10n_latam_document_number
                    if rec.l10n_latam_document_number and '-' in rec.l10n_latam_document_number:
                        doc_source = rec.l10n_latam_document_number
                    # Priority 2: ref
                    elif rec.ref and '-' in rec.ref:
                        doc_source = rec.ref
                    # Priority 3: name
                    elif rec.name and '-' in rec.name:
                        doc_source = rec.name

                    if doc_source:
                        data = doc_source.split('-')
                        serie_transfer_document = data[0]
                        number_transfer_document = data[1]
                        transfer_document_type_id = rec.l10n_latam_document_type_id

                if rec.name and '-' in rec.name and flag == 2:
                    data = rec.name.split('-')
                    serie_transfer_document = data[0]
                    number_transfer_document = data[1]
                    transfer_document_type_id = rec.l10n_latam_document_type_id
            picking.serie_transfer_document = serie_transfer_document
            picking.number_transfer_document = number_transfer_document
            picking.transfer_document_type_id = transfer_document_type_id

    def massive_serie_number_type(self):
        for i in self:
            if i.serie_transfer_document == '' or not i.serie_transfer_document or i.number_transfer_document == '' or not i.number_transfer_document or i.transfer_document_type_id == '' or not i.transfer_document_type_id:
                i._compute_transfer_data_picking()
            else:
                pass

