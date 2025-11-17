# 📋 Resumen de Patrones Arquitectónicos Implementados

## 1. 🏥 Health Monitoring Point

**Ubicación:** Todos los servicios (`/health` endpoint)

**Implementación:**
- Endpoint `GET /health` en cada servicio (usuarios, proyectos, tareas)
- Retorna `{"status": "ok"}` con código 200
- Permite a sistemas externos (orquestadores, balanceadores) verificar el estado de los servicios

**Código:**
```python
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200
```

---

## 2. ⚡ Circuit Breaker

**Ubicación:** `proyectos-service/app.py` (líneas 252-279)

**Implementación:**
- **Estado del circuito:** Almacenado en `circuit_state.json`
- **Lógica:**
  - Cuenta fallos consecutivos (`fail_count`)
  - Si hay 3 o más fallos (`FAIL_THRESHOLD = 3`), abre el circuito
  - Circuito abierto → rechaza llamadas inmediatamente (retorna 503)
  - Después de 10 segundos (`RESET_TIMEOUT = 10`), intenta cerrar el circuito
  - Si la llamada tiene éxito, resetea el contador

**Flujo:**
1. Verifica si el circuito está abierto
2. Si está abierto y no ha pasado el timeout → rechaza (503)
3. Intenta llamar al servicio de usuarios
4. Si falla → incrementa `fail_count`
5. Si `fail_count >= 3` → abre el circuito

---

## 3. 💾 Cache Aside

**Ubicación:** `proyectos-service/app.py` (líneas 222-240)

**Implementación:**
- **Cache:** Redis con TTL de 30 segundos
- **Flujo:**
  1. **Read:** Busca en Redis primero → si no está (cache miss), lee del archivo JSON → guarda en Redis
  2. **Cache hit:** Retorna directamente desde Redis (más rápido)
  3. **Cache miss:** Lee de persistencia y actualiza cache

**Código clave:**
```python
# Buscar en cache
cached_proyecto = cache.get(cache_key)
if cached_proyecto:
    return jsonify(json.loads(cached_proyecto)), 200  # Cache hit

# Si no está, leer del archivo
# ... leer archivo ...
# Guardar en cache
cache.setex(cache_key, CACHE_TTL, json.dumps(proyecto))
```

---

## 4. 📬 Queue Based Load Leveling

**Ubicación:** `tareas-service/app.py` (líneas 205-234, 237-260)

**Implementación:**
- **Cola:** Redis List (`tareas_pendientes`)
- **Flujo:**
  1. **POST /tareas:** Recibe la tarea → la encola en Redis (`RPUSH`) → retorna inmediatamente (202)
  2. **POST /procesar_tareas:** Procesa tareas de la cola una por una (`LPOP`)
  3. Simula tiempo de procesamiento (2 segundos) para demostrar la nivelación de carga

**Beneficios:**
- El cliente no espera el procesamiento completo
- El servicio puede procesar tareas de forma controlada
- Evita sobrecarga si llegan muchas peticiones simultáneas

**Código:**
```python
# Encolar
queue.rpush(QUEUE_KEY, json.dumps(data))  # Agregar a la cola

# Procesar
tarea_json = queue.lpop(QUEUE_KEY)  # Obtener y remover de la cola
```

---

## 5. 🚪 Gatekeeper

**Ubicación:** Todos los servicios (decorador `@gatekeeper_required`)

**Implementación:**
- **Decorador:** `@gatekeeper_required` valida tokens/API keys antes de ejecutar endpoints
- **Validación:**
  - Extrae token de headers: `Authorization: Bearer <token>` o `X-API-Key: <token>`
  - Verifica token en Redis (cache rápido) o archivo JSON (persistencia)
  - Si no tiene token → retorna 401
  - Si token inválido → retorna 403

**Tokens:**
- **Token regular:** Generado con `POST /tokens` en usuarios-service
- **Token interno:** `internal-service-token-2024` para comunicación entre servicios

**Endpoints protegidos:**
- `/usuarios` (GET, POST)
- `/proyectos` (GET, POST)
- `/tareas` (GET, POST, POST /procesar_tareas)

---

## 6. 🔑 Valet Key

**Ubicación:** Todos los servicios (`@valet_key_required` y endpoint `/valet-keys`)

**Implementación:**
- **Concepto:** Tokens temporales con permisos limitados y específicos
- **Generación:** `POST /valet-keys` (requiere token válido)
- **Características:**
  - **Scopes:** Permisos específicos (ej: `read:proyectos`, `write:usuarios`)
  - **Métodos HTTP:** Solo permite ciertos métodos (GET, POST, etc.)
  - **Restricciones de recursos:** Acceso solo a recursos específicos (ej: `proyecto_id: 1`)
  - **Expiración:** TTL configurable (default: 1 hora)

**Validación:**
- Decorador `@valet_key_required(scope="read:proyectos", resource_key="proyecto_id", method="GET")`
- Verifica: expiración, scopes, métodos permitidos, recursos específicos
- Si es token regular (no valet key) → permite acceso completo

**Ejemplo de uso:**
```json
POST /valet-keys
{
  "scopes": ["read:proyectos"],
  "allowed_methods": ["GET"],
  "resource_constraints": {"proyecto_id": 1},
  "expires_in_hours": 1
}
```

**Metadata almacenada en Redis:**
- `valet_key:<token>` → JSON con scopes, métodos, restricciones, expiración

---

## 🔄 Flujo Completo de Ejemplo

1. **Cliente solicita token** → `POST /tokens`
2. **Cliente solicita Valet Key** → `POST /valet-keys` (con token)
3. **Cliente usa Valet Key** → `GET /proyectos/1` (con valet key)
4. **Gatekeeper valida** → Verifica token/valet key
5. **Valet Key validator** → Verifica permisos específicos (scope, recurso, método)
6. **Cache Aside** → Busca en Redis, si no está lee archivo
7. **Circuit Breaker** → Si llama a otro servicio, protege contra fallos
8. **Queue Load Leveling** → Si es tarea, la encola para procesamiento asíncrono

---

## 📊 Tecnologías Utilizadas

- **Flask:** Framework web
- **Redis:** Cache y cola de mensajes
- **Docker Compose:** Orquestación de servicios
- **JSON:** Persistencia de datos y tokens

