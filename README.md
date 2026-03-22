# Odoo + PrestaShop Connector

Conector bidireccional entre Odoo 16 y PrestaShop 9 mediante Docker Compose.

---

## Requisitos

- Docker Desktop instalado y abierto
- Crear una carpeta llamada `odoo-prestashop-podoks`
- Puertos **8069** y **8080** libres

---

## Método de instalación

1. Descomprimir el `.zip`
2. Buscar el archivo `start.bat` y hacerle doble clic

---

## Configuración de PrestaShop

Accedemos a la aplicación Docker Desktop y en el apartado **Containers** encontraremos el nuestro creado. Si clicamos en él nos saldrá una nueva pestaña con las diferentes partes del proyecto. Accedemos a la que pone **prestashop-1** y en la nueva pestaña buscamos la que pone **Files**. Navegamos hasta la siguiente ruta:

```
var > www > html
```

Debajo de `admin-api` hay una carpeta que se genera con código aleatorio (esta se genera de forma aleatoria cada vez que se instala PrestaShop desde cero por motivos de seguridad).

**Ejemplo:** `admin4285r9fxj2eytyxyp45`

Copiamos el nombre de esa carpeta y accedemos a:

```
http://localhost:8080/<nombre de carpeta anterior>
```

En el login introducimos los siguientes datos:

| Campo | Valor |
|---|---|
| Correo electrónico | `admin@test.com` |
| Contraseña | `adminpassword` |

Una vez dentro del panel de administración de PrestaShop, hacemos scroll en la barra lateral hasta llegar a **Parámetros avanzados**, y entramos en **Servicios web**. En la esquina superior derecha hay un botón que dice **Añadir nueva clave de servicio web**; clicamos en él.

En la nueva pestaña, en el apartado **Clave**, introducimos la siguiente:

```
9BD4XS8X7IJASRI412JST3EIIBT43RKP
```

Nos aseguramos de que el botón de **Activar la clave de servicio web** esté en verde y le damos permisos a los siguientes recursos de la API:

- Customers
- Employees
- Order_details
- Orders
- Products
- Stock_availables
- Stocks

>  Asegúrate de dar **todos los permisos** a cada uno de esos recursos antes de guardar.

---

## Configuración de Odoo

Accedemos a `http://localhost:8069/web/login` y rellenamos el formulario de creación de base de datos con los siguientes datos:

| Campo | Valor |
|---|---|
| Contraseña maestra | *(la que elijas)* |
| Nombre de base de datos | `odoo` |
| Correo | *(el que elijas)* |
| Contraseña | *(la que elijas)* |
| Demo data | Desmarcado |

>  Guárdate el correo y la contraseña que uses. Para las pruebas se puede usar la misma contraseña para la cuenta maestra y la normal.

Una vez dentro de Odoo, nos vamos al apartado **Apps** y descargamos las siguientes:

- Inventario
- Ventas
- PrestaShop Connector *(para esta última hay que desactivar el filtro de la barra de búsqueda de aplicaciones)*

Con el conector instalado, vamos a **Configuración** y hacemos scroll hasta el fondo hasta encontrar **Modo desarrollador**. Clicamos en él y cuando se recargue la página aparecerá una nueva pestaña llamada **Técnico** en la barra superior.

Dentro de **Técnico**, buscamos **Automatización → Acciones planificadas** y buscamos la acción llamada **Sincronización PrestaShop - Odoo**. Una vez dentro podemos ejecutarla manualmente con el botón de la esquina superior izquierda.

---

## Encender y apagar los servicios (siguientes veces)

En la aplicación Docker Desktop se habrá generado un container llamado **odoo-prestashop-podoks**. Desde la columna **Actions** podrás pararlo y encenderlo cuando quieras.

> **NUNCA usar `docker compose down`**, ya que elimina todos los datos.

---

*Realizado por Joaquín Gómez Martínez*
