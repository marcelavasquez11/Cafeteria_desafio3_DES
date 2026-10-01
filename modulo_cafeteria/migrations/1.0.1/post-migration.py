from odoo import SUPERUSER_ID, api


PRODUCT_XMLIDS = (
    "producto_seed_croissant",
    "producto_seed_latte",
    "producto_seed_capuchino",
    "producto_seed_te_chai",
    "producto_seed_sandwich",
    "producto_seed_muffin",
    "producto_seed_dona",
    "producto_seed_limonada",
    "producto_seed_zumo_naranja",
    "producto_seed_tarta_chocolate",
)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    sales_tax = env.ref("modulo_cafeteria.impuesto_ventas_13")
    purchase_tax = env.ref("modulo_cafeteria.impuesto_compras_13")

    for xmlid in PRODUCT_XMLIDS:
        product = env.ref(f"modulo_cafeteria.{xmlid}", raise_if_not_found=False)
        if product:
            product.write(
                {
                    "taxes_id": [(6, 0, sales_tax.ids)],
                    "supplier_taxes_id": [(6, 0, purchase_tax.ids)],
                }
            )