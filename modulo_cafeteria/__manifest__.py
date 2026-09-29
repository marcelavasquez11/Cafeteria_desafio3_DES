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
    'stock',
    'account',
    ],

    'data': [
        'security/ir.model.access.csv',
        'views/producto_views.xml',
         'views/cafeteria_menu.xml',
    ],

    'installable': True,
    'application': True,
}