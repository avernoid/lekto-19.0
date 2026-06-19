from odoo import fields, models


class ProductCategory(models.Model):
    """Extensión de product.category para marcar categorías que requieren
    ingeniería a medida. Los productos de estas categorías dispararán la
    creación automática de un ECO de PLM al confirmar una orden de venta."""

    _inherit = 'product.category'

    requires_engineering = fields.Boolean(
        string="Requires custom engineering",
        default=False,
        help="When enabled, confirming a sale order that contains a storable "
             "product of this category without an active Bill of Materials "
             "automatically creates a PLM Engineering Change Order (ECO) and a "
             "draft BOM for that product. Leave it off for standard products "
             "that do not need an engineering design step.",
    )
    eco_type_id = fields.Many2one(
        comodel_name='mrp.eco.type',
        string="ECO Type",
        help="Engineering Change Order type assigned to the ECOs created "
             "automatically for products of this category. It determines the "
             "engineering stages the ECO goes through; the first stage by "
             "sequence is selected on creation. This is required once "
             "'Requires custom engineering' is enabled — without it no ECO can "
             "be created.",
    )
