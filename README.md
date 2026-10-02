# ☕ Cafetería Marymel — Odoo 19

Sistema de gestión para una cafetería desarrollado con **Odoo 19** y **PostgreSQL 16**, utilizando Docker para facilitar su instalación y ejecución.

El sistema permite gestionar productos, inventario, ventas, clientes y facturación desde una interfaz adaptada para una cafetería.

---

## ✨ Funcionalidades

- 🛒 **Carrito de ventas**
  - Selección de productos.
  - Control de cantidades.
  - Selección de cliente.
  - Cálculo automático del total.
  - Cobro de la venta.

- 📦 **Inventario**
  - Catálogo de productos.
  - Categorías.
  - Precio de venta y costo.
  - Control de existencias.
  - Stock mínimo.
  - Alerta de stock bajo.

- 👥 **Clientes**
  - Gestión de clientes mediante los contactos nativos de Odoo.
  - Creación y edición de clientes.
  - Selección de clientes desde el carrito.

- 🧾 **Ventas y facturación**
  - Registro de ventas.
  - Descuento automático del stock al confirmar una venta.
  - Generación de facturas.
  - IVA del 13%.
  - Registro de pagos en efectivo.
  - Factura PDF personalizada con formato inspirado en una representación DTE.

---

## 🛠️ Tecnologías

| Tecnología | Versión |
|---|---|
| Odoo | 19.0 |
| PostgreSQL | 16 |
| Docker | Requerido |
| Python | Incluido en Odoo |
| JavaScript | Interfaz del carrito |
| XML / QWeb | Vistas y reportes |
| SCSS | Estilos |

---

# 🚀 Instalación y ejecución

## 1. Requisitos

Antes de comenzar, tener instalado:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Git

Verificar Docker:

```bash
docker --version
```

Verificar Docker Compose:

```bash
docker compose version
```

---

## 2. Clonar el repositorio

Abrir una terminal y ejecutar:

```bash
git clone https://github.com/marcelavasquez11/Cafeteria_desafio3_DES.git
```

Entrar al proyecto:

```bash
cd Cafeteria_desafio3_DES
```

---

## 3. Levantar los contenedores

Ejecutar:

```bash
docker compose up -d
```

Este comando levanta:

- **Odoo 19**
- **PostgreSQL 16**

Comprobar que los contenedores estén ejecutándose:

```bash
docker compose ps
```

Los contenedores principales utilizados por el proyecto son:

```text
cafeteria_odoo
cafeteria_db
```

---

## 4. Acceder a Odoo

Abrir en el navegador:

```text
http://localhost:8069
```

Desde allí se puede acceder a Odoo y al módulo **Cafetería**.

---

# 🔄 Actualizar el módulo

Cuando se realicen cambios en el código del módulo, ejecutar:

```bash
docker exec cafeteria_odoo odoo -d cafeteria -u modulo_cafeteria --db_host=db --db_port=5432 --db_user=odoo --db_password=odoo --stop-after-init
```

Después reiniciar Odoo:

```bash
docker restart cafeteria_odoo
```

Si el navegador mantiene archivos antiguos, realizar una recarga forzada:

```text
Ctrl + F5
```

---

# ▶️ Detener el proyecto

Para detener los contenedores:

```bash
docker compose down
```

Para volver a levantarlos:

```bash
docker compose up -d
```

> **Nota:** `docker compose down` detiene y elimina los contenedores, pero los datos de PostgreSQL se conservan mientras se mantenga el volumen configurado por Docker.

---

# 📁 Estructura principal

```text
Cafeteria_desafio3_DES/
│
├── docker-compose.yml
│
├── modulo_cafeteria/
│   ├── __init__.py
│   ├── __manifest__.py
│   │
│   ├── data/
│   │   ├── productos_seed.xml
│   │   └── impuestos_13.xml
│   │
│   ├── models/
│   │   └── sale_order.py
│   │
│   ├── reports/
│   │   └── ...
│   │
│   ├── static/
│   │   └── src/
│   │       ├── js/
│   │       ├── xml/
│   │       └── scss/
│   │
│   └── views/
│       └── ...
│
└── README.md
```

---

# 🧪 Flujo principal

El funcionamiento principal del sistema es:

```text
Cafetería
    │
    ├── 🛒 Carrito
    │      │
    │      └── Seleccionar productos
    │              │
    │              └── Cobrar
    │
    ├── 📦 Inventario
    │      └── Productos y stock
    │
    ├── 👥 Clientes
    │      └── Clientes de Odoo
    │
    └── 🧾 Ventas
           └── Ventas realizadas
```

Al confirmar una venta:

```text
Venta
  ↓
Confirmación
  ↓
Actualización del stock
  ↓
Factura
  ↓
Pago en efectivo
  ↓
Factura pagada
```

---

## 📌 Información del proyecto

**Proyecto:** Cafetería Marymel  
**Plataforma:** Odoo 19  
**Base de datos:** PostgreSQL 16  
**Contenedores:** Docker  
**Tipo:** Proyecto académico

---

---

## 👥 Equipo de desarrollo

### ☕ Cafetería Marymel

- **Wendy Aguilar**
- **Melissa Flores**

---

> *Proyecto desarrollado con Odoo 19, PostgreSQL 16 y Docker con fines académicos · 2026*
