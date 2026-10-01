from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    # Recalcula el extra price de las opciones de combo y los precios de los productos combo
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["product.combo.item"].search([])._compute_extra_price()
    env["product.template"].search([("type", "=", "combo")])._sincronizar_precios_combo()
