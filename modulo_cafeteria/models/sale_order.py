import math

from odoo import _, api, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

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

        return result