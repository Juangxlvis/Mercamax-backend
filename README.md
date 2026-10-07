# 🛒 MercaMax — Backend

Sistema de gestión integral para supermercados. API REST construida con Django y desplegada en Google Cloud Run.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Django](https://img.shields.io/badge/Django-5.2.5-green?logo=django)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-NeonSQL-blue?logo=postgresql)
![Google Cloud Run](https://img.shields.io/badge/Deploy-Cloud%20Run-orange?logo=google-cloud)
![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-black?logo=github-actions)
![Tests](https://img.shields.io/badge/TestRail-24%2F24%20Passed-brightgreen)

---

## 📑 Tabla de contenido

- [URL de producción](#-url-de-producción)
- [Descripción](#-descripción)
- [Características principales](#-características-principales)
- [Arquitectura](#️-arquitectura)
- [Tecnologías](#-tecnologías)
- [Estructura del proyecto](#-estructura-del-proyecto)
- [Instalación local](#️-instalación-local)
- [Ejecución con Docker](#-ejecución-con-docker)
- [Variables de entorno](#-variables-de-entorno)
- [Autenticación y 2FA](#-autenticación-y-2fa)
- [Endpoints principales](#-endpoints-principales)
- [Roles de usuario](#-roles-de-usuario)
- [Seguridad](#-seguridad)
- [Despliegue y CI/CD](#-despliegue-y-cicd)
- [Pruebas](#-pruebas)
- [Monitoreo](#-monitoreo)
- [Solución de problemas](#-solución-de-problemas)
- [Repositorios relacionados](#-repositorios-relacionados)
- [Equipo](#-equipo)
- [Contexto académico](#-contexto-académico)

---

## 🌐 URL de producción

```
https://mercamax-backend-807300167790.us-central1.run.app
```

---

## 📋 Descripción

MercaMax es una solución de software para la gestión de supermercados que abarca cuatro procesos de negocio principales:

| Proceso | Descripción |
|---|---|
| 🔐 Autenticación | Login seguro con 2FA vía Gmail API, control de acceso por roles |
| 📦 Inventario | Productos con IVA configurable, lotes, stock, ubicaciones, alertas |
| 🛒 Ventas | Punto de venta, facturación consecutiva, envío de factura por correo |
| 🚚 Compras | Órdenes a proveedores, recepción de mercancía, pagos |

---

## ✨ Características principales

- **Login en dos pasos (2FA):** código de verificación enviado por correo mediante Gmail API (OAuth2).
- **Control de acceso por roles (RBAC):** cuatro perfiles con permisos diferenciados.
- **Protección contra fuerza bruta:** bloqueo automático de intentos fallidos con `django-axes`.
- **Inventario por lotes:** control de stock, ubicaciones en bodega, ajustes manuales y alertas.
- **IVA configurable** por producto.
- **Facturación consecutiva** con generación de PDF (`reportlab`) y envío automático por correo.
- **Anulación de ventas** restringida al gerente del supermercado.
- **Flujo de compras completo:** orden → aprobación → recepción de mercancía → factura → pago.
- **Despliegue continuo** a Cloud Run y monitoreo en Grafana Cloud.

---

## 🏗️ Arquitectura

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Angular 17     │────▶│  Django REST API  │────▶│  PostgreSQL     │
│  AWS Amplify    │     │  Google Cloud Run │     │  NeonSQL        │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                  │
                   ┌──────────────┼───────────────┐
                   │              │               │
          ┌────────┴────────┐ ┌───┴──────────┐ ┌──┴─────────────┐
          │  Grafana Cloud  │ │  Gmail API   │ │ GitHub Actions │
          │  (Monitoreo)    │ │  (2FA/Email) │ │ (CI/CD)        │
          └─────────────────┘ └──────────────┘ └────────────────┘
```

---

## 🚀 Tecnologías

| Categoría | Tecnología |
|---|---|
| Framework | Django 5.2.5 + Django REST Framework |
| Lenguaje | Python 3.11 |
| Base de datos | PostgreSQL (NeonSQL) |
| Autenticación | Token Authentication + 2FA vía Gmail API OAuth2 |
| Seguridad | django-axes (bloqueo por fuerza bruta), hashing PBKDF2 + SHA256 |
| PDF | reportlab |
| Contenedores | Docker |
| Deploy | Google Cloud Run |
| CI/CD | GitHub Actions |
| Monitoreo | Grafana Cloud |
| Pruebas | Newman (Postman), TestRail |

---

## 📁 Estructura del proyecto

```
Mercamax-backend/
├── .github/
│   └── workflows/
│       └── deploy.yml          # Pipeline CI/CD GitHub Actions
├── compras/                    # Proceso 4: Gestión de compras
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
├── inventario/                 # Proceso 2: Productos, categorías, proveedores
├── ventas/                     # Proceso 3: Punto de venta y facturación
├── users/                      # Proceso 1: Autenticación, 2FA y usuarios
├── bodega/                     # Lotes, ubicaciones y stock
├── core/                       # Notificaciones y utilidades compartidas
├── mercamax/                   # Configuración principal del proyecto
│   ├── settings.py
│   └── urls.py
├── Dockerfile
├── requirements.txt
└── manage.py
```

> Cada app (`compras`, `inventario`, `ventas`, `users`, `bodega`) sigue la misma convención de Django: `models.py`, `serializers.py`, `views.py` y `urls.py`.

---

## ⚙️ Instalación local

### Prerrequisitos

- Python 3.11+
- pip
- Git
- Una base de datos PostgreSQL (local o una instancia gratuita en [Neon](https://neon.tech))
- Credenciales OAuth2 de Gmail API (para 2FA y correos)

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/Juangxlvis/Mercamax-backend.git
cd Mercamax-backend

# 2. Crear entorno virtual
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
# Crear archivo .env en la raíz (ver sección "Variables de entorno")

# 5. Aplicar migraciones
python manage.py migrate

# 6. Crear superusuario
python manage.py createsuperuser

# 7. Ejecutar servidor
python manage.py runserver
```

La API estará disponible en `http://localhost:8000`.

---

## 🐳 Ejecución con Docker

```bash
# Construir la imagen
docker build -t mercamax-backend .

# Ejecutar el contenedor usando tu archivo .env
docker run --rm -p 8080:8080 --env-file .env mercamax-backend
```

> Cloud Run inyecta la variable `PORT` automáticamente; en local puedes ajustar el puerto según tu `Dockerfile`.

---

## 🔑 Variables de entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
DATABASE_URL=postgresql://usuario:password@host/db
SECRET_KEY=tu-secret-key
GMAIL_CLIENT_ID=tu-client-id
GMAIL_CLIENT_SECRET=tu-client-secret
GMAIL_REFRESH_TOKEN=tu-refresh-token
FRONTEND_URL=http://localhost:4200
```

| Variable | Descripción |
|---|---|
| `DATABASE_URL` | URL de conexión a PostgreSQL |
| `SECRET_KEY` | Clave secreta de Django |
| `GMAIL_CLIENT_ID` | Client ID de Gmail API para 2FA y correos |
| `GMAIL_CLIENT_SECRET` | Client Secret de Gmail API |
| `GMAIL_REFRESH_TOKEN` | Refresh token OAuth2 de Gmail (expira cada 7 días) |
| `FRONTEND_URL` | URL del frontend para CORS |

> ⚠️ El `GMAIL_REFRESH_TOKEN` expira cada 7 días. Renovar con `python get_token.py` y actualizar el valor en Cloud Run y en los secretos de GitHub.

> 🔒 **Nunca subas el archivo `.env` al repositorio.** Verifica que esté incluido en `.gitignore`.

---

## 🔐 Autenticación y 2FA

El acceso a la API usa **Token Authentication** precedido de un segundo factor por correo:

```
1. POST /api/auth/login/        → valida usuario/contraseña y envía código 2FA al correo
2. POST /api/auth/verify-2fa/   → valida el código y devuelve el token
3. Usar el token en cada petición protegida:
   Authorization: Token <tu-token>
```

Ejemplo ilustrativo con `curl`:

```bash
# Paso 1: login (envía el código al correo)
curl -X POST https://mercamax-backend-807300167790.us-central1.run.app/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "usuario", "password": "tu-password"}'

# Paso 2: verificar el código 2FA
curl -X POST https://mercamax-backend-807300167790.us-central1.run.app/api/auth/verify-2fa/ \
  -H "Content-Type: application/json" \
  -d '{"username": "usuario", "code": "123456"}'

# Paso 3: usar el token
curl https://mercamax-backend-807300167790.us-central1.run.app/api/inventario/productos/ \
  -H "Authorization: Token <tu-token>"
```

> Los nombres exactos de los campos del cuerpo pueden variar; revisa los serializers de `users/` o la colección de Postman.

---

## 📡 Endpoints principales

Todas las rutas (excepto el login) requieren el header `Authorization: Token <token>`.

### Autenticación
```
POST /api/auth/login/           # Login con credenciales
POST /api/auth/verify-2fa/      # Verificar código 2FA
POST /api/auth/validate-token/  # Validar token activo
```

### Inventario
```
GET  /api/inventario/productos/        # Listar productos
POST /api/inventario/productos/        # Crear producto
GET  /api/inventario/categorias/       # Listar categorías
GET  /api/inventario/proveedores/      # Listar proveedores
GET  /api/inventario/estadisticas/     # Estadísticas del inventario
```

### Ventas
```
POST /api/ventas/crear/                # Registrar venta
GET  /api/ventas/                      # Historial de ventas
GET  /api/ventas/{id}/pdf/             # Descargar factura PDF
POST /api/ventas/{id}/anular/          # Anular venta
GET  /api/ventas/buscar-producto/      # Buscar producto para venta
POST /api/ventas/clientes/             # Crear cliente
```

### Compras
```
POST /api/compras/ordenes/crear/                    # Crear orden de compra
GET  /api/compras/ordenes/                          # Listar órdenes
POST /api/compras/ordenes/{id}/aprobar-rechazar/    # Aprobar o rechazar orden
POST /api/compras/ordenes/{id}/recepcionar/         # Recepcionar mercancía
POST /api/compras/facturas/crear/                   # Registrar factura
POST /api/compras/facturas/{id}/registrar-pago/     # Registrar pago
```

### Bodega
```
GET  /api/bodega/lotes/             # Listar lotes
GET  /api/bodega/ubicaciones/       # Listar ubicaciones
GET  /api/bodega/stockitems/        # Listar items de stock
POST /api/bodega/inventory/adjust/  # Ajuste manual de stock
```

### Flujo típico de compras

```
Crear orden ──▶ Aprobar/Rechazar ──▶ Recepcionar mercancía ──▶ Registrar factura ──▶ Registrar pago
 (Gerente      (Gerente del          (Encargado de            (Gerente de          (Gerente de
  de compras)   supermercado)         inventario)              compras)             compras)
```

> Los responsables de cada paso son una guía; confirma los permisos reales en las vistas de `compras/views.py`.

---

## 🔐 Roles de usuario

| Rol | Acceso |
|---|---|
| `GERENTE_SUPERMERCADO` | Acceso total — aprueba órdenes, anula ventas |
| `GERENTE_COMPRAS` | Módulo de compras completo |
| `ENCARGADO_INVENTARIO` | Módulo de inventario y bodega |
| `CAJERO` | Solo punto de venta |

---

## 🛡️ Seguridad

- **2FA por correo** en cada inicio de sesión.
- **django-axes:** bloquea cuentas/IP tras varios intentos fallidos (protección contra fuerza bruta).
- **Contraseñas** almacenadas con PBKDF2 + SHA256.
- **CORS** restringido al dominio definido en `FRONTEND_URL`.
- **Secretos** gestionados mediante variables de entorno (nunca en el código).
- **Permisos por rol** aplicados en cada endpoint sensible (aprobar órdenes, anular ventas).

---

## 🚢 Despliegue y CI/CD

El despliegue es automático mediante **GitHub Actions** en cada push a `main`:

```yaml
# .github/workflows/deploy.yml
on:
  push:
    branches: [main]
```

Flujo general: `push a main` → build de la imagen Docker → despliegue en Cloud Run → servicio actualizado en `us-central1`.

Para despliegue manual:

```bash
gcloud run deploy mercamax-backend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --project mercamax-backend
```

Migraciones en producción:

```bash
gcloud run jobs execute migrate --region us-central1 --wait
```

> Ejecuta las migraciones **después** de cada despliegue que modifique los modelos.

---

## 🧪 Pruebas

### Pruebas automatizadas con Newman

```bash
# Instalar Newman
npm install -g newman newman-reporter-htmlextra

# Ejecutar colección completa
npx newman run MercaMax_Coleccion_Postman.json \
  --reporters cli,htmlextra \
  --reporter-htmlextra-export reporte-newman.html
```

### Pruebas unitarias backend

```bash
python manage.py test
```

### Pruebas unitarias frontend

```bash
cd ../Mercamax-frontend
ng test --watch=false --browsers=ChromeHeadless
```

### TestRail

Resultados registrados en https://drive.google.com/file/d/1lnHrUdw2eUVYTpnzC0S9NLd7pOhp1Yw7/view?usp=sharing — 24 casos de prueba con 100% Passed.

---

## 📊 Monitoreo

Dashboard de Grafana Cloud disponible en:
```
[https://galvis2044.grafana.net](https://galvis2044.grafana.net/goto/sqlhdn)
```

Métricas monitoreadas:
- Uso de CPU del contenedor
- Latencia de respuesta (ms)
- Respuestas HTTP por código
- Instancias activas de Cloud Run

---

## 🩺 Solución de problemas

| Problema | Causa probable | Solución |
|---|---|---|
| No llega el código 2FA ni los correos de factura | `GMAIL_REFRESH_TOKEN` vencido (7 días) | Ejecutar `python get_token.py` y actualizar el token en Cloud Run y GitHub |
| Error de CORS desde el frontend | `FRONTEND_URL` incorrecta | Ajustar la variable al dominio real del frontend |
| `OperationalError` al conectar a la base de datos | `DATABASE_URL` mal formada o BD en pausa (Neon) | Verificar la URL y que la instancia esté activa |
| Usuario bloqueado tras varios intentos | `django-axes` | Liberar con `python manage.py axes_reset` |
| Error 500 tras desplegar | Migraciones pendientes | Ejecutar el job `migrate` en Cloud Run |

---

## 🔗 Repositorios relacionados

- **Frontend (Angular 17):** `[Mercamax-frontend](https://github.com/Juangxlvis/mercamax-frontend.git)` — desplegado en AWS Amplify.

---

## 👥 Equipo

| Nombre | Correo | Rol |
|---|---|---|
| Juan José Galvis Copete | juanj.galvisc@uqvirtual.edu.co | Backend, DevOps, Cloud |
| Isabella García Gómez | isabella.garciag@uqvirtual.edu.co | Inventario, Documentación |
| Ana María Vélez Ramírez | anam.velezr@uqvirtual.edu.co | Ventas, Frontend |

---

## 🎓 Contexto académico

Proyecto desarrollado para la asignatura **Ingeniería de Software III**
Universidad del Quindío — Armenia, Colombia — 2026
