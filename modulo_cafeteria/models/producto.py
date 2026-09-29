from odoo import models, fields


class ProductoCafeteria(models.Model):
    _inherit = 'product.template'

    tipo_producto_cafeteria = fields.Selection(
        [
            ('bebida', 'Bebida'),
            ('comida', 'Comida'),
            ('reposteria', 'Repostería'),
        ],
        string='Tipo de producto'
    )

    tamano = fields.Selection(
        [
            ('pequeno', 'Pequeño'),
            ('mediano', 'Mediano'),
            ('grande', 'Grande'),
        ],
        string='Tamaño'
    )