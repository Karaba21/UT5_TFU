# Script de prueba para demostrar el patrón Circuit Breaker
# Simula fallos y muestra cómo el circuito se abre y cierra

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "DEMO: Circuit Breaker (Disponibilidad)" -ForegroundColor Cyan
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

Write-Host "`n2. Simulando fallos para activar Circuit Breaker..." -ForegroundColor Yellow
Write-Host "   (Intentando crear proyecto con usuario_id inexistente)" -ForegroundColor Gray
Write-Host ""

$failCount = 0
$circuitOpened = $false

# Realizar 5 intentos fallidos
for ($i = 1; $i -le 5; $i++) {
    Write-Host "   Intento ${i}:" -ForegroundColor Cyan
    try {
        $body = @{
            nombre = "Proyecto Test Circuit Breaker"
            usuario_id = 99999  # Usuario que no existe
        } | ConvertTo-Json
        
        $response = Invoke-RestMethod -Uri "$baseUrl/proyectos" -Method POST `
            -Headers @{"X-API-Key"=$apiKey} `
            -Body $body -ContentType "application/json" `
            -ErrorAction Stop
        
        Write-Host "   [OK] Exito (no deberia pasar)" -ForegroundColor Green
    } catch {
        $errorResponse = $_.ErrorDetails.Message | ConvertFrom-Json
        $errorMsg = $errorResponse.error
        
        if ($errorMsg -like "*Circuito abierto*") {
            Write-Host "   [WARNING] Circuito ABIERTO - Rechazo inmediato" -ForegroundColor Red
            $circuitOpened = $true
        } else {
            Write-Host "   [ERROR] Error: $errorMsg" -ForegroundColor Yellow
            $failCount++
        }
    }
    
    Start-Sleep -Seconds 1
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "RESULTADOS:" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fallos registrados: $failCount" -ForegroundColor Yellow
if ($circuitOpened) {
    Write-Host "Estado del circuito: ABIERTO" -ForegroundColor Red
    Write-Host "`nEl circuito se abrió después de 3 fallos consecutivos" -ForegroundColor Yellow
    Write-Host "y ahora rechaza las peticiones inmediatamente para" -ForegroundColor Yellow
    Write-Host "proteger el sistema de sobrecarga." -ForegroundColor Yellow
} else {
    Write-Host "Estado del circuito: CERRADO" -ForegroundColor Green
    Write-Host "`nEl circuito se reiniciará automáticamente después de 10 segundos." -ForegroundColor Yellow
}
Write-Host "========================================" -ForegroundColor Cyan

Write-Host "`n3. Esperando 12 segundos para reinicio del circuito..." -ForegroundColor Yellow
Start-Sleep -Seconds 12

Write-Host "`n4. Intentando nuevamente después del timeout..." -ForegroundColor Yellow
try {
    $body = @{
        nombre = "Proyecto Test Después Timeout"
        usuario_id = 99999
    } | ConvertTo-Json
    
    $response = Invoke-RestMethod -Uri "$baseUrl/proyectos" -Method POST `
        -Headers @{"X-API-Key"=$apiKey} `
        -Body $body -ContentType "application/json" `
        -ErrorAction Stop
    
    Write-Host "   [OK] Circuito reiniciado, intentando nuevamente..." -ForegroundColor Green
} catch {
    $errorResponse = $_.ErrorDetails.Message | ConvertFrom-Json
    Write-Host "   [ERROR] Error: $($errorResponse.error)" -ForegroundColor Yellow
}

