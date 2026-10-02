import random
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError

# Campos que ya no se pueden cambiar cuando la venta está pagada
CAMPOS_BLOQUEADOS_PAGADA = {
    "order_line",
    "partner_id",
    "date_order",
    "pricelist_id",
    "payment_term_id",
    "note",
    "metodo_pago",
    "efectivo_recibido",
    "tarjeta_marca",
    "tarjeta_ultimos4",
}


class VentaCafeteria(models.Model):
    _inherit = "sale.order"

    # Estado de la venta: pendiente -> pagada, o cancelada (solo estando pendiente)
    estado_venta = fields.Selection(
        selection=[
            ("pendiente", "Pendiente"),
            ("pagada", "Pagada"),
            ("cancelada", "Cancelada"),
        ],
        string="Estado",
        default="pendiente",
        required=True,
        copy=False,
        index=True,
    )

    # Paso de pago, antes de facturar
    metodo_pago = fields.Selection(
        selection=[("efectivo", "Efectivo"), ("tarjeta", "Tarjeta")],
        string="Método de pago",
        copy=False,
    )
    efectivo_recibido = fields.Monetary(
        string="Efectivo recibido", currency_field="currency_id", copy=False
    )
    vuelto = fields.Monetary(
        string="Vuelto", compute="_compute_vuelto", currency_field="currency_id"
    )

    # Simulación del pago con tarjeta (datáfono)
    tarjeta_marca = fields.Selection(
        selection=[("visa", "Visa"), ("mastercard", "Mastercard"), ("amex", "American Express")],
        string="Tarjeta",
        copy=False,
    )
    tarjeta_ultimos4 = fields.Char(string="Últimos 4 dígitos", size=4, copy=False)
    tarjeta_estado = fields.Selection(
        selection=[("aprobada", "✅ Aprobada"), ("rechazada", "❌ Rechazada")],
        string="Resultado",
        copy=False,
        readonly=True,
    )
    tarjeta_autorizacion = fields.Char(string="Código de autorización", copy=False, readonly=True)

    # Subtotal sin descuento, descuento por tipo de cliente y total (el total es amount_total)
    subtotal_cafeteria = fields.Monetary(
        string="Subtotal",
        compute="_compute_totales_cafeteria",
        currency_field="currency_id",
    )
    descuento_cafeteria = fields.Monetary(
        string="Descuento",
        compute="_compute_totales_cafeteria",
        currency_field="currency_id",
    )

    @api.depends("order_line.price_total", "order_line.price_unit", "order_line.product_uom_qty",
                 "order_line.tax_ids", "amount_total")
    def _compute_totales_cafeteria(self):
        for venta in self:
            # Total normal: cada línea calculada sin su descuento (con impuestos, si los hay)
            normal = 0.0
            for linea in venta.order_line.filtered(lambda l: not l.display_type):
                normal += linea.tax_ids.compute_all(
                    linea.price_unit,
                    currency=venta.currency_id,
                    quantity=linea.product_uom_qty,
                    product=linea.product_id,
                    partner=venta.partner_id,
                )["total_included"]
            venta.subtotal_cafeteria = normal
            venta.descuento_cafeteria = normal - venta.amount_total

    @api.depends("metodo_pago", "efectivo_recibido", "amount_total")
    def _compute_vuelto(self):
        # El vuelto solo existe cuando se paga en efectivo y se recibió más del total
        for venta in self:
            recibido = venta.efectivo_recibido if venta.metodo_pago == "efectivo" else 0.0
            venta.vuelto = max(recibido - venta.amount_total, 0.0)

    @api.onchange("metodo_pago")
    def _onchange_metodo_pago(self):
        # Al cambiar de método se borran los datos del otro método
        if self.metodo_pago != "efectivo":
            self.efectivo_recibido = 0.0
        if self.metodo_pago != "tarjeta":
            self.tarjeta_marca = False
            self.tarjeta_ultimos4 = False
            self.tarjeta_estado = False
            self.tarjeta_autorizacion = False

    @api.onchange("tarjeta_marca", "tarjeta_ultimos4")
    def _onchange_tarjeta(self):
        # Si se cambian los datos de la tarjeta, hay que volver a procesar el pago
        self.tarjeta_estado = False
        self.tarjeta_autorizacion = False

    def action_procesar_tarjeta(self):
        # Simula el datáfono: valida la tarjeta y aprueba o rechaza el cobro.
        # Una tarjeta que termina en 0000 se rechaza (para simular un rechazo)
        self.ensure_one()
        if self.estado_venta != "pendiente":
            raise UserError(_("Solo se puede cobrar una venta pendiente."))
        if not self.tarjeta_marca:
            raise UserError(_("Seleccione la marca de la tarjeta."))
        if not re.fullmatch(r"\d{4}", self.tarjeta_ultimos4 or ""):
            raise UserError(_("Escriba los últimos 4 dígitos de la tarjeta."))
        if self.tarjeta_ultimos4 == "0000":
            self.tarjeta_estado = "rechazada"
            self.tarjeta_autorizacion = False
        else:
            self.tarjeta_estado = "aprobada"
            self.tarjeta_autorizacion = "%06d" % random.randint(0, 999999)

    # --- Pagar -------------------------------------------------------------------------------

    def action_facturar(self):
        # Valida el pago, confirma la venta si falta, crea y publica la factura,
        # registra el pago y abre la factura para imprimirla
        self.ensure_one()
        if self.estado_venta != "pendiente":
            raise UserError(_("Solo se puede pagar una venta pendiente."))
        if not self.order_line:
            raise UserError(_("La venta no tiene productos."))
        if not self.metodo_pago:
            raise UserError(_("Seleccione el método de pago antes de facturar."))
        if self.metodo_pago == "tarjeta" and self.tarjeta_estado != "aprobada":
            raise UserError(_("Procese el pago con tarjeta (y que sea aprobado) antes de facturar."))
        if self.metodo_pago == "efectivo" and self.currency_id.compare_amounts(
            self.efectivo_recibido, self.amount_total
        ) < 0:
            raise UserError(
                _("El efectivo recibido es menor al total. Faltan %s.")
                % self.currency_id.format(self.amount_total - self.efectivo_recibido)
            )

        if self.state in ("draft", "sent"):
            self.action_confirm()

        factura = self._create_invoices()
        factura.action_post()

        # Efectivo: diario de efectivo si existe (si no, el de banco). Tarjeta: diario de banco
        diarios = self.env["account.journal"]
        dominio = [("company_id", "=", self.company_id.id)]
        if self.metodo_pago == "efectivo":
            diarios = diarios.search(dominio + [("type", "=", "cash")], limit=1)
        diario = diarios or self.env["account.journal"].search(
            dominio + [("type", "=", "bank")], limit=1
        )
        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=factura.ids
        ).create({"journal_id": diario.id})._create_payments()

        self.with_context(permitir_edicion_pagada=True).estado_venta = "pagada"

        # Se abre la factura en PDF para imprimirla. Odoo 19 devuelve primero un diálogo de
        # "Enviar e imprimir"; se toma de ahí la acción del PDF para abrirlo directo
        accion = self.env.ref("account.account_invoices").report_action(factura)
        return accion.get("context", {}).get("report_action") or accion

    # --- Cancelar ----------------------------------------------------------------------------

    def action_cancelar_venta(self):
        self.ensure_one()
        if self.estado_venta != "pendiente":
            raise UserError(_("Solo se puede cancelar una venta pendiente."))

        # Si ya se entregó, se devuelven las unidades al inventario
        for entrega in self.picking_ids.filtered(
            lambda p: p.state == "done" and p.picking_type_code == "outgoing"
        ):
            asistente = self.env["stock.return.picking"].with_context(
                active_id=entrega.id, active_model="stock.picking"
            ).create({})
            devolucion = self.env["stock.picking"].browse(
                asistente.action_create_returns_all()["res_id"]
            )
            devolucion.with_context(skip_sms=True).button_validate()

        self._action_cancel()

    def _action_cancel(self):
        if any(venta.estado_venta == "pagada" for venta in self):
            raise UserError(_("Una venta pagada no se puede cancelar."))
        # Las ventas ya confirmadas devuelven el stock propio de sus combos
        confirmadas = self.filtered(lambda v: v.state == "sale")
        resultado = super()._action_cancel()
        confirmadas._mover_stock_combos(1)
        self.with_context(permitir_edicion_pagada=True).estado_venta = "cancelada"
        return resultado

    # --- Una venta pagada ya no se modifica ---------------------------------------------------

    def write(self, vals):
        if (
            not self.env.context.get("permitir_edicion_pagada")
            and CAMPOS_BLOQUEADOS_PAGADA & vals.keys()
            and any(venta.estado_venta == "pagada" for venta in self)
        ):
            raise UserError(_("Una venta pagada ya no se puede modificar."))
        return super().write(vals)
