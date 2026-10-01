from odoo import Command, api, fields, models
from odoo.exceptions import UserError


class ProductoCafeteria(models.Model):
    _inherit = "product.template"

    # Todos los productos de la cafetería llevan control de inventario
    # (el campo "Track Inventory" se ocultó del formulario)
    is_storable = fields.Boolean(default=True)

    # Impuestos por defecto al crear un producto: IVA 13% en ventas y compras vacío
    taxes_id = fields.Many2many(default=lambda self: self._default_impuesto_ventas())
    supplier_taxes_id = fields.Many2many(default=lambda self: [])

    stock_minimo = fields.Float(
        string="Stock mínimo",
        default=0,
    )

    stock_bajo = fields.Boolean(
        string="Stock bajo",
        compute="_compute_stock_bajo",
    )

    # Stock de los productos combo y servicio, que se escribe a mano en la tarjeta del producto
    # (en goods se usa la cantidad real de inventario, qty_available)
    stock_actual = fields.Float(string="Stock actual", default=0.0)

    # Estado del stock, usado como alerta en el inventario
    estado_stock = fields.Selection(
        selection=[
            ("disponible", "Disponible"),
            ("bajo", "⚠️ Stock bajo"),
            ("agotado", "⛔ Agotado"),
        ],
        string="Estado del stock",
        compute="_compute_estado_stock",
        search="_search_estado_stock",
    )

    def _default_impuesto_ventas(self):
        impuesto = self.env.ref("modulo_cafeteria.impuesto_ventas_13", raise_if_not_found=False)
        return [Command.set(impuesto.ids)] if impuesto else []

    @api.depends("stock_minimo", "qty_available")
    def _compute_stock_bajo(self):
        for producto in self:
            producto.stock_bajo = (
                producto.stock_minimo > 0
                and producto.qty_available <= producto.stock_minimo
            )

    # Combo y servicio no tienen movimientos de inventario: su "On Hand" (qty_available) muestra
    # el stock escrito a mano, para que se vea igual en el kanban, la lista y los botones
    @api.depends("type", "stock_actual")
    def _compute_quantities(self):
        super()._compute_quantities()
        for producto in self.filtered(lambda p: p.type != "consu"):
            producto.with_context(skip_qty_available_update=True).qty_available = producto.stock_actual

    @api.depends("type", "stock_minimo", "stock_actual", "qty_available")
    def _compute_estado_stock(self):
        # agotado: sin existencias; bajo: por debajo o igual al mínimo; si no, disponible
        for producto in self:
            # goods: inventario real; combo y servicio: el stock escrito a mano
            stock = producto.qty_available if producto.type == "consu" else producto.stock_actual
            if stock <= 0:
                producto.estado_stock = "agotado"
            elif producto.stock_minimo > 0 and stock <= producto.stock_minimo:
                producto.estado_stock = "bajo"
            else:
                producto.estado_stock = "disponible"

    def _search_estado_stock(self, operator, value):
        # El stock no se guarda en la tabla, así que se calcula producto por producto
        if operator not in ("=", "in"):
            raise UserError("Solo se puede filtrar por un estado de stock.")
        estados = value if operator == "in" else [value]
        productos = self.search([]).filtered(
            lambda p: p.estado_stock in estados
        )
        return [("id", "in", productos.ids)]
