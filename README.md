# Trabajo Final Unidad 5 – Arquitectura Monolítica

## Mini Gestor de Proyectos

Este proyecto implementa una **arquitectura monolítica** utilizando **Flask** y **Docker**, con un único servicio que gestiona usuarios, proyectos y tareas mediante **blueprints** y **acceso directo a datos**.

📹 [Aquí va un video explicativo del proyecto](https://drive.google.com/drive/folders/1vzmv4lIT7H1yjGgBBuUKAB06DZlHdZ-d?usp=sharing)

📊 [Presentación del proyecto](https://www.canva.com/design/DAG3nAWY3TE/1H8MXLYz0LoazjWywDKNkA/edit?utm_content=DAG3nAWY3TE&utm_campaign=designshare&utm_medium=link2&utm_source=sharebutton)

---

## Estructura general

```
UT5_TFU/
│
├── docker-compose.yaml
│
└── monolito/
    ├── app.py                    # Aplicación principal Flask
    ├── Dockerfile
    ├── requirements.txt
    │
    ├── controllers/              # Blueprints (endpoints)
    │   ├── usuarios_controller.py
    │   ├── proyectos_controller.py
    │   └── tareas_controller.py
    │
    ├── services/                 # Lógica de negocio y acceso a datos
    │   ├── usuarios_service.py
    │   └── proyectos_service.py
    │
    └── middleware/               # Autenticación y autorización
        └── auth.py               # Gatekeeper, Tokens, Valet Keys
```

---

## Arquitectura Monolítica

| Módulo                   | Responsabilidad                                                                                            | Dependencias                        |
| ------------------------ | ---------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| **usuarios_controller**  | Endpoints para gestión de usuarios (GET, POST)                                                             | usuarios_service                    |
| **proyectos_controller** | Endpoints para gestión de proyectos (GET, POST). Valida usuario existente mediante acceso directo a datos. | proyectos_service, usuarios_service |
| **tareas_controller**    | Endpoints para gestión de tareas (GET, POST). Valida proyecto existente mediante acceso directo a datos.   | proyectos_service                   |

**Características:**

- **Un único servicio Flask** en el puerto 5000
- **Acceso directo a datos**: Los módulos se comunican mediante llamadas directas a funciones, sin HTTP interno
- **Blueprints**: Organización modular mediante Flask Blueprints
- **Persistencia local**: Cada módulo persiste sus datos en archivos JSON separados
- **Redis**: Utilizado para cache (Cache-Aside) y colas (Queue-Based Load Leveling)

---

## Despliegue con Docker

### Requisitos previos

- Tener instalado **Docker Desktop** o Docker Engine.
- No se necesita instalar Flask ni dependencias localmente (Docker se encarga).

### Levantar la aplicación

Desde la raíz del proyecto:

```bash
docker compose up --build
```

Esto construye e inicia:

- **monolito** -> http://localhost:5000
- **redis** -> localhost:6379 (para cache y colas)

La respuesta esperada en `/health` es:

```json
{ "status": "ok", "service": "monolito" }
```

### Flujo de uso

**1. Generar un token de acceso:**

```powershell
Invoke-RestMethod -Uri http://localhost:5000/tokens -Method POST
```

**2. Crear un usuario:**

```powershell
Invoke-RestMethod -Uri http://localhost:5000/usuarios -Method POST `
  -Headers @{"X-API-Key"="<token>"} `
  -Body '{"nombre":"Claudio"}' -ContentType "application/json"
```

**3. Crear un proyecto (Valida el usuario):**

```powershell
Invoke-RestMethod -Uri http://localhost:5000/proyectos -Method POST `
  -Headers @{"X-API-Key"="<token>"} `
  -Body '{"nombre":"App UT5", "usuario_id":1}' -ContentType "application/json"
```

**4. Crear una tarea (valida el proyecto):**

```powershell
Invoke-RestMethod -Uri http://localhost:5000/tareas -Method POST `
  -Headers @{"X-API-Key"="<token>"} `
  -Body '{"nombre":"Diseñar endpoints", "proyecto_id":1}' -ContentType "application/json"
```

### Arquitectura Interna

```
┌─────────────────────────────────────────────────────────┐
│                    MONOLITO (Puerto 5000)                │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Usuarios    │  │  Proyectos   │  │   Tareas     │ │
│  │  Controller  │  │  Controller  │  │  Controller  │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
│         │                  │                  │         │
│         └──────────┬───────┴──────────────────┘         │
│                    │                                     │
│         ┌──────────▼──────────┐                         │
│         │   Services Layer     │                         │
│         │  (Acceso directo)    │                         │
│         └──────────┬───────────┘                         │
│                    │                                     │
│         ┌──────────▼──────────┐                         │
│         │   Middleware Auth    │                         │
│         │  (Gatekeeper/Valet)  │                         │
│         └──────────────────────┘                         │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
         ┌──────────────────┐
         │   Redis Cache    │
         │   (Puerto 6379)  │
         └──────────────────┘
```

**Flujo de datos:**

- El usuario se crea mediante `usuarios_controller`
- `proyectos_controller` accede directamente a `usuarios_service` para validar el `usuario_id` (sin HTTP)
- `tareas_controller` accede directamente a `proyectos_service` para validar el `proyecto_id` (sin HTTP)

## 🏗️ Arquitectura aplicada

**Arquitectura monolítica unificada:**

- **Un solo despliegue**: Todo el sistema en un único contenedor
- **Comunicación directa**: Los módulos se comunican mediante llamadas a funciones, sin overhead de red
- **Organización modular**: Blueprints para separación de responsabilidades
- **Persistencia local**: Datos en formato JSON para simplicidad de la demo
- **Disponibilidad básica**: Endpoint `/health` para monitoreo

# UT4 - Arquitectura Distribuida

## DEMO DE PATRONES ARQUITECTÓNICOS

Este proyecto demuestra **patrones de arquitectura** aplicados sobre una **arquitectura monolítica** con Flask, Docker y Redis.  
Se incluyen patrones de **Disponibilidad**, **Rendimiento** y **Seguridad**, implementados y probados con ejemplos reales.

---

## DEMO DE DISPONIBILIDAD

### Health Endpoint Monitoring

Permite monitorear si el servicio monolítico está activo y funcionando correctamente.

**Comandos de prueba:**

```powershell
(iwr http://localhost:5000/health).Content   # MONOLITO
```

Respuesta esperada:

```json
{ "status": "ok", "service": "monolito" }
```

Simulación de falla:

```powershell
(iwr http://localhost:5000/health).Content
docker stop ut5-tfu-monolito-1
(iwr http://localhost:5000/health).Content
docker start ut5-tfu-monolito-1
```

### Circuit Breaker

Controla fallos repetidos en el acceso a datos para evitar saturar al sistema.

El archivo `circuit_state.json` guarda el estado del circuito (abierto/cerrado, contador de fallos).

**Simulación:**

Intento crear un proyecto:

```powershell
Invoke-RestMethod -Uri http://localhost:5000/proyectos -Method POST `
  -Headers @{"X-API-Key"="supersecreta123"} `
  -Body '{"nombre":"App Prueba","usuario_id":999}' -ContentType "application/json"
```

Respuesta esperada (si el usuario no existe o hay error):

```json
{ "error": "Servicio de usuarios no disponible" }
```

Luego de 3 intentos fallidos:

```json
{
  "error": "Circuito abierto: servicio de usuarios no disponible temporalmente"
}
```

En los logs quedará registrado:

```
⚠️ Circuit breaker abierto: demasiadas fallas en usuarios-service.
```

El circuito se reinicia automáticamente después de 10 segundos.

## DEMO DE RENDIMIENTO

### Cache-Aside Pattern

Redis guarda temporalmente los proyectos consultados para mejorar el rendimiento.

**Comando:**

```powershell
(iwr http://localhost:5000/proyectos/1 -Headers @{"X-API-Key"="supersecreta123"}).Content
```

**Funcionamiento:**

1. Si el proyecto está en Redis → se devuelve desde la cache (Cache hit).
2. Si no está → se lee desde `proyectos.json` y luego se guarda en Redis:
   ```python
   cache.setex(cache_key, CACHE_TTL, json.dumps(proyecto))
   ```

**Verificación:**

- Primera llamada: Cache miss (lee del archivo)
- Segunda llamada: Cache hit (lee de Redis)

### Queue-Based Load Leveling

Redis actúa como una cola temporal de tareas para distribuir la carga.

**Encolar una tarea:**

```powershell
Invoke-RestMethod -Uri http://localhost:5000/tareas -Method POST `
  -Headers @{"X-API-Key"="supersecreta123"} `
  -Body '{"nombre":"Tarea 1","proyecto_id":1}' -ContentType "application/json"
```

Respuesta:

```json
{ "mensaje": "Tarea encolada correctamente" }
```

**Comprobación en Redis:**

```bash
docker exec -it redis-cache redis-cli
LRANGE tareas_pendientes 0 -1
```

Se debería ver:

```
1) "{\"nombre\": \"Tarea 1\", \"proyecto_id\": 1}"
2) "{\"nombre\": \"Tarea 2\", \"proyecto_id\": 1}"
```

**Verificar que tareas.json sigue vacío:**

```bash
docker exec -it ut5-tfu-monolito-1 cat tareas.json
```

**Procesar las tareas:**

```powershell
Invoke-RestMethod -Uri http://localhost:5000/procesar_tareas -Method POST `
  -Headers @{"X-API-Key"="supersecreta123"}
```

**Verificar nuevamente:**

```bash
docker exec -it ut5-tfu-monolito-1 cat tareas.json
```

Resultado esperado:

```json
[
  { "id": 1, "nombre": "Tarea 1", "proyecto_id": 1 },
  { "id": 2, "nombre": "Tarea 2", "proyecto_id": 1 }
]
```

**Logs esperados:**

```
⚙️ Procesando tarea: Tarea 1
⚙️ Procesando tarea: Tarea 2
```

## DEMO DE SEGURIDAD

### Gatekeeper Pattern

Centraliza la autenticación en el middleware del monolito.
Todas las peticiones deben contener una API Key válida o un token.

**Sin API Key:**

```powershell
Invoke-RestMethod -Uri http://localhost:5000/proyectos
```

Respuesta:

```json
{
  "error": "Token de acceso requerido. Use header 'Authorization: Bearer <token>' o 'X-API-Key: <token>'"
}
```

**Con API Key válida:**

```powershell
Invoke-RestMethod -Uri http://localhost:5000/proyectos -Headers @{"X-API-Key"="supersecreta123"}
```

### Generación de Tokens

**Generar un token de acceso:**

```powershell
Invoke-RestMethod -Uri http://localhost:5000/tokens -Method POST
```

Respuesta:

```json
{
  "mensaje": "Token generado exitosamente",
  "token": "<token_generado>",
  "instrucciones": "Use este token en el header 'Authorization: Bearer <token>' o 'X-API-Key: <token>'"
}
```

### Valet Key Pattern

Genera tokens con permisos limitados y específicos (scopes, métodos HTTP, recursos).

**Generar un Valet Key (requiere API Key del gateway):**

```powershell
Invoke-RestMethod -Uri http://localhost:5000/valet-keys -Method POST `
  -Headers @{"X-API-Key"="supersecreta123"} `
  -Body '{
    "scopes": ["read:proyectos"],
    "allowed_methods": ["GET"],
    "resource_constraints": {"proyecto_id": 1},
    "expires_in_hours": 1
  }' -ContentType "application/json"
```

Respuesta:

```json
{
  "mensaje": "Valet Key generado exitosamente",
  "valet_key": "<valet_key_token>",
  "metadata": {
    "scopes": ["read:proyectos"],
    "allowed_methods": ["GET"],
    "resource_constraints": { "proyecto_id": 1 },
    "expires_at": "2024-..."
  }
}
```

**Usar el Valet Key:**

```powershell
# ✅ Permitido: Leer proyecto con ID 1
Invoke-RestMethod -Uri http://localhost:5000/proyectos/1 `
  -Headers @{"X-API-Key"="<valet_key>"}

# ❌ Denegado: Leer proyecto con ID 2 (fuera del scope)
Invoke-RestMethod -Uri http://localhost:5000/proyectos/2 `
  -Headers @{"X-API-Key"="<valet_key>"}

# ❌ Denegado: Crear proyecto (método POST no permitido)
Invoke-RestMethod -Uri http://localhost:5000/proyectos -Method POST `
  -Headers @{"X-API-Key"="<valet_key>"} `
  -Body '{"nombre":"Nuevo","usuario_id":1}' -ContentType "application/json"
```

---

## 🌐 Endpoint SOAP con XML

La aplicación incluye un **endpoint SOAP** que retorna datos en formato **XML**, cumpliendo con el requisito de la Parte 2.

### Métodos SOAP disponibles

1. **obtener_estadisticas**: Obtiene estadísticas del sistema (proyectos, tareas, usuarios)
2. **obtener_proyecto_por_id**: Obtiene un proyecto específico por su ID

### Probar con Postman

**Configuración:**

- **Método:** `POST`
- **URL:** `http://localhost:5000/soap`
- **Headers:**
  - `Content-Type: text/xml; charset=utf-8`
  - `SOAPAction: ""` (opcional)

**Ejemplo 1: Obtener estadísticas generales**

Body (raw XML):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:est="estadisticas">
   <soapenv:Header/>
   <soapenv:Body>
      <est:obtener_estadisticas>
         <est:tipo>general</est:tipo>
      </est:obtener_estadisticas>
   </soapenv:Body>
</soapenv:Envelope>
```

**Ejemplo 2: Obtener proyecto por ID**

Body (raw XML):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:est="estadisticas">
   <soapenv:Header/>
   <soapenv:Body>
      <est:obtener_proyecto_por_id>
         <est:proyecto_id>1</est:proyecto_id>
      </est:obtener_proyecto_por_id>
   </soapenv:Body>
</soapenv:Envelope>
```

**Respuesta esperada (XML):**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<estadisticas>
    <tipo>general</tipo>
    <total_proyectos>2</total_proyectos>
    <total_tareas>3</total_tareas>
    <total_usuarios>1</total_usuarios>
    <timestamp>{"total_proyectos": 2, ...}</timestamp>
</estadisticas>
```

### Probar con PowerShell

```powershell
$soapBody = @"
<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:est="estadisticas">
   <soapenv:Header/>
   <soapenv:Body>
      <est:obtener_estadisticas>
         <est:tipo>general</est:tipo>
      </est:obtener_estadisticas>
   </soapenv:Body>
</soapenv:Envelope>
"@

Invoke-WebRequest -Uri "http://localhost:5000/soap" `
    -Method POST `
    -ContentType "text/xml; charset=utf-8" `
    -Body $soapBody
```

---

## 📜 Scripts de Prueba

Se incluyen scripts PowerShell para demostrar las mejoras en atributos de calidad:

### Ejecutar todas las pruebas

```powershell
.\scripts\run_all_tests.ps1
```

### Pruebas individuales

1. **Cache-Aside (Rendimiento)**

   ```powershell
   .\scripts\test_cache_aside.ps1
   ```

   - Mide el tiempo de respuesta con y sin cache
   - Demuestra la mejora de rendimiento usando Redis

2. **Circuit Breaker (Disponibilidad)**

   ```powershell
   .\scripts\test_circuit_breaker.ps1
   ```

   - Simula fallos y muestra cómo el circuito se abre
   - Demuestra protección contra sobrecarga

3. **Queue-Based Load Leveling (Rendimiento)**

   ```powershell
   .\scripts\test_queue_load_leveling.ps1
   ```

   - Encola múltiples tareas rápidamente
   - Muestra procesamiento controlado de carga

4. **SOAP Endpoint (XML)**
   ```powershell
   .\scripts\test_soap_endpoint.ps1
   ```
   - Prueba el endpoint SOAP
   - Verifica respuestas en formato XML

### Resultados esperados

Los scripts muestran:

- **Rendimiento:** Mejora del 30-50% con cache vs sin cache
- **Disponibilidad:** Circuit breaker activándose después de 3 fallos
- **Carga:** Procesamiento controlado de tareas en cola
- **Integración:** Respuestas XML válidas desde SOAP

---

## 📋 Checklist de Entregables (Parte 2)

✅ **Código de la aplicación**

- ✅ API REST con JSON (endpoints existentes)
- ✅ Endpoint SOAP con XML (`/soap`)
- ✅ Arquitectura monolítica mantenida

✅ **Docker Compose**

- ✅ `docker-compose.yaml` para despliegue
- ✅ Servicios: monolito + redis

✅ **Scripts de prueba**

- ✅ Scripts PowerShell para demostrar mejoras
- ✅ Pruebas de rendimiento (Cache-Aside)
- ✅ Pruebas de disponibilidad (Circuit Breaker)
- ✅ Pruebas de carga (Queue-Based Load Leveling)
- ✅ Pruebas de SOAP/XML

✅ **Documentación**

- ✅ README con instrucciones
- ✅ Ejemplos para Postman
- ✅ Ejemplos para PowerShell/curl

---
