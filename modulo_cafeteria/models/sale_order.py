from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

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