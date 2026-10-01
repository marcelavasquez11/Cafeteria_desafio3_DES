from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    # El combo ahora suma todos sus productos: se recalculan opciones y productos combo
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["product.combo.item"].search([])._compute_extra_price()
    env["product.template"].search([("type", "=", "combo")])._sincronizar_precios_combo()
