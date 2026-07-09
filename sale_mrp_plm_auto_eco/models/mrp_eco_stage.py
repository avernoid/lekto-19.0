from odoo import fields, models


class MrpEcoStage(models.Model):
    """Extensión de mrp.eco.stage para marcar qué etapa, al ser alcanzada por
    un ECO, dispara la creación automática de la Orden de Manufactura.

    Actúa en conjunto con mrp.eco.type.auto_create_mo: ambos deben estar
    activos para que el cambio de etapa genere la MO."""

    _inherit = 'mrp.eco.stage'

    triggers_mo_creation = fields.Boolean(
        string="Generate Manufacturing Order",
        default=False,
        help="Auto-creation requires BOTH switches: this one on the stage AND "
             "'Auto-create Manufacturing Order' on the ECO Type. When an ECO "
             "whose Type has that option enabled enters this stage (e.g. when "
             "'Apply Changes' moves it to the final stage), a Manufacturing "
             "Order is automatically created to supply the originating sale "
             "order. If only this stage flag is set but the ECO Type's is not, "
             "nothing is generated automatically — use the manual button on the "
             "ECO instead. Typically set on your final/approval stage.",
    )
