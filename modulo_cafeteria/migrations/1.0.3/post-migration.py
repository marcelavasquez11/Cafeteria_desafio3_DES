from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    # Recalcula la categoría de los clientes existentes (ahora depende de "es empresa")
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["res.partner"].search([])._compute_categoria_cliente()
