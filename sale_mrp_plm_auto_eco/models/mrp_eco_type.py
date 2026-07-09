from odoo import fields, models


class MrpEcoType(models.Model):
    """Extensión de mrp.eco.type para gobernar 'en qué casos' la aprobación
    de un ECO genera automáticamente una Orden de Manufactura.

    La decisión vive en el Tipo de ECO porque el disparador (cambio de etapa)
    ocurre cuando el ECO ya existe, y su type_id se asigna desde la categoría
    del producto al crearlo (ver sale_order._create_plm_ecos_for_custom_products)."""

    _inherit = 'mrp.eco.type'

    auto_create_mo = fields.Boolean(
        string="Auto-create Manufacturing Order",
        default=False,
        help="Auto-creation requires BOTH switches: this one on the ECO Type "
             "AND 'Generate Manufacturing Order' on the target stage. When "
             "enabled, an ECO of this type automatically creates a "
             "Manufacturing Order for its originating sale order once it "
             "reaches a stage flagged with 'Generate Manufacturing Order'. "
             "The manual button on the ECO works regardless of this setting.",
    )
