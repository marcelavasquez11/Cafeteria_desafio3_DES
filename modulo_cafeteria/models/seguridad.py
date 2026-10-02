from odoo import Command, api, models

# Aplicaciones nativas de Odoo que solo ve el Administrador (el Cajero ve solo la Cafetería)
MENUS_SOLO_ADMINISTRADOR = [
    "sale.sale_menu_root",  # Ventas de Odoo
    "contacts.menu_contacts",  # Contactos (el Cajero no ve el módulo de clientes)
    "mail.menu_root_discuss",  # Conversaciones
    "spreadsheet_dashboard.spreadsheet_dashboard_menu_root",  # Dashboards de Odoo
    "base.menu_management",  # Aplicaciones
]


class MenuCafeteria(models.Model):
    _inherit = "ir.ui.menu"

    @api.model
    def restringir_menus_cafeteria(self):
        # Deja las aplicaciones nativas de Odoo visibles solo para el Administrador de la cafetería.
        # Se ejecuta en cada actualización del módulo y no falla si algún menú no existe.
        administrador = self.env.ref("modulo_cafeteria.grupo_administrador")
        for xmlid in MENUS_SOLO_ADMINISTRADOR:
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if menu:
                menu.group_ids = [Command.set(administrador.ids)]
