# Script de prueba para demostrar el patrón Queue-Based Load Leveling
# Muestra cómo las tareas se encolan y procesan de forma controlada

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "DEMO: Queue-Based Load Leveling" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$baseUrl = "http://localhost:5000"
$apiKey = "supersecreta123"

# Generar token si no existe
Write-Host "1. Generando token de acceso..." -ForegroundColor Yellow
try {
    $tokenResponse = Invoke-RestMethod -Uri "$baseUrl/tokens" -Method POST
    $apiKey = $tokenResponse.token
    Write-Host "   Token generado: $($apiKey.Substring(0, 20))..." -ForegroundColor Green
} catch {
    Write-Host "   Usando token por defecto" -ForegroundColor Yellow
}

# Asegurar que existe un usuario primero
Write-Host "`n2. Verificando/Creando usuario..." -ForegroundColor Yellow
$usuarioId = $null
try {
    $usuarios = Invoke-RestMethod -Uri "$baseUrl/usuarios" `
        -Headers @{"X-API-Key"=$apiKey} -ErrorAction SilentlyContinue
    if ($usuarios -and $usuarios.data -and $usuarios.data.Count -gt 0) {
        $usuarioId = $usuarios.data[0].id
        Write-Host "   [OK] Usuario existente encontrado (ID: $usuarioId)" -ForegroundColor Green
    } else {
        Write-Host "   Creando usuario de prueba..." -ForegroundColor Yellow
        $userBody = @{
            nombre = "Usuario Test Queue"
        } | ConvertTo-Json
        $usuario = Invoke-RestMethod -Uri "$baseUrl/usuarios" -Method POST `
            -Headers @{"X-API-Key"=$apiKey} -Body $userBody -ContentType "application/json"
        $usuarioId = $usuario.data.id
        Write-Host "   [OK] Usuario creado (ID: $usuarioId)" -ForegroundColor Green
    }
} catch {
    Write-Host "   [ERROR] Error al crear/verificar usuario: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Asegurar que existe un proyecto
Write-Host "`n3. Verificando/Creando proyecto..." -ForegroundColor Yellow
$proyectoId = 1
try {
    $proyecto = $null
    try {
        $proyecto = Invoke-RestMethod -Uri "$baseUrl/proyectos/$proyectoId" `
            -Headers @{"X-API-Key"=$apiKey} -ErrorAction Stop
        Write-Host "   [OK] Proyecto existente encontrado (ID: $proyectoId)" -ForegroundColor Green
    } catch {
        # Proyecto no existe, crear uno nuevo
        Write-Host "   Creando proyecto de prueba..." -ForegroundColor Yellow
        $body = @{
            nombre = "Proyecto Test Queue"
            usuario_id = $usuarioId
        } | ConvertTo-Json
        $proyectoCreado = Invoke-RestMethod -Uri "$baseUrl/proyectos" -Method POST `
            -Headers @{"X-API-Key"=$apiKey} -Body $body -ContentType "application/json" -ErrorAction Stop
        $proyectoId = $proyectoCreado.data.id
        Write-Host "   [OK] Proyecto creado (ID: $proyectoId)" -ForegroundColor Green
    }
} catch {
    Write-Host "   [ERROR] Error al verificar/crear proyecto: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "`n4. Encolando multiples tareas rapidamente..." -ForegroundColor Yellow
Write-Host "   (Simulando picos de carga)" -ForegroundColor Gray
Write-Host ""

$tareasEncoladas = 0
$tiemposEncolado = @()

# Encolar 5 tareas rápidamente
for ($i = 1; $i -le 5; $i++) {
    $tiempo = Measure-Command {
        try {
            $body = @{
                nombre = "Tarea Test Queue ${i}"
                proyecto_id = 1
            } | ConvertTo-Json
            
            $response = Invoke-RestMethod -Uri "$baseUrl/tareas" -Method POST `
                -Headers @{"X-API-Key"=$apiKey} `
                -Body $body -ContentType "application/json"
            
            $tareasEncoladas++
            Write-Host "   [OK] Tarea $i encolada en $([math]::Round($tiempo.TotalMilliseconds, 2)) ms" -ForegroundColor Green
        } catch {
            Write-Host "   [ERROR] Error al encolar tarea $i" -ForegroundColor Red
        }
    }
    $tiemposEncolado += $tiempo.TotalMilliseconds
}

$tiempoPromedioEncolado = [math]::Round(($tiemposEncolado | Measure-Object -Average).Average, 2)

Write-Host "`n5. Verificando tareas en cola (antes de procesar)..." -ForegroundColor Yellow
Write-Host "   Las tareas están en Redis esperando procesamiento" -ForegroundColor Gray

Write-Host "`n6. Procesando tareas de la cola..." -ForegroundColor Yellow
Write-Host "   (Esto tomará aproximadamente 2 segundos por tarea)" -ForegroundColor Gray
Write-Host ""

$tiempoProcesamiento = Measure-Command {
    try {
        $response = Invoke-RestMethod -Uri "$baseUrl/procesar_tareas" -Method POST `
            -Headers @{"X-API-Key"=$apiKey}
        
        $tareasProcesadas = $response.data.Count
        Write-Host "   [OK] $tareasProcesadas tareas procesadas exitosamente" -ForegroundColor Green
    } catch {
        Write-Host "   [ERROR] Error al procesar tareas" -ForegroundColor Red
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "RESULTADOS:" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Tareas encoladas: $tareasEncoladas" -ForegroundColor Yellow
Write-Host "Tiempo promedio de encolado: $tiempoPromedioEncolado ms" -ForegroundColor Yellow
Write-Host "Tiempo total de procesamiento: $([math]::Round($tiempoProcesamiento.TotalSeconds, 2)) segundos" -ForegroundColor Yellow
Write-Host "`nBENEFICIOS:" -ForegroundColor Green
Write-Host "- El cliente recibe respuesta inmediata al encolar (no espera procesamiento)" -ForegroundColor White
Write-Host "- El sistema procesa tareas de forma controlada (2 seg/tarea)" -ForegroundColor White
Write-Host "- Evita sobrecarga en picos de carga simultáneos" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan

