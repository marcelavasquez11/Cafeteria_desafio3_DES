from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    # El Extra Price de los combos ahora se calcula desde el descuento: se recalcula lo existente
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["product.combo.item"].search([])._compute_extra_price()
