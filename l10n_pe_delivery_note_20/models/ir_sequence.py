from odoo import api, fields, models


class IrSequence(models.Model):
    _inherit = 'ir.sequence'


    @api.depends('prefix', 'name')
    def _compute_display_name(self):
        for sequence in self:
            # Para el contexto específico de sunat_sequence_id, mostrar prefix
            if (self.env.context.get('sunat_sequence_context') and 
                sequence.code == 'l10n_pe_edi_stock.stock_picking_sunat_sequence' and 
                sequence.prefix):
                sequence.display_name = sequence.prefix
            else:
                # Comportamiento por defecto para otros casos
                super(IrSequence, sequence)._compute_display_name()

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        # Para búsquedas en el contexto de sunat_sequence_id, buscar por prefix
        if (self.env.context.get('sunat_sequence_context') and 
            domain and any('l10n_pe_edi_stock.stock_picking_sunat_sequence' in str(d) for d in domain if isinstance(d, (list, tuple)))):
            domain = domain or []
            if name:
                # Buscar por prefix en lugar de name
                prefix_domain = [('prefix', operator, name)]
                domain = prefix_domain + [d for d in domain if d != ('name', operator, name)]
            return self._search(domain, limit=limit, order=order)
        return super()._name_search(name, domain, operator, limit, order)

    

