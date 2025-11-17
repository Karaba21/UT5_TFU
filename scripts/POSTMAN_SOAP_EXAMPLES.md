# Ejemplos para Postman - Endpoint SOAP

## Configuración Base

**URL:** `http://localhost:5000/soap`  
**Método:** `POST`  
**Headers:**

- `Content-Type: text/xml; charset=utf-8`
- `SOAPAction:` (vacío o omitir)

---

## Ejemplo 1: Obtener Estadísticas Generales

**Request Body (raw - XML):**

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

**Tipos disponibles:**

- `general` - Todas las estadísticas
- `proyectos` - Solo proyectos
- `tareas` - Solo tareas
- `usuarios` - Solo usuarios

---

## Ejemplo 2: Obtener Proyecto por ID

**Request Body (raw - XML):**

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

---

## Pasos en Postman

1. **Crear nueva request:**

   - Click en "New" → "HTTP Request"
   - Nombre: "SOAP - Obtener Estadísticas"

2. **Configurar método y URL:**

   - Método: `POST`
   - URL: `http://localhost:5000/soap`

3. **Configurar Headers:**

   - Click en la pestaña "Headers"
   - Agregar:
     - Key: `Content-Type`
     - Value: `text/xml; charset=utf-8`

4. **Configurar Body:**

   - Click en la pestaña "Body"
   - Seleccionar "raw"
   - En el dropdown, seleccionar "XML"
   - Pegar el XML del ejemplo

5. **Enviar request:**
   - Click en "Send"
   - Verificar que la respuesta sea XML

---

## Respuesta Esperada

**Ejemplo de respuesta (Estadísticas):**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
   <soapenv:Body>
      <tns:obtener_estadisticasResponse xmlns:tns="estadisticas">
         <tns:obtener_estadisticasResult>
            <?xml version="1.0" encoding="UTF-8"?>
            <estadisticas>
                <tipo>general</tipo>
                <total_proyectos>2</total_proyectos>
                <total_tareas>3</total_tareas>
                <total_usuarios>1</total_usuarios>
                <timestamp>{"total_proyectos": 2, ...}</timestamp>
            </estadisticas>
         </tns:obtener_estadisticasResult>
      </tns:obtener_estadisticasResponse>
   </soapenv:Body>
</soapenv:Envelope>
```

---

## Troubleshooting

**Error: "Method not allowed"**

- Verificar que el método sea `POST` (no GET)

**Error: "Invalid XML"**

- Verificar que el XML esté bien formado
- Asegurarse de que los namespaces estén correctos

**Error: "No response"**

- Verificar que el servicio esté corriendo: `http://localhost:5000/health`
- Verificar que Docker esté activo: `docker ps`

**Respuesta vacía o error 500**

- Verificar los logs del contenedor: `docker logs ut5-tfu-monolito-1`
- Asegurarse de que existan datos (proyectos.json, tareas.json, usuarios.json)
