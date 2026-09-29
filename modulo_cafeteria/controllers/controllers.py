# from odoo import http


# class ModuloCafeteria(http.Controller):
#     @http.route('/modulo_cafeteria/modulo_cafeteria', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/modulo_cafeteria/modulo_cafeteria/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('modulo_cafeteria.listing', {
#             'root': '/modulo_cafeteria/modulo_cafeteria',
#             'objects': http.request.env['modulo_cafeteria.modulo_cafeteria'].search([]),
#         })

#     @http.route('/modulo_cafeteria/modulo_cafeteria/objects/<model("modulo_cafeteria.modulo_cafeteria"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('modulo_cafeteria.object', {
#             'object': obj
#         })

