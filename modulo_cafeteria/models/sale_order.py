import math

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

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
                lambda l: l.product_id.is_storable and not l.display_type
            ):
                producto = line.product_id
                pedido[producto] = pedido.get(producto, 0.0) + line.product_uom_id._compute_quantity(
                    line.product_uom_qty, producto.uom_id
                )
            for producto, cantidad in pedido.items():
                if cantidad > producto.qty_available:
                    raise ValidationError(
                        _("Stock insuficiente de '%(producto)s': disponible %(stock)g, solicitado %(cantidad)g.")
                        % {
                            "producto": producto.display_name,
                            "stock": producto.qty_available,
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

    def action_confirm(self):
        result = super().action_confirm()

        pickings = self.env["stock.picking"].search(
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
        self.partner_id.actualizar_categoria_por_compras()

        return result
