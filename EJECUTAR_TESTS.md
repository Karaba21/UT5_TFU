# 🧪 Cómo Ejecutar los Tests

## Prerrequisitos

1. **Asegúrate de que Docker esté corriendo:**

   ```powershell
   docker ps
   ```

2. **Levanta la aplicación si no está corriendo:**

   ```powershell
   docker compose up -d
   ```

3. **Verifica que el servicio esté disponible:**
   ```powershell
   Invoke-RestMethod -Uri "http://localhost:5000/health"
   ```

---

## Opción 1: Ejecutar TODOS los tests (Recomendado)

Desde la **raíz del proyecto**, ejecuta:

```powershell
.\scripts\run_all_tests.ps1
```

Este script:

- ✅ Verifica que el servicio esté disponible
- ✅ Ejecuta todas las pruebas en secuencia:
  1. Cache-Aside (Rendimiento)
  2. Circuit Breaker (Disponibilidad)
  3. Queue-Based Load Leveling (Rendimiento)
  4. SOAP Endpoint (XML)
- ✅ Muestra un resumen al final

**Tiempo estimado:** 2-3 minutos

---

## Opción 2: Ejecutar tests individuales

### 1. Test de Cache-Aside (Rendimiento)

```powershell
.\scripts\test_cache_aside.ps1
```

**Qué demuestra:** Mejora de rendimiento usando Redis como cache

### 2. Test de Circuit Breaker (Disponibilidad)

```powershell
.\scripts\test_circuit_breaker.ps1
```

**Qué demuestra:** Protección contra fallos repetidos

### 3. Test de Queue-Based Load Leveling

```powershell
.\scripts\test_queue_load_leveling.ps1
```

**Qué demuestra:** Procesamiento controlado de carga

### 4. Test de SOAP Endpoint

```powershell
.\scripts\test_soap_endpoint.ps1
```

**Qué demuestra:** Funcionamiento del endpoint SOAP con XML

---

## Solución de Problemas

### Error: "El servicio no está disponible"

```powershell
# Verifica que Docker esté corriendo
docker ps

# Si no está corriendo, inicia los servicios
docker compose up -d

# Espera unos segundos y verifica
Invoke-RestMethod -Uri "http://localhost:5000/health"
```

### Error: "Script no se puede ejecutar"

```powershell
# Permite la ejecución de scripts (solo la primera vez)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Error: "No se puede encontrar el script"

Asegúrate de ejecutar el comando desde la **raíz del proyecto**:

```powershell
# Verifica que estás en la raíz
pwd
# Debe mostrar: C:\Users\ASUS\Desktop\tfu 5\UT5_TFU

# Si no, cambia al directorio correcto
cd "C:\Users\ASUS\Desktop\tfu 5\UT5_TFU"
```

---

## Resultados Esperados

### ✅ Cache-Aside

- Primera llamada: ~50-100ms (lee del archivo)
- Segundas llamadas: ~10-30ms (lee de Redis)
- **Mejora:** 30-50% más rápido

### ✅ Circuit Breaker

- Primeros 3 fallos: Error normal
- Después del 3er fallo: "Circuito abierto"
- Después de 10 segundos: Intento de reinicio

### ✅ Queue-Based Load Leveling

- Encolado: Respuesta inmediata (< 50ms)
- Procesamiento: ~2 segundos por tarea

### ✅ SOAP Endpoint

- Respuesta en formato XML válido
- Status Code: 200 OK

---

## Ejecución Rápida (Una línea)

```powershell
docker compose up -d; Start-Sleep -Seconds 5; .\scripts\run_all_tests.ps1
```

Este comando:

1. Levanta los servicios Docker
2. Espera 5 segundos para que inicien
3. Ejecuta todos los tests
