# Script de prueba para demostrar el patrón Cache-Aside
# Mide el tiempo de respuesta con y sin cache

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "DEMO: Cache-Aside Pattern (Rendimiento)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$baseUrl = "http://localhost:5000"
$apiKey = "supersecreta123"
$proyectoId = 1

# Generar token si no existe
Write-Host "1. Generando token de acceso..." -ForegroundColor Yellow
try {
    $tokenResponse = Invoke-RestMethod -Uri "$baseUrl/tokens" -Method POST
    $apiKey = $tokenResponse.token
    Write-Host "   [OK] Token generado: $($apiKey.Substring(0, 20))..." -ForegroundColor Green
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
            nombre = "Usuario Test Cache"
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
            nombre = "Proyecto Test Cache"
            usuario_id = $usuarioId
        } | ConvertTo-Json
        $proyectoCreado = Invoke-RestMethod -Uri "$baseUrl/proyectos" -Method POST `
            -Headers @{"X-API-Key"=$apiKey} -Body $body -ContentType "application/json" -ErrorAction Stop
        $proyectoId = $proyectoCreado.data.id
        Write-Host "   [OK] Proyecto creado con ID: $proyectoId" -ForegroundColor Green
    }
} catch {
    Write-Host "   [ERROR] Error al verificar/crear proyecto: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "`n4. Realizando pruebas de rendimiento..." -ForegroundColor Yellow
Write-Host ""

# Primera llamada (Cache Miss - debe leer del archivo)
Write-Host "   Primera llamada (Cache MISS - lee del archivo):" -ForegroundColor Cyan
$time1 = Measure-Command {
    $response1 = Invoke-RestMethod -Uri "$baseUrl/proyectos/$proyectoId" `
        -Headers @{"X-API-Key"=$apiKey}
}
Write-Host "   Tiempo: $([math]::Round($time1.TotalMilliseconds, 2)) ms" -ForegroundColor White
Write-Host "   Proyecto: $($response1.nombre)" -ForegroundColor Gray

# Segunda llamada (Cache Hit - debe leer de Redis)
Start-Sleep -Seconds 1
Write-Host "`n   Segunda llamada (Cache HIT - lee de Redis):" -ForegroundColor Cyan
$time2 = Measure-Command {
    $response2 = Invoke-RestMethod -Uri "$baseUrl/proyectos/$proyectoId" `
        -Headers @{"X-API-Key"=$apiKey}
}
Write-Host "   Tiempo: $([math]::Round($time2.TotalMilliseconds, 2)) ms" -ForegroundColor White
Write-Host "   Proyecto: $($response2.nombre)" -ForegroundColor Gray

# Tercera llamada (Cache Hit)
Start-Sleep -Seconds 1
Write-Host "`n   Tercera llamada (Cache HIT - lee de Redis):" -ForegroundColor Cyan
$time3 = Measure-Command {
    $response3 = Invoke-RestMethod -Uri "$baseUrl/proyectos/$proyectoId" `
        -Headers @{"X-API-Key"=$apiKey}
}
Write-Host "   Tiempo: $([math]::Round($time3.TotalMilliseconds, 2)) ms" -ForegroundColor White

# Calcular mejora
$mejora = [math]::Round((($time1.TotalMilliseconds - $time2.TotalMilliseconds) / $time1.TotalMilliseconds) * 100, 2)
$promedioCache = [math]::Round(($time2.TotalMilliseconds + $time3.TotalMilliseconds) / 2, 2)

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "RESULTADOS:" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Tiempo sin cache (archivo): $([math]::Round($time1.TotalMilliseconds, 2)) ms" -ForegroundColor Yellow
Write-Host "Tiempo con cache (Redis):   $promedioCache ms (promedio)" -ForegroundColor Green
Write-Host "Mejora de rendimiento:     $mejora %" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan

