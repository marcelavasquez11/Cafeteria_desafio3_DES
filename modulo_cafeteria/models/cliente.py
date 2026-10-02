import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# Monto acumulado de compras (en $) a partir del cual un cliente pasa a ser "frecuente"
MONTO_CLIENTE_FRECUENTE = 30.0
# Porcentaje de descuento por categoría de cliente (regular no recibe)
DESCUENTO_FRECUENTE = 7.0
DESCUENTO_CORPORATIVO = 10.0
# Estados de una venta que cuentan como compra realizada
ESTADOS_COMPRA = ("sale", "done")

# Correo: texto@dominio.ext, sin espacios
REGEX_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# DUI: 8 dígitos, guion y dígito verificador (ej: 06689569-4)
REGEX_DUI = re.compile(r"^\d{8}-\d$")
# Teléfono: dígitos, espacios, guiones, paréntesis y un "+" inicial opcional
REGEX_TELEFONO = re.compile(r"^\+?[\d\s\-()]+$")


class ClienteCafeteria(models.Model):
    # Se extiende el contacto nativo para que el carrito, las ventas y las facturas lo sigan usando
    _inherit = "res.partner"

    # Fecha en que se registró el cliente (viene con la fecha actual, pero se puede editar)
    fecha_registro = fields.Date(
        string="Fecha de registro",
        default=fields.Date.context_today,
        copy=False,
    )

    # Cliente genérico "Consumidor final": se usa cuando el cliente no quiere ser registrado.
    # No tiene datos y nunca cambia de categoría ni se borra.
    es_consumidor_final = fields.Boolean(string="Consumidor final", copy=False)

    # Documento Único de Identidad (se escribe con la máscara 00000000-0)
    dui = fields.Char(string="DUI", size=10)

    # Historial de compras confirmadas del cliente (se muestra en su ficha)
    compra_ids = fields.One2many(
        "sale.order",
        "partner_id",
        string="Historial de compras",
        domain=[("state", "in", ESTADOS_COMPRA)],
    )

    # Suma de todas las compras confirmadas del cliente
    total_compras = fields.Monetary(
        string="Total acumulado en compras",
        currency_field="currency_id",
        compute="_compute_total_compras",
        store=True,
    )

    # Categoría del cliente: se elige directamente en una lista desplegable
    categoria_cliente = fields.Selection(
        selection=[
            ("regular", "Regular"),
            ("frecuente", "Frecuente"),
            ("corporativo", "Corporativo"),
        ],
        string="Categoría de cliente",
        default="regular",
        required=True,
    )

    # Número de color de la etiqueta de la categoría (ver cafeteria.scss)
    color_categoria = fields.Integer(compute="_compute_color_categoria")

    # Descuento que se aplica automáticamente a sus ventas
    descuento_cliente = fields.Float(
        string="Descuento (%)",
        compute="_compute_descuento_cliente",
    )

    @api.depends("compra_ids.amount_total", "compra_ids.state")
    def _compute_total_compras(self):
        # Se suman solo las ventas confirmadas
        for cliente in self:
            cliente.total_compras = sum(cliente.compra_ids.mapped("amount_total"))

    @api.depends("categoria_cliente")
    def _compute_color_categoria(self):
        # regular: celeste, frecuente: verde claro, corporativo: lila
        colores = {"regular": 101, "frecuente": 102, "corporativo": 103}
        for cliente in self:
            cliente.color_categoria = colores.get(cliente.categoria_cliente, 101)

    @api.depends("categoria_cliente")
    def _compute_descuento_cliente(self):
        # Corporativo 10%, frecuente 7%, regular sin descuento
        descuentos = {
            "corporativo": DESCUENTO_CORPORATIVO,
            "frecuente": DESCUENTO_FRECUENTE,
        }
        for cliente in self:
            cliente.descuento_cliente = descuentos.get(cliente.categoria_cliente, 0.0)

    def actualizar_categoria_por_compras(self):
        # Un cliente regular pasa a frecuente al acumular el monto mínimo en compras
        # (no toca a los corporativos ni baja de categoría a nadie)
        for cliente in self:
            # El consumidor final junta las compras de mucha gente distinta: nunca sube de categoría
            if (
                not cliente.es_consumidor_final
                and cliente.categoria_cliente == "regular"
                and cliente.total_compras >= MONTO_CLIENTE_FRECUENTE
            ):
                cliente.categoria_cliente = "frecuente"

    @api.onchange("dui")
    def _onchange_dui(self):
        # Máscara: al escribir 9 dígitos se inserta el guion (06689569-4)
        for cliente in self:
            if cliente.dui:
                digitos = re.sub(r"\D", "", cliente.dui)[:9]
                cliente.dui = f"{digitos[:8]}-{digitos[8:]}" if len(digitos) > 8 else digitos

    @api.constrains("dui")
    def _check_formato_dui(self):
        # El DUI es opcional, pero si se escribe debe cumplir 00000000-0
        for cliente in self:
            if cliente.dui and not REGEX_DUI.match(cliente.dui):
                raise ValidationError(
                    _("El DUI '%s' no es válido (formato: 00000000-0).") % cliente.dui
                )

    @api.constrains("email")
    def _check_formato_email(self):
        # El correo es opcional, pero si se escribe debe tener formato válido
        for cliente in self:
            if cliente.email and not REGEX_EMAIL.match(cliente.email.strip()):
                raise ValidationError(
                    _("El correo '%s' no tiene un formato válido (ej: nombre@correo.com).")
                    % cliente.email
                )

    @api.constrains("phone")
    def _check_formato_telefono(self):
        # El teléfono es opcional, pero si se escribe debe tener entre 7 y 15 dígitos
        for cliente in self:
            if not cliente.phone:
                continue
            telefono = cliente.phone.strip()
            cantidad_digitos = len(re.sub(r"\D", "", telefono))
            if not REGEX_TELEFONO.match(telefono) or not 7 <= cantidad_digitos <= 15:
                raise ValidationError(
                    _("El teléfono '%s' no es válido (use solo números, +, - y paréntesis; 7 a 15 dígitos).")
                    % cliente.phone
                )

    def unlink(self):
        # El cliente "Consumidor final" es parte del sistema: no se puede borrar
        if any(cliente.es_consumidor_final for cliente in self):
            raise ValidationError(_("El cliente 'Consumidor final' no se puede borrar."))
        return super().unlink()
