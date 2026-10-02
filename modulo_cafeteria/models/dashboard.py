from datetime import datetime, time, timedelta

import pytz

from odoo import api, models

from .cliente import ESTADOS_COMPRA

# Cantidad de productos que se muestran en el top de más vendidos
CANTIDAD_TOP = 5
DIAS_SEMANA = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

# Rangos que se pueden elegir en el gráfico de ventas: 1 = la semana actual (un punto por día),
# 4, 8 o 12 = esa cantidad de semanas hasta hoy (un punto por semana)
OPCIONES_SEMANAS = (1, 4, 8, 12)


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
    def ventas_grafico(self, semanas=1):
        # Datos del gráfico de ventas.
        # semanas=1: ventas de cada día de la semana actual (lunes a domingo).
        # semanas=4, 8 o 12: total vendido en cada una de las últimas N semanas (incluye la actual).
        if semanas not in OPCIONES_SEMANAS:
            semanas = 1
        tz = pytz.timezone(self.env.user.tz or "UTC")
        hoy = datetime.now(tz).date()

        # La semana actual empieza el lunes y termina el domingo
        inicio_semana_actual = hoy - timedelta(days=hoy.weekday())
        fin = inicio_semana_actual + timedelta(days=7)

        if semanas == 1:
            inicio = inicio_semana_actual
            etiquetas = DIAS_SEMANA
            dias_por_punto = 1
        else:
            # Se retrocede N-1 semanas desde la actual; cada punto es una semana, rotulada con
            # la fecha de su lunes (ej. "29 sep")
            inicio = inicio_semana_actual - timedelta(weeks=semanas - 1)
            lunes = [inicio + timedelta(weeks=i) for i in range(semanas)]
            etiquetas = ["%d %s" % (dia.day, MESES[dia.month - 1]) for dia in lunes]
            dias_por_punto = 7

        ventas, _ = self._resumen_ventas(self._a_utc(tz, inicio), self._a_utc(tz, fin))

        # Cada venta se suma al punto que le corresponde según su fecha local
        montos = [0.0] * len(etiquetas)
        for venta in ventas:
            dia = pytz.utc.localize(venta.date_order).astimezone(tz).date()
            montos[(dia - inicio).days // dias_por_punto] += venta.amount_total
        return {"etiquetas": etiquetas, "montos": montos}

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
            "ventas_semana": self.ventas_grafico(1),
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
