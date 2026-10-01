/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { formatCurrency } from "@web/core/currency";
import { useService } from "@web/core/utils/hooks";
import { Many2One } from "@web/views/fields/many2one/many2one";

class CafeteriaPos extends Component {
    static template = "modulo_cafeteria.CafeteriaPos";
    static components = { Many2One };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.totalsRequestId = 0;
        this.state = useState({
            products: [],
            cart: [],
            totals: {
                amount_untaxed: 0,
                amount_tax: 0,
                amount_total: 0,
                amount_total_normal: 0,
                descuento_monto: 0,
                descuento_porcentaje: 0,
                categoria_cliente: "",
                tax_lines: [],
            },
            totalsLoading: false,
            totalsError: "",
            selectedPartner: null,
            checkoutLoading: false,
            checkoutError: "",
            checkoutSuccess: "",
            loading: true,
            error: false,
        });

        onWillStart(() => this.loadProducts());
    }

    async loadProducts() {
        try {
            this.state.products = await this.orm.searchRead(
                "product.template",
                [
                    ["active", "=", true],
                    ["sale_ok", "=", true],
                ],
                [
                    "name",
                    "list_price",
                    "qty_available",
                    "stock_bajo",
                    "image_512",
                    "currency_id",
                    "product_variant_id",
                ],
                { order: "name asc" }
            );
        } catch (error) {
            console.error("No se pudieron cargar los productos de la cafetería.", error);
            this.state.error = true;
        } finally {
            this.state.loading = false;
        }
    }

    get currencyId() {
        const product = this.state.products.find((item) => item.currency_id);
        return product ? product.currency_id[0] : false;
    }

    get itemCount() {
        return this.state.cart.reduce((sum, line) => sum + line.quantity, 0);
    }

    formatMoney(amount) {
        return this.currencyId
            ? formatCurrency(amount, this.currencyId)
            : new Intl.NumberFormat(undefined, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
              }).format(amount);
    }

    formatStock(quantity) {
        return new Intl.NumberFormat(undefined, {
            maximumFractionDigits: 2,
        }).format(quantity || 0);
    }

    addProduct(product) {
        const line = this.state.cart.find((item) => item.product.id === product.id);
        if (line) {
            this.changeQuantity(product.id, 1);
            return;
        }
        this.state.cart.push({ product, quantity: 1, stockWarning: false });
        this.refreshTotals();
    }

    changeQuantity(productId, amount) {
        const line = this.state.cart.find((item) => item.product.id === productId);
        if (!line) {
            return;
        }
        if (line.quantity + amount <= 0) {
            this.removeProduct(productId);
            return;
        }
        // No se permite superar el stock disponible: se muestra "Stock insuficiente"
        if (line.quantity + amount > line.product.qty_available) {
            line.stockWarning = true;
            return;
        }
        line.stockWarning = false;
        line.quantity += amount;
        this.refreshTotals();
    }

    removeProduct(productId) {
        this.state.cart = this.state.cart.filter(
            (line) => line.product.id !== productId
        );
        this.refreshTotals();
    }

    clearCart() {
        this.state.cart = [];
        this.refreshTotals();
    }

    async refreshTotals() {
        const requestId = ++this.totalsRequestId;
        const lines = this.state.cart.map((line) => ({
            product_id: line.product.product_variant_id[0],
            quantity: line.quantity,
        }));

        if (!lines.length) {
            this.state.totals = {
                amount_untaxed: 0,
                amount_tax: 0,
                amount_total: 0,
                amount_total_normal: 0,
                descuento_monto: 0,
                descuento_porcentaje: 0,
                categoria_cliente: "",
                tax_lines: [],
            };
            this.state.totalsLoading = false;
            this.state.totalsError = "";
            return;
        }

        this.state.totalsLoading = true;
        this.state.totalsError = "";
        try {
            const totals = await this.orm.call("sale.order", "get_pos_totals", [
                this.state.selectedPartner ? this.state.selectedPartner.id : false,
                lines,
            ]);
            if (requestId === this.totalsRequestId) {
                this.state.totals = totals;
            }
        } catch (error) {
            console.error("No se pudieron calcular los impuestos del carrito.", error);
            if (requestId === this.totalsRequestId) {
                this.state.totalsError = "No se pudo calcular el desglose de impuestos.";
            }
        } finally {
            if (requestId === this.totalsRequestId) {
                this.state.totalsLoading = false;
            }
        }
    }

    getCustomerDomain() {
        return [["active", "=", true]];
    }

    async selectCustomer(partner) {
        if (partner && !partner.display_name) {
            const [record] = await this.orm.read(
                "res.partner",
                [partner.id],
                ["display_name"]
            );
            partner = record ? { id: partner.id, display_name: record.display_name } : false;
        }
        this.state.selectedPartner = partner || null;
        this.state.checkoutError = "";
        this.state.checkoutSuccess = "";
        this.refreshTotals();
    }

    async checkout() {
        if (
            !this.state.cart.length ||
            !this.state.selectedPartner ||
            this.state.checkoutLoading
        ) {
            return;
        }

        this.state.checkoutLoading = true;
        this.state.checkoutError = "";
        this.state.checkoutSuccess = "";

        let order;
        try {
            order = await this.orm.call(
                "sale.order",
                "create_and_confirm_pos_order",
                [
                    this.state.selectedPartner.id,
                    this.state.cart.map((line) => ({
                        product_id: line.product.product_variant_id[0],
                        quantity: line.quantity,
                    })),
                ]
            );
        } catch (error) {
            console.error("No se pudo confirmar la venta de cafetería.", error);
            this.state.checkoutError = error.message || "No se pudo realizar la venta.";
            return;
        } finally {
            this.state.checkoutLoading = false;
        }

        this.state.cart = [];
        this.state.checkoutSuccess = `Venta ${order.name} realizada correctamente. Total: ${this.formatMoney(order.amount_total)}`;

        try {
            await this.action.doAction({
                type: "ir.actions.act_window",
                name: order.name,
                res_model: "sale.order",
                res_id: order.id,
                views: [[false, "form"]],
                target: "current",
            });
        } catch (error) {
            console.error("La venta se creó, pero no se pudo abrir el pedido.", error);
            this.state.checkoutError = `La venta ${order.name} se creó, pero no se pudo abrir.`;
        }
    }
}

registry.category("actions").add("modulo_cafeteria.cafeteria_pos", CafeteriaPos);