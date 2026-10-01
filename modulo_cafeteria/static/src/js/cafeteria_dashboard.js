/** @odoo-module **/

import { Component, onMounted, onWillStart, onWillUnmount, useRef, useState } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { formatCurrency } from "@web/core/currency";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

// Pantalla de inicio de la cafetería: cards, gráfico semanal, top y alertas de stock
class CafeteriaDashboard extends Component {
    static template = "modulo_cafeteria.CafeteriaDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.chartRef = useRef("chart");
        this.chart = null;
        this.state = useState({
            datos: null,
            error: false,
            // Pestaña de alertas visible: "minimo" (stock mínimo) o "agotados"
            tabAlertas: "minimo",
        });

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            await this.cargarDatos();
        });
        onMounted(() => this.dibujarGrafico());
        onWillUnmount(() => this.chart && this.chart.destroy());
    }

    async cargarDatos() {
        try {
            this.state.datos = await this.orm.call("cafeteria.dashboard", "obtener_datos", []);
        } catch (error) {
            console.error("No se pudo cargar el dashboard de la cafetería.", error);
            this.state.error = true;
        }
    }

    dibujarGrafico() {
        if (!this.state.datos || !this.chartRef.el) {
            return;
        }
        const semana = this.state.datos.ventas_semana;
        this.chart = new Chart(this.chartRef.el, {
            type: "line",
            data: {
                labels: semana.dias,
                datasets: [
                    {
                        label: "Ventas",
                        data: semana.montos,
                        borderColor: "#176b52",
                        backgroundColor: "rgba(23, 107, 82, 0.15)",
                        fill: true,
                        tension: 0.3,
                        pointRadius: 4,
                        pointBackgroundColor: "#fff",
                        pointBorderWidth: 2,
                        borderWidth: 3,
                    },
                ],
            },
            options: {
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, grid: { color: "#e3e9e5" } },
                    x: { grid: { display: false } },
                },
            },
        });
    }

    // Abre la ficha del producto en el inventario
    abrirProducto(productoId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Inventario",
            res_model: "product.template",
            res_id: productoId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    // Fecha de hoy en texto, para el encabezado (ej: "jueves, 1 de octubre de 2026")
    get fechaHoy() {
        return new Date().toLocaleDateString(undefined, {
            weekday: "long",
            day: "numeric",
            month: "long",
            year: "numeric",
        });
    }

    // Ancho de la barra de stock de una alerta: stock actual respecto al mínimo
    porcentajeStock(item) {
        return item.minimo ? Math.min(100, Math.round((item.stock / item.minimo) * 100)) : 0;
    }

    formatMoney(monto) {
        return formatCurrency(monto, this.state.datos.currency_id);
    }

    formatNumber(numero) {
        return new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(numero || 0);
    }

    get alertas() {
        return this.state.datos.alertas[this.state.tabAlertas];
    }
}

registry.category("actions").add("modulo_cafeteria.cafeteria_dashboard", CafeteriaDashboard);
