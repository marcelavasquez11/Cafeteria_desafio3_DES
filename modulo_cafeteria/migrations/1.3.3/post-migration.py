from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    # Ventas que ya existian: las canceladas pasan a "cancelada" y las con factura pagada a "pagada"
    env = api.Environment(cr, SUPERUSER_ID, {})
    ventas = env["sale.order"].with_context(permitir_edicion_pagada=True)
    ventas.search([("state", "=", "cancel")]).estado_venta = "cancelada"
    pagadas = ventas.search([("invoice_ids.payment_state", "in", ("paid", "in_payment"))])
    pagadas.estado_venta = "pagada"
