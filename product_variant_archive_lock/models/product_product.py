# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    manually_archived = fields.Boolean(
        string="Manually archived",
        default=False,
        copy=False,
        help="Technical flag: marks that a user archived this variant on "
             "purpose (not because of an invalid combination). Used to avoid "
             "reactivating it when variants are regenerated while the product "
             "has 'Keep manually archived variants' enabled.",
    )

    def action_archive(self):
        # Archivado deliberado desde la interfaz (botón Archivar / acción de
        # lista). La ruta automática de Odoo para combinaciones inválidas usa
        # write({'active': False}) en _unlink_or_archive, NO action_archive,
        # por lo que aquí solo capturamos la intención del usuario.
        res = super().action_archive()
        self.write({'manually_archived': True})
        return res

    def action_unarchive(self):
        # Si el usuario reactiva a mano, deja de estar "archivada manualmente".
        res = super().action_unarchive()
        self.write({'manually_archived': False})
        return res
