from odoo import models, fields, api
from lxml import etree

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _l10n_pe_edi_get_qr(self):
        """ Retrieve the CDR's QR code. """
        try:
            self.ensure_one()
            result = super()._l10n_pe_edi_get_qr()
            if not result:
                return ''
                
            edi_filename = 'cdr-%s-09-%s.xml' % (
                self.company_id.vat,
                (self.l10n_latam_document_number or '').replace(' ', ''),
            )
            attachment = self.env['ir.attachment'].search([
                ('name', '=', edi_filename),
                ('res_id', '=', self.id),
                ('res_model', '=', self._name)], limit=1)
                
            if not attachment:
                return ''
                
            edi_attachment_str = attachment.raw
            edi_tree = etree.fromstring(edi_attachment_str)
            element = edi_tree.xpath('//cbc:DocumentDescription',
                                    namespaces={'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'})
                                    
            if not element:
                return ''
                
            return element[0].text
        except ValueError:
            return ''


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def _get_aggregated_product_weights(self, **kwargs):
        """ Returns a dictionary of products add weight (key = id+name+description+uom+weight) and corresponding values of interest."""
        aggregated_lines = {}
        # Loop to get the aggregated product quantities
        for move_line in self:
            # Safeguard quantity first
            line_qty = move_line.quantity or 0.0
            
            if kwargs.get('strict') and move_line.product_uom_id != move_line.product_id.uom_id:
                # Optimized version of the standard implementation to avoid ORM overhead
                # when the UoM are different.
                qty = move_line.product_uom_id._compute_quantity(line_qty, move_line.product_id.uom_id)
            else:
                qty = line_qty

            # Safeguard against None values (redundant but safe)
            qty = qty or 0.0
            weight = move_line.product_id.weight or 0.0

            # Define the key for aggregation
            # We use a tuple as key to be able to retrieve the product easily
            key = (
                move_line.product_id.id,
                move_line.product_id.display_name,
                move_line.description_picking,
                move_line.product_uom_id.id,
            )

            # Aggregate the values
            if key not in aggregated_lines:
                aggregated_lines[key] = {
                    'name': move_line.product_id.display_name,
                    'description': move_line.description_picking,
                    'quantity': qty,
                    'product_uom': move_line.product_uom_id,
                    'product': move_line.product_id,
                    'weight': weight,
                }
            else:
                aggregated_lines[key]['quantity'] += qty
                # We don't sum the weight, it is the unit weight of the product

        return aggregated_lines

class StockLocation(models.Model):
    _inherit = 'stock.location'

    direction_id = fields.Many2one(
        comodel_name='res.partner',
        string='Address',
        help="Address associated with the warehouse location, used for delivery guide origin/destination.",
        compute='_default_direction_id',
        inverse='_inverse_direction_id',
        default=False,
        store=True
    )

    @api.depends('warehouse_id.partner_id', 'active')
    def _default_direction_id(self):
        for record in self:
            if record.active and record.warehouse_id and record.warehouse_id.partner_id:
                record.direction_id = record.warehouse_id.partner_id
            else:
                record.direction_id = False

    def _inverse_direction_id(self):
        return