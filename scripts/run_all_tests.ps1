# Script maestro que ejecuta todas las pruebas
# Demuestra las mejoras en atributos de calidad

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "DEMO COMPLETA: Mejoras en Atributos de Calidad" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar que el servicio esté corriendo
Write-Host "Verificando que el servicio este disponible..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:5000/health" -Method GET
    Write-Host "[OK] Servicio disponible" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host "[ERROR] El servicio no esta disponible" -ForegroundColor Red
    Write-Host "  Por favor ejecuta: docker compose up" -ForegroundColor Yellow
    exit 1
}

# Ejecutar todas las pruebas
$scripts = @(
    @{Name="Cache-Aside (Rendimiento)"; File="test_cache_aside.ps1"},
    @{Name="Circuit Breaker (Disponibilidad)"; File="test_circuit_breaker.ps1"},
    @{Name="Queue-Based Load Leveling (Rendimiento)"; File="test_queue_load_leveling.ps1"},
    @{Name="SOAP Endpoint (XML)"; File="test_soap_endpoint.ps1"}
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

foreach ($script in $scripts) {
    Write-Host "========================================" -ForegroundColor Magenta
    Write-Host "Ejecutando: $($script.Name)" -ForegroundColor Magenta
    Write-Host "========================================" -ForegroundColor Magenta
    Write-Host ""
    
    $scriptPath = Join-Path $scriptDir $script.File
    
    if (Test-Path $scriptPath) {
        & $scriptPath
        Write-Host ""
        if ($script -ne $scripts[-1]) {
            Write-Host "Esperando 3 segundos antes de la siguiente prueba..." -ForegroundColor Gray
            Start-Sleep -Seconds 3
            Write-Host ""
        }
    } else {
        Write-Host "[ERROR] Script no encontrado: $scriptPath" -ForegroundColor Red
    }
}

Write-Host "========================================" -ForegroundColor Green
Write-Host "TODAS LAS PRUEBAS COMPLETADAS" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Resumen de mejoras demostradas:" -ForegroundColor Cyan
Write-Host "  - Rendimiento: Cache-Aside, Queue-Based Load Leveling" -ForegroundColor White
Write-Host "  - Disponibilidad: Circuit Breaker" -ForegroundColor White
Write-Host "  - Integracion: SOAP/XML Endpoint" -ForegroundColor White
Write-Host ""

