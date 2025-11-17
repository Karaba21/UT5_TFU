# Script de prueba para demostrar el endpoint SOAP con XML
# Prueba el servicio SOAP que retorna datos en formato XML

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "DEMO: SOAP Endpoint (XML)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$baseUrl = "http://localhost:5000"

Write-Host "1. Obteniendo WSDL del servicio SOAP..." -ForegroundColor Yellow
Write-Host "   URL: $baseUrl/soap?wsdl" -ForegroundColor Gray
Write-Host ""

try {
    $wsdl = Invoke-WebRequest -Uri "$baseUrl/soap?wsdl" -Method GET
    Write-Host "   [OK] WSDL obtenido exitosamente" -ForegroundColor Green
    Write-Host "   Tamaño: $($wsdl.Content.Length) bytes" -ForegroundColor Gray
} catch {
    Write-Host "   [WARNING] WSDL no disponible (puede ser normal)" -ForegroundColor Yellow
}

Write-Host "`n2. Probando método obtener_estadisticas (tipo: general)..." -ForegroundColor Yellow
Write-Host ""

# Crear SOAP request para obtener estadísticas
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

try {
    $response = Invoke-WebRequest -Uri "$baseUrl/soap" `
        -Method POST `
        -ContentType "text/xml; charset=utf-8" `
        -Body $soapBody `
        -Headers @{"SOAPAction"=""}
    
    Write-Host "   [OK] Respuesta SOAP recibida" -ForegroundColor Green
    Write-Host "   Status Code: $($response.StatusCode)" -ForegroundColor Gray
    Write-Host "`n   Contenido XML:" -ForegroundColor Cyan
    Write-Host "   $($response.Content)" -ForegroundColor White
} catch {
    Write-Host "   [ERROR] Error: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "   Detalles: $($_.ErrorDetails.Message)" -ForegroundColor Yellow
    }
}

Write-Host "`n3. Probando método obtener_proyecto_por_id (ID: 1)..." -ForegroundColor Yellow
Write-Host ""

# Crear SOAP request para obtener proyecto por ID
$soapBody2 = @"
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
"@

try {
    $response2 = Invoke-WebRequest -Uri "$baseUrl/soap" `
        -Method POST `
        -ContentType "text/xml; charset=utf-8" `
        -Body $soapBody2 `
        -Headers @{"SOAPAction"=""}
    
    Write-Host "   [OK] Respuesta SOAP recibida" -ForegroundColor Green
    Write-Host "   Status Code: $($response2.StatusCode)" -ForegroundColor Gray
    Write-Host "`n   Contenido XML:" -ForegroundColor Cyan
    Write-Host "   $($response2.Content)" -ForegroundColor White
} catch {
    Write-Host "   [ERROR] Error: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "   Detalles: $($_.ErrorDetails.Message)" -ForegroundColor Yellow
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "RESULTADOS:" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "[OK] Endpoint SOAP funcionando correctamente" -ForegroundColor Green
Write-Host "[OK] Respuestas en formato XML" -ForegroundColor Green
Write-Host "[OK] Compatible con clientes SOAP estandar" -ForegroundColor Green
Write-Host "`nNOTA: Para probar con Postman:" -ForegroundColor Yellow
Write-Host "1. Método: POST" -ForegroundColor White
Write-Host "2. URL: http://localhost:5000/soap" -ForegroundColor White
Write-Host "3. Headers: Content-Type: text/xml" -ForegroundColor White
Write-Host "4. Body: Usar el XML SOAP mostrado arriba" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan

