#  Trabajo Final Unidad 3 – Soluciones Arquitectónicas

##  Mini Gestor de Proyectos

Este proyecto implementa una **arquitectura de microservicios** utilizando **Flask** y **Docker**, con tres servicios independientes que se comunican entre sí mediante **HTTP interno**.

📹 [Aquí va un video explicativo del proyecto](https://drive.google.com/drive/folders/1vzmv4lIT7H1yjGgBBuUKAB06DZlHdZ-d?usp=sharing)

📊 [Presentación del proyecto](https://www.canva.com/design/DAG3nAWY3TE/1H8MXLYz0LoazjWywDKNkA/edit?utm_content=DAG3nAWY3TE&utm_campaign=designshare&utm_medium=link2&utm_source=sharebutton)

---

##  Estructura general


UT3-TFU/
│
├── docker-compose.yml
│
├── usuarios-service/
│ ├── app.py
│ ├── Dockerfile
│ └── requirements.txt
│
├── proyectos-service/
│ ├── app.py
│ ├── Dockerfile
│ └── requirements.txt
│
└── tareas-service/
├── app.py
├── Dockerfile
└── requirements.txt


---

##  Servicios

| Servicio | Puerto | Responsabilidad | Dependencias |
|-----------|---------|----------------|---------------|
| **usuarios-service** | 5001 | Gestiona usuarios (GET, POST) | — |
| **proyectos-service** | 5002 | Gestiona proyectos (GET, POST). Valida usuario existente llamando al servicio de usuarios. | usuarios-service |
| **tareas-service** | 5003 | Gestiona tareas (GET, POST). Valida proyecto existente llamando al servicio de proyectos. | proyectos-service |

Cada servicio persiste sus datos localmente en un archivo JSON.

---

##  Despliegue con Docker

###  Requisitos previos
- Tener instalado **Docker Desktop** o Docker Engine.
- No se necesita instalar Flask ni dependencias localmente (Docker se encarga).

###  Levantar la aplicación

Desde la raíz del proyecto:
```bash
docker compose up --build

Esto construye e inicia los tres servicios:
usuarios-service  -> http://localhost:5001
proyectos-service -> http://localhost:5002
tareas-service    -> http://localhost:5003

Cada uno tiene su propio contenedor y se comunican internamente mediante la red tfu3_network.
La respuesta esperada es: 
{"status": "ok"}

Flujo de uso
Crear un usuario
Invoke-RestMethod -Uri http://localhost:5001/usuarios -Method POST -Body '{"nombre":"Claudio"}' -ContentType "application/json"

Crear un proyecto (Valida el usuario)
Invoke-RestMethod -Uri http://localhost:5002/proyectos -Method POST -Body '{"nombre":"App UT3", "usuario_id":1}' -ContentType "application/json"

Crear una tarea (valida el proyecto)
Invoke-RestMethod -Uri http://localhost:5003/tareas -Method POST -Body '{"nombre":"Diseñar endpoints", "proyecto_id":1}' -ContentType "application/json"


Listar la informacion
Crear una tarea (valida el proyecto)

+--------------------+        +--------------------+        +--------------------+
|  usuarios-service  |        | proyectos-service  |        |  tareas-service    |
| (puerto 5001)      | <----> | (puerto 5002)      | <----> | (puerto 5003)      |
|  Maneja usuarios   |        | Valida usuarios    |        | Valida proyectos   |
+--------------------+        +--------------------+        +--------------------+
El usuario se crea en usuarios-service.

proyectos-service consulta internamente al usuarios-service para validar el usuario_id.

tareas-service consulta internamente al proyectos-service para validar el proyecto_id.

## 🏗️ Arquitectura aplicada

Partición por dominio funcional: cada microservicio representa un subdominio del sistema.

Escalabilidad horizontal: cada servicio puede ejecutarse en múltiples instancias.

Despliegue independiente: cada servicio se puede actualizar o reiniciar sin afectar a los demás.

Comunicación HTTP interna: mediante la red Docker.

Persistencia local: datos en formato JSON para simplicidad de la demo.

Disponibilidad básica: endpoint /health para monitoreo.


#  UT4 - Arquitectura Distribuida  
## DEMO DE PATRONES ARQUITECTÓNICOS  

Este proyecto demuestra **patrones de arquitectura** aplicados sobre una arquitectura basada en **microservicios** con Flask, Docker y Redis.  
Se incluyen patrones de **Disponibilidad**, **Rendimiento** y **Seguridad**, implementados y probados con ejemplos reales.

---

##  DEMO DE DISPONIBILIDAD  

###  Health Endpoint Monitoring

Permite monitorear si cada microservicio está activo y funcionando correctamente.

**Comandos de prueba:**
```powershell
(iwr http://localhost:5001/health).Content   # USUARIOS  
(iwr http://localhost:5002/health).Content   # PROYECTOS  
(iwr http://localhost:5003/health).Content   # TAREAS  
(iwr http://localhost:5000/health).Content   # GATEWAY  

Respuesta esperada:
{"status":"ok"}

Simulación de falla:
(iwr http://localhost:5001/health).Content
docker stop ut3-tfu-usuarios-service-1
(iwr http://localhost:5001/health).Content
docker start ut3-tfu-usuarios-service-1

### Circuit Breaker

Controla fallos repetidos entre servicios para evitar saturar al sistema.

El archivo circuit_state.json guarda:

Simulación:

Intento crear un proyecto
Invoke-RestMethod -Uri http://localhost:5000/proyectos/proyectos -Method POST `
-Headers @{"X-API-Key"="supersecreta123"} `
-Body '{"nombre":"App Prueba","usuario_id":1}' -ContentType "application/json"

Respuesta esperada:
{"error":"Servicio de usuarios no disponible"}

Luego de 3 intentos:
{"error":"Circuito abierto: servicio de usuarios no disponible temporalmente"}


En los logs quedará registrado:
Circuit breaker abierto: demasiadas fallas en usuarios-service.

Reinicio el servicio:
docker start ut3-tfu-usuarios-service-1


###Demo de rendimiento
#Cache-Aside Pattern

Redis guarda temporalmente los proyectos consultados para mejorar el rendimiento.

Comando:
(iwr http://localhost:5000/proyectos/proyectos/1 -Headers @{"X-API-Key"="supersecreta123"}).Content

Funcionamiento:

Si el proyecto está en Redis → se devuelve desde la cache.

Si no está → se lee desde proyectos.json y luego se guarda en Redis:
cache.setex(cache_key, CACHE_TTL, json.dumps(proyecto))

#Queue-Based Load Leveling
Redis actúa como una cola temporal de tareas para distribuir la carga.

Invoke-RestMethod -Uri http://localhost:5003/tareas -Method POST `
-Body '{"nombre":"Tarea 1","proyecto_id":1}' -ContentType "application/json"

{"mensaje":"Tarea encolada correctamente"}

Comprobación en Redis:

docker exec -it redis-cache redis-cli
LRANGE tareas_pendientes 0 -1

Se deberia ver:
1) "{\"nombre\": \"Tarea 1\", \"proyecto_id\": 1}"
2) "{\"nombre\": \"Tarea 2\", \"proyecto_id\": 1}"

Verificar que tareas.json sigue vacío:

docker exec -it ut3-tfu-tareas-service-1 cat tareas.json

Procesar las tareas:
Invoke-RestMethod -Uri http://localhost:5003/procesar_tareas -Method POST


Verificar nuevamente:
docker exec -it ut3-tfu-tareas-service-1 cat tareas.json

Resultado:
[
  {"id": 1, "nombre": "Analizar logs", "proyecto_id": 5},
  {"id": 2, "nombre": "Generar reporte", "proyecto_id": 3}
]

Logs esperados:
Procesando tarea: Tarea 1

###DEMO DE SEGURIDAD

##Gatekeeper Pattern

Centraliza la autenticación en el Gateway.
Todas las peticiones deben pasar por gateway-service y contener una API Key válida.

Sin API Key:
Invoke-RestMethod -Uri http://localhost:5000/proyectos/proyectos

Respuesta:
{"error":"Acceso denegado: API Key inválida"}


Con API Key válida:
Invoke-RestMethod -Uri http://localhost:5000/proyectos/proyectos -Headers @{"X-API-Key"="supersecreta123"}



---



