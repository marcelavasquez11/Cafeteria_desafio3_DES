import base64
import random
import string
import uuid

from num2words import num2words

from odoo import fields, models

# Datos ficticios del emisor que aparecen en la factura (DTE de uso académico).
# Se cambian aquí y la factura los toma.
DATOS_EMISOR_DTE = {
    "razon_social": "Cafetería Marymel",
    "nit": "0000-000000-000-0",
    "nrc": "123456-7",
    "actividad": "Servicio de cafetería y venta de alimentos y bebidas",
    "direccion": "El Salvador, San Salvador Este, Calle Don Bosco, Casa 1000",
    "telefono": "1234-5678",
    "correo": "cafeteriamarymel@gmail.com",
    "nombre_comercial": "Cafetería Marymel",
    "tipo_establecimiento": "Casa Matriz",
}

# Enlace de consulta pública que lleva el QR (simulado)
URL_CONSULTA_DTE = "https://admin.factura.gob.sv/consultaPublica"

# Caracteres que puede tener el sello de recepción (letras mayúsculas y números)
CARACTERES_SELLO = string.ascii_uppercase + string.digits


class FacturaDTE(models.Model):
    _inherit = "account.move"

    # Códigos del DTE.
    # Aquí se SIMULAN: se inventan al azar una sola vez y se guardan en la factura,
    dte_codigo_generacion = fields.Char(string="Código de generación", copy=False, readonly=True)
    dte_numero_control = fields.Char(string="Número de control", copy=False, readonly=True)
    dte_sello_recepcion = fields.Char(string="Sello de recepción", copy=False, readonly=True)

    def _generar_codigos_dte(self):
        # Inventa los códigos al azar, solo para las facturas que todavía no los tienen
        for factura in self.filtered(lambda f: not f.dte_codigo_generacion):
            # Código de generación: un UUID aleatorio (uuid4), ej. D0B553E9-1972-4D18-...
            codigo_generacion = str(uuid.uuid4()).upper()

            # Número de control: formato "DTE-01-M001P001-" más 15 dígitos al azar
            numero_control = "DTE-01-M001P001-" + "".join(random.choices(string.digits, k=15))

            # Sello de recepción: 40 caracteres al azar (letras mayúsculas y números)
            sello = "".join(random.choices(CARACTERES_SELLO, k=40))

            # sudo(): se guardan aunque la factura ya esté publicada o el usuario no edite facturas
            factura.sudo().write(
                {
                    "dte_codigo_generacion": codigo_generacion,
                    "dte_numero_control": numero_control,
                    "dte_sello_recepcion": sello,
                }
            )

    def action_post(self):
        # Al publicar la factura se le asignan sus códigos simulados
        resultado = super().action_post()
        self._generar_codigos_dte()
        return resultado

    def _dte_datos(self):
        # Reúne todo lo que necesita la plantilla del PDF para armar el encabezado del DTE
        self.ensure_one()

        # Si la factura es anterior a este cambio (o aún no tiene códigos), se generan ahora
        self._generar_codigos_dte()

        # Fecha y hora de generación: cuando se creó la factura, en la zona horaria del usuario
        fecha = fields.Datetime.context_timestamp(
            self, self.create_date or fields.Datetime.now()
        )

        # QR: imagen PNG que apunta a la consulta pública de Hacienda con el código de
        # generación y la fecha de emisión. Es simulado: Hacienda no tiene este documento.
        url_qr = "%s?ambiente=00&codGen=%s&fechaEmi=%s" % (
            URL_CONSULTA_DTE,
            self.dte_codigo_generacion,
            fecha.strftime("%Y-%m-%d"),
        )
        imagen_qr = self.env["ir.actions.report"].barcode("QR", url_qr, width=130, height=130)

        return {
            "emisor": DATOS_EMISOR_DTE,
            "codigo_generacion": self.dte_codigo_generacion,
            "numero_control": self.dte_numero_control,
            "sello_recepcion": self.dte_sello_recepcion,
            "fecha_hora": fecha.strftime("%Y-%m-%d %H:%M:%S"),
            # El PNG se incrusta en el PDF como texto base64
            "qr": base64.b64encode(imagen_qr).decode(),
        }

    def _dte_valor_en_letras(self):
        # Ej.: 27.00 -> "VEINTISIETE DÓLARES"; 4.65 -> "CUATRO DÓLARES CON SESENTA Y CINCO CENTAVOS"
        self.ensure_one()
        total = self.currency_id.round(self.amount_total)
        entero = int(total)
        centavos = int(round((total - entero) * 100))

        def en_letras(numero):
            # num2words devuelve "uno" y "veintiuno"; antes de "dólares" se dice "un" y "veintiún"
            texto = num2words(numero, lang="es").upper()
            if texto.endswith("VEINTIUNO"):
                return texto[: -len("VEINTIUNO")] + "VEINTIÚN"
            if texto.endswith("UNO"):
                return texto[:-1]
            return texto

        resultado = "%s %s" % (en_letras(entero), "DÓLAR" if entero == 1 else "DÓLARES")
        if centavos:
            resultado += " CON %s CENTAVO%s" % (en_letras(centavos), "" if centavos == 1 else "S")
        return resultado
