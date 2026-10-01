from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    # Se desactiva el envío de SMS al validar entregas: Odoo abría un asistente "Enviar SMS"
    # cuando el cliente tenía teléfono y la entrega no se validaba (el stock no se descontaba)
    def _pre_action_done_hook(self):
        return super(StockPicking, self.with_context(skip_sms=True))._pre_action_done_hook()

    def _send_confirmation_email(self):
        return super(StockPicking, self.with_context(skip_sms=True))._send_confirmation_email()
