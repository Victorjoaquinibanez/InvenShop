# InvenShop

Sistema de gestión e inventario con comercio electrónico, hecho con Django.
Trabajo Final de Aplicación de **Programación IV** (Tecnicatura Superior en Desarrollo de Software, ITSE, 2026).

## Qué hace

- **Catálogo público**: muestra 12 productos por página. Se puede filtrar por categoría, buscar por nombre o descripción (las dos cosas a la vez) y ordenar por precio o nombre. Los productos sin stock aparecen como "Agotado".
- **Carrito en la sesión**: permite agregar, cambiar cantidades, quitar y vaciar. Controla el stock y calcula subtotales y el total.
- **Checkout en dos pasos**:
  1. Datos de envío, que se validan.
  2. Confirmación final.

  El pedido y el descuento de stock se hacen en **una sola transacción**: si falta un producto, no se registra nada.
- **Pedidos**: el estado pasa de Pendiente a Pagado y después a Enviado. También puede pasar a Cancelado, y en ese caso se repone el stock. Cada cliente ve solo su historial.
- **Panel de gestión** (empleados y administradores):
  - Productos: alta, edición, ajuste rápido de stock y mostrar/ocultar.
  - Categorías.
  - Pedidos con filtros.
  - Usuarios y reportes de ventas (solo Administrador).
- **Admin de Django personalizado**:
  - Búsqueda, filtros laterales y edición de `stock` y `activo` desde el listado.
  - Los detalles del pedido se muestran dentro del pedido (inline) y son de solo lectura.

## Roles

| Rol | Puede |
|---|---|
| **Administrador** | Todo: usuarios y roles, catálogo, pedidos y reportes |
| **Empleado** | Productos, categorías, stock y estado de los pedidos (no administra usuarios) |
| **Cliente** | Catálogo, carrito, hacer pedidos, ver su historial y editar su perfil |

Cada rol es un **grupo de Django** con sus permisos (ver [usuarios/roles.py](usuarios/roles.py)). Los grupos se crean solos al correr `migrate`. Las vistas usan `LoginRequiredMixin` / `PermissionRequiredMixin` (y `@login_required` / `@permission_required` en las vistas de función). Un usuario logueado sin permiso recibe un **403**; uno sin sesión va al login.

## Instalación (Windows)

Hace falta **Python 3.12 o superior**.

```powershell
git clone https://github.com/Victorjoaquinibanez/InvenShop.git
cd InvenShop

python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

copy .env.example .env
# Abrir .env y poner una SECRET_KEY nueva (la línea para generarla está en el mismo archivo)

python manage.py migrate
python manage.py cargar_datos_demo
python manage.py runserver
```

Después se abre http://127.0.0.1:8000.

En Linux o Mac cambian dos comandos: `source venv/bin/activate` y `cp .env.example .env`.

### Usuarios de prueba

Los crea `cargar_datos_demo`. Todos tienen la contraseña **`InvenShop2026!`**.

| Rol | Nombre | Email |
|---|---|---|
| Administrador | Ana Gómez | ana.gomez@invenshop.com |
| Empleado | Esteban Ruiz | esteban.ruiz@invenshop.com |
| Cliente | Carla Medina | carla.medina@example.com |
| Cliente | Martín Herrera | martin.herrera@example.com |
| Cliente | Sofía Ledesma | sofia.ledesma@example.com |
| Cliente | Julián Paz | julian.paz@example.com |
| Cliente | Valentina Ríos | valentina.rios@example.com |

También carga 16 pedidos de los últimos seis meses, en los cuatro estados, para que el panel y los reportes tengan datos.

## Tests

```powershell
python manage.py test
```

Los tests cubren:

- Registro con rol Cliente.
- Redirección según el rol.
- Permisos y respuestas 403.
- Filtros del catálogo.
- Límites de stock del carrito.
- Checkout con transacción.
- Transiciones de estado con reposición de stock.
- Que un cliente no pueda ver pedidos ajenos.
- Cantidad de consultas fija (sin N+1).

## Estructura

```
config/      configuración (settings lee el .env) y URLs principales
usuarios/    usuario propio (login con email), roles/grupos, registro, perfil, gestión de usuarios
catalogo/    Categoria y Producto, catálogo público, gestión de productos y categorías
carrito/     carrito en la sesión (sin modelos)
pedidos/     Pedido y DetallePedido, checkout, historial, estados
panel/       inicio del panel de gestión y reportes
templates/   base.html (Bootstrap 5), includes y páginas de error 403/404/500
static/      CSS propio
```

## Seguridad

- **Credenciales:** la `SECRET_KEY` y la configuración salen del `.env`, que no se sube a git.
- **Errores:** con `DEBUG=False` no se muestran detalles internos; se usan las plantillas 403, 404 y 500.
  Para probarlo en la computadora local hay que poner `DEBUG=False` y `SERVIR_MEDIA=True` en el `.env`,
  y levantar el servidor con `python manage.py runserver --insecure` (si no, faltan el CSS y las fotos).
- **Producción:** con `SEGURO_HTTPS=True` las cookies viajan solo por HTTPS, se fuerza HTTPS y se activa HSTS,
  y así se pasa `python manage.py check --deploy`.
- **Formularios:** todos los que cambian datos usan POST con `{% csrf_token %}`.
- **XSS:** las plantillas escapan el contenido automáticamente.
- **Carrito:** en la sesión se guardan solo los ids y las cantidades. Los precios se leen siempre de la base, así que no se pueden manipular.
- **Stock:** se descuenta con un `UPDATE` condicional (`stock >= cantidad`) dentro de la transacción. Así, si dos clientes compran la última unidad al mismo tiempo, solo una compra pasa.
