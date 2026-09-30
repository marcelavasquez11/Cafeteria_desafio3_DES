{
    'name': 'Gestión de Cafetería',

    'summary': 'Gestión básica de clientes, productos, inventario, ventas y facturación.',

    'description': """
        Sistema mínimo viable para la gestión de la cafetería.

        Permite gestionar:
        - Clientes
        - Productos
        - Inventario
        - Ventas
        - Facturación
    """,

    'author': 'Grupo de Cafetería',
    'website': '',

    'category': 'Sales',
    'version': '1.0.0',

    'depends': [
    'base',
    'contacts',
    'product',
    'sale_management',
    'sale_stock',
    'stock',
    'account',
    ],

    'data': [
        'security/ir.model.access.csv',
        'views/producto_views.xml',
         'views/cafeteria_menu.xml',
         "views/product_cafeteria_views.xml",
        'data/productos_seed.xml',
        "views/sale_order_views.xml",
        'views/account_move_cafeteria_views.xml',
    ],

    'assets': {
        'web.assets_web': [
            'modulo_cafeteria/static/src/scss/cafeteria.scss',
        ],
    },

    'installable': True,
    'application': True,
}