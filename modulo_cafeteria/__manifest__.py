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
    'version': '1.1.5',

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
        'views/cliente_views.xml',
        'views/cafeteria_menu.xml',
         "views/product_cafeteria_views.xml",
        'data/impuestos_13.xml',
        'data/productos_seed.xml',
        "views/sale_order_views.xml",
        'views/account_move_cafeteria_views.xml',
        'reports/factura_cafeteria_template.xml',
        'reports/factura_cafeteria_report.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'modulo_cafeteria/static/src/scss/cafeteria.scss',
            'modulo_cafeteria/static/src/xml/cafeteria_pos.xml',
            'modulo_cafeteria/static/src/js/cafeteria_pos.js',
            'modulo_cafeteria/static/src/js/masked_char_field.js',
            'modulo_cafeteria/static/src/xml/cafeteria_dashboard.xml',
            'modulo_cafeteria/static/src/js/cafeteria_dashboard.js',
        ],
    },

    'installable': True,
    'application': True,
}