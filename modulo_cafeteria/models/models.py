# from odoo import models, fields, api


# class modulo_cafeteria(models.Model):
#     _name = 'modulo_cafeteria.modulo_cafeteria'
#     _description = 'modulo_cafeteria.modulo_cafeteria'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

