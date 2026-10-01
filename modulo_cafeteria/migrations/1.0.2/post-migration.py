from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    sales_tax = env.ref("modulo_cafeteria.impuesto_ventas_13")
    purchase_tax = env.ref("modulo_cafeteria.impuesto_compras_13")
    products = env["product.template"].search([])

    products.write(
        {
            "taxes_id": [(6, 0, sales_tax.ids)],
            "supplier_taxes_id": [(6, 0, purchase_tax.ids)],
        }
    )