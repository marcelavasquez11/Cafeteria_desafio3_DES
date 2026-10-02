import math

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # Subtotal de la línea con el descuento ya reflejado (es lo que paga el cliente por esa línea)
    subtotal_linea = fields.Monetary(
        string="Subtotal",
        compute="_compute_subtotal_linea",
        currency_field="currency_id",
    )

    def _combo_suelto(self):
        # Un combo "suelto" se vende como un producto normal, con su propio precio y su propio
        # stock (el que se escribe en la tarjeta de stock del combo). No tiene líneas hijas
        # con los productos que lo componen, así que no mueve el inventario de esos productos.
        self.ensure_one()
        return self.product_id.type == "combo" and not self.linked_line_ids

    def _get_display_price(self):
        # Odoo pone siempre en 0 el precio de la línea de un combo (el precio va en sus líneas
        # hijas). Un combo suelto no tiene hijas: se cobra su precio de venta normal.
        self.ensure_one()
        if self._combo_suelto():
            return self._get_display_price_ignore_combo()
        return super()._get_display_price()

    def _prepare_invoice_line(self, **optional_values):
        # Odoo pone la línea de un combo en la factura como un simple título (precio 0), porque
        # el precio va en las líneas de sus productos. Un combo suelto no tiene esas líneas:
        # se factura como una línea normal, con su precio y su descuento.
        self.ensure_one()
        if not self._combo_suelto():
            return super()._prepare_invoice_line(**optional_values)
        valores = {
            "display_type": "product",
            "sequence": self.sequence,
            "name": self.env["account.move.line"]._get_journal_items_full_name(
                self.name, self.product_id.display_name
            ),
            "product_id": self.product_id.id,
            "product_uom_id": self.product_uom_id.id,
            "quantity": self.qty_to_invoice,
            "discount": self.discount,
            "price_unit": self.price_unit,
            "tax_ids": [Command.set(self.tax_ids.ids)],
            "sale_line_ids": [Command.link(self.id)],
        }
        valores.update(optional_values)
        return valores

    @api.depends("qty_invoiced", "qty_delivered", "product_uom_qty", "state")
    def _compute_qty_to_invoice(self):
        # Odoo solo deja facturar un combo si alguna de sus líneas hijas es facturable; un combo
        # suelto se factura por la cantidad vendida, como cualquier producto con política "pedido"
        super()._compute_qty_to_invoice()
        for line in self:
            if line.state == "sale" and not line.display_type and line._combo_suelto():
                line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced

    @api.depends("price_total", "order_id.order_line.price_total")
    def _compute_subtotal_linea(self):
        for line in self:
            if line.product_id.type == "combo":
                # La fila del combo no tiene precio propio (Odoo lo pone en sus productos):
                # se muestra la suma de las líneas de los productos que lo componen
                hijas = line.order_id.order_line.filtered(
                    lambda h: h.combo_item_id
                    and (
                        (h.linked_line_id and h.linked_line_id == line)
                        or (h.linked_virtual_id and h.linked_virtual_id == line.virtual_id)
                    )
                )
                line.subtotal_linea = sum(hijas.mapped("price_total")) if hijas else line.price_total
            else:
                line.subtotal_linea = line.price_total

    # Se vuelve a calcular el descuento cuando cambia el cliente de la venta
    @api.depends("order_id.partner_id")
    def _compute_discount(self):
        super()._compute_discount()
        # Aplica a cada línea el descuento de la categoría del cliente
        # (con sin_descuento_cliente se calcula el total "normal", sin ese descuento)
        if self.env.context.get("sin_descuento_cliente"):
            return
        for line in self:
            descuento = line.order_id.partner_id.descuento_cliente
            if line.product_id and not line.display_type and descuento > line.discount:
                line.discount = descuento


    # No se puede vender más de lo que hay en stock (solo mientras la venta no está confirmada,
    # porque al confirmar el stock ya se descuenta)
    @api.constrains("product_id", "product_uom_id", "product_uom_qty")
    def _check_stock_suficiente(self):
        for orden in self.order_id.filtered(lambda o: o.state in ("draft", "sent")):
            # Se suma la cantidad pedida de cada producto en toda la venta
            pedido = {}
            for line in orden.order_line.filtered(
                # Goods con inventario y combos (que tienen su propio stock); el servicio no
                lambda l: (
                    (l.product_id.type == "consu" and l.product_id.is_storable)
                    or l.product_id.type == "combo"
                )
                and not l.display_type
            ):
                producto = line.product_id
                pedido[producto] = pedido.get(producto, 0.0) + line.product_uom_id._compute_quantity(
                    line.product_uom_qty, producto.uom_id
                )
            for producto, cantidad in pedido.items():
                # Goods: existencias reales. Combo: el stock escrito en su tarjeta de stock
                disponible = (
                    producto.product_tmpl_id.stock_actual
                    if producto.type == "combo"
                    else producto.qty_available
                )
                if cantidad > disponible:
                    raise ValidationError(
                        _("Stock insuficiente de '%(producto)s': disponible %(stock)g, solicitado %(cantidad)g.")
                        % {
                            "producto": producto.display_name,
                            "stock": disponible,
                            "cantidad": cantidad,
                        }
                    )


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # Resumen de productos de la venta, para mostrarlo en el historial del cliente
    productos_resumen = fields.Char(
        string="Productos",
        compute="_compute_productos_resumen",
    )

    @api.depends("order_line.product_id", "order_line.product_uom_qty")
    def _compute_productos_resumen(self):
        for orden in self:
            lineas = orden.order_line.filtered(lambda l: not l.display_type)
            orden.productos_resumen = ", ".join(
                "%s x%g" % (l.product_id.name, l.product_uom_qty) for l in lineas
            )

    @api.model
    def _prepare_pos_order_data(self, partner_id, lines, require_partner=True):
        partner = (
            self.env["res.partner"].browse(partner_id).exists()
            if partner_id
            else self.env["res.partner"]
        )
        if partner_id and not partner:
            raise UserError(_("Seleccione un cliente válido."))
        if require_partner and not partner:
            raise UserError(_("Seleccione un cliente válido."))
        if not lines:
            raise UserError(_("El carrito está vacío."))

        order_lines = []
        for line in lines:
            try:
                product_id = int(line["product_id"])
                quantity = float(line["quantity"])
            except (KeyError, TypeError, ValueError):
                raise UserError(_("Hay una línea de producto inválida.")) from None

            if not math.isfinite(quantity) or quantity <= 0:
                raise UserError(_("Las cantidades deben ser mayores que cero."))

            product = self.env["product.product"].browse(product_id).exists()
            if not product or not product.active or not product.sale_ok:
                raise UserError(_("Uno de los productos ya no está disponible para la venta."))

            order_lines.append(
                (
                    0,
                    0,
                    {
                        "product_id": product.id,
                        "product_uom_qty": quantity,
                        "product_uom_id": product.uom_id.id,
                        "price_unit": product.product_tmpl_id.list_price,
                    },
                )
            )

        return partner, order_lines

    @api.model
    def get_pos_totals(self, partner_id, lines):
        partner, order_lines = self._prepare_pos_order_data(
            partner_id, lines, require_partner=False
        )
        order = self.new(
            {
                "partner_id": partner.id or False,
                "order_line": order_lines,
            }
        )
        order._compute_amounts()

        # Total normal: el mismo carrito calculado sin el descuento por tipo de cliente
        orden_normal = self.with_context(sin_descuento_cliente=True).new(
            {
                "partner_id": partner.id or False,
                "order_line": order_lines,
            }
        )
        orden_normal._compute_amounts()
        tax_totals = order.tax_totals or {}
        tax_lines = [
            {
                "name": tax_group.get("group_name")
                or tax_group.get("group_label")
                or _("Impuestos"),
                "amount": tax_group["tax_amount_currency"],
            }
            for subtotal in tax_totals.get("subtotals", [])
            for tax_group in subtotal.get("tax_groups", [])
        ]

        return {
            "amount_untaxed": order.amount_untaxed,
            "amount_tax": order.amount_tax,
            "amount_total": order.amount_total,
            "amount_total_normal": orden_normal.amount_total,
            "descuento_monto": orden_normal.amount_total - order.amount_total,
            "descuento_porcentaje": partner.descuento_cliente,
            "categoria_cliente": dict(partner._fields["categoria_cliente"].selection).get(
                partner.categoria_cliente, ""
            )
            if partner
            else "",
            "tax_lines": tax_lines,
        }

    @api.model
    def create_and_confirm_pos_order(self, partner_id, lines):
        partner, order_lines = self._prepare_pos_order_data(partner_id, lines)
        order = self.create(
            {
                "partner_id": partner.id,
                "order_line": order_lines,
            }
        )
        order.action_confirm()

        return {
            "id": order.id,
            "name": order.name,
            "amount_total": order.amount_total,
        }

    def _mover_stock_combos(self, signo):
        # Los combos sueltos llevan su propio stock (stock_actual): se descuenta al confirmar la
        # venta (signo=-1) y se devuelve al cancelarla (signo=1). Nunca baja de 0.
        for linea in self.order_line:
            if linea.display_type or not linea._combo_suelto():
                continue
            # sudo(): el cajero no edita productos, pero el sistema sí actualiza este stock
            producto = linea.product_id.product_tmpl_id.sudo()
            producto.stock_actual = max(producto.stock_actual + signo * linea.product_uom_qty, 0)

    def action_confirm(self):
        # Solo las ventas que se confirman ahora (las que aún no estaban confirmadas)
        por_confirmar = self.filtered(lambda v: v.state in ("draft", "sent"))
        result = super().action_confirm()
        por_confirmar._mover_stock_combos(-1)

        # sudo(): el cajero no tiene permisos de inventario, pero la entrega debe validarse
        pickings = self.env["stock.picking"].sudo().search(
            [
                ("move_ids.sale_line_id.order_id", "in", self.ids),
                ("state", "not in", ("done", "cancel")),
            ]
        )

        for picking in pickings:
            picking.action_assign()

            if picking.state == "assigned":
                picking.button_validate()

        # Al confirmar, el cliente puede subir de regular a frecuente
        # sudo(): el cajero no edita clientes, pero el sistema sí puede subirlos de categoría
        self.partner_id.sudo().actualizar_categoria_por_compras()

        return result
