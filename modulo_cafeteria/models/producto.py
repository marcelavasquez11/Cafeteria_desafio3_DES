from odoo import api, fields, models


class ProductoCafeteria(models.Model):
    _inherit = "product.template"

    stock_minimo = fields.Float(
        string="Stock mínimo",
        default=0,
    )

    stock_bajo = fields.Boolean(
        string="Stock bajo",
        compute="_compute_stock_bajo",
    )

    @api.depends("stock_minimo", "qty_available")
    def _compute_stock_bajo(self):
        for producto in self:
            producto.stock_bajo = (
                producto.stock_minimo > 0
                and producto.qty_available <= producto.stock_minimo
            )