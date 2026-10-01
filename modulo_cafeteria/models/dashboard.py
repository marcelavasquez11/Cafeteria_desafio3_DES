from datetime import datetime, time, timedelta

import pytz

from odoo import api, models

from .cliente import ESTADOS_COMPRA

# Cantidad de productos que se muestran en el top de más vendidos
CANTIDAD_TOP = 5
DIAS_SEMANA = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


class CafeteriaDashboard(models.AbstractModel):
    # Modelo sin tabla: solo reúne los datos que muestra la pantalla de inicio
    _name = "cafeteria.dashboard"
    _description = "Dashboard de la cafetería"

    def _a_utc(self, tz, dia):
        # Medianoche (hora local del usuario) de un día, convertida a UTC para consultar la base
        local = tz.localize(datetime.combine(dia, time.min))
        return local.astimezone(pytz.utc).replace(tzinfo=None)

    def _resumen_ventas(self, desde, hasta):
        # Ventas confirmadas entre dos fechas (UTC), con su total en $ y su cantidad
        ventas = self.env["sale.order"].search(
            [
                ("state", "in", ESTADOS_COMPRA),
                ("date_order", ">=", desde),
                ("date_order", "<", hasta),
            ]
        )
        return ventas, {"monto": sum(ventas.mapped("amount_total")), "cantidad": len(ventas)}

    @api.model
    def obtener_datos(self):
        tz = pytz.timezone(self.env.user.tz or "UTC")
        hoy = datetime.now(tz).date()

        # Venta del día
        _, ventas_hoy = self._resumen_ventas(
            self._a_utc(tz, hoy), self._a_utc(tz, hoy + timedelta(days=1))
        )

        # Ventas del mes actual
        inicio_mes = hoy.replace(day=1)
        siguiente_mes = (inicio_mes + timedelta(days=32)).replace(day=1)
        _, ventas_mes = self._resumen_ventas(
            self._a_utc(tz, inicio_mes), self._a_utc(tz, siguiente_mes)
        )

        # Ventas de cada día de la semana actual (lunes a domingo)
        inicio_semana = hoy - timedelta(days=hoy.weekday())
        ventas_semana, _ = self._resumen_ventas(
            self._a_utc(tz, inicio_semana), self._a_utc(tz, inicio_semana + timedelta(days=7))
        )
        monto_por_dia = [0.0] * 7
        for venta in ventas_semana:
            dia = pytz.utc.localize(venta.date_order).astimezone(tz).date()
            monto_por_dia[(dia - inicio_semana).days] += venta.amount_total

        # Top de productos más vendidos del mes (por unidades)
        top = self.env["sale.order.line"]._read_group(
            [
                ("order_id.state", "in", ESTADOS_COMPRA),
                ("order_id.date_order", ">=", self._a_utc(tz, inicio_mes)),
                ("order_id.date_order", "<", self._a_utc(tz, siguiente_mes)),
                ("display_type", "=", False),
            ],
            ["product_id"],
            ["product_uom_qty:sum"],
            order="product_uom_qty:sum desc",
            limit=CANTIDAD_TOP,
        )

        # Productos que se venden y llevan control de inventario
        productos = self.env["product.template"].search(
            [("sale_ok", "=", True), ("is_storable", "=", True)]
        )
        con_stock = productos.filtered(lambda p: p.qty_available > 0)
        agotados = productos.filtered(lambda p: p.qty_available <= 0)
        stock_minimo = productos.filtered(
            lambda p: p.stock_minimo > 0 and 0 < p.qty_available <= p.stock_minimo
        ).sorted("qty_available")

        return {
            "currency_id": self.env.company.currency_id.id,
            "total_productos": len(productos),
            "productos_en_stock": len(con_stock),
            "ventas_hoy": ventas_hoy,
            "ventas_mes": ventas_mes,
            "ventas_semana": {"dias": DIAS_SEMANA, "montos": monto_por_dia},
            "top_productos": [
                {
                    "id": producto.product_tmpl_id.id,
                    # Nombre primero y luego el código: "Croissant [CAF-001]"
                    "nombre": "%s [%s]" % (producto.name, producto.default_code)
                    if producto.default_code
                    else producto.name,
                    "cantidad": cantidad,
                }
                for producto, cantidad in top
            ],
            "alertas": {
                "minimo": [
                    {"id": p.id, "nombre": p.name, "stock": p.qty_available, "minimo": p.stock_minimo}
                    for p in stock_minimo
                ],
                "agotados": [
                    {"id": p.id, "nombre": p.name, "stock": p.qty_available, "minimo": p.stock_minimo}
                    for p in agotados.sorted("name")
                ],
            },
        }
