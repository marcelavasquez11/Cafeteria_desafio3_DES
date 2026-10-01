from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ComboItemCafeteria(models.Model):
    _inherit = "product.combo.item"

    # Descuento en % que recibe este producto dentro del combo
    descuento = fields.Float(string="Descuento (%)", default=0.0)

    # Precio del producto dentro del combo, ya con el descuento (solo informativo)
    precio_final = fields.Float(
        string="Precio con descuento",
        compute="_compute_precio_final",
    )

    # El "Extra Price" de Odoo no se usa: el combo cobra la suma de todos sus productos
    # (ya con descuento), que se guarda en el precio de venta del producto combo
    extra_price = fields.Float(
        compute="_compute_extra_price",
        store=True,
        readonly=True,
    )

    @api.depends("descuento")
    def _compute_extra_price(self):
        for item in self:
            item.extra_price = 0.0

    @api.depends("lst_price", "descuento")
    def _compute_precio_final(self):
        for item in self:
            item.precio_final = item.lst_price * (1 - item.descuento / 100)

    @api.constrains("descuento")
    def _check_descuento(self):
        # El descuento debe estar entre 0% y 100%
        for item in self:
            if not 0 <= item.descuento <= 100:
                raise ValidationError("El descuento debe estar entre 0 y 100%.")

    # Al cambiar las opciones de un combo se recalculan los precios de los productos combo
    def _sincronizar_productos_combo(self):
        combos = self.combo_id
        productos = self.env["product.template"].search([("combo_ids", "in", combos.ids)])
        productos._sincronizar_precios_combo()

    @api.model_create_multi
    def create(self, vals_list):
        items = super().create(vals_list)
        items._sincronizar_productos_combo()
        return items

    def write(self, vals):
        resultado = super().write(vals)
        self._sincronizar_productos_combo()
        return resultado

    def unlink(self):
        combos = self.combo_id
        resultado = super().unlink()
        productos = self.env["product.template"].search([("combo_ids", "in", combos.ids)])
        productos._sincronizar_precios_combo()
        return resultado


class ComboEleccionCafeteria(models.Model):
    _inherit = "product.combo"

    # Se permite repetir un producto dentro de una misma elección (se anula la regla de Odoo)
    @api.constrains("combo_item_ids")
    def _check_combo_item_ids_no_duplicates(self):
        return

    # Botón "Eliminar" de la lista de combos. No devuelve ninguna acción a propósito:
    # así Odoo recarga la lista donde se hizo clic (también dentro de la ventana de selección)
    def action_eliminar_combo(self):
        self.unlink()

    # Al borrar una elección guardada se recalculan los productos combo que la usaban
    def unlink(self):
        productos = self.env["product.template"].search([("combo_ids", "in", self.ids)])
        resultado = super().unlink()
        productos._sincronizar_precios_combo()
        return resultado


class ProductoComboCafeteria(models.Model):
    _inherit = "product.template"

    def _calcular_precios_combo(self):
        # Se suman TODOS los productos que tiene el combo:
        # - precio de venta: suma de los precios ya con el descuento de cada producto
        # - costo: suma del costo real (standard_price) de cada producto, sin descuento
        items = self.combo_ids.combo_item_ids
        precio = sum(items.mapped("precio_final"))
        # (se recorre item por item para contar los productos repetidos cada vez)
        costo = sum(item.product_id.standard_price for item in items)
        return precio, costo

    def _sincronizar_precios_combo(self):
        # Solo para productos de tipo combo; el resto de productos no se toca
        for producto in self.filtered(lambda p: p.type == "combo"):
            precio, costo = producto._calcular_precios_combo()
            producto.with_context(sincronizando_combo=True).write(
                {"list_price": precio, "standard_price": costo}
            )

    @api.onchange("type", "combo_ids")
    def _onchange_precios_combo(self):
        # Vista previa en el formulario mientras se arma el combo
        for producto in self.filtered(lambda p: p.type == "combo"):
            producto.list_price, producto.standard_price = producto._calcular_precios_combo()

    @api.model_create_multi
    def create(self, vals_list):
        productos = super().create(vals_list)
        productos._sincronizar_precios_combo()
        return productos

    def write(self, vals):
        resultado = super().write(vals)
        if not self.env.context.get("sincronizando_combo") and ("type" in vals or "combo_ids" in vals):
            self._sincronizar_precios_combo()
        return resultado
