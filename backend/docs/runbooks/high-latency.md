---
title: "Alta latencia en servicios backend"
applies_to: api-gateway
severity: medium
symptoms: |
  Tiempo de respuesta p95 superior a 2 segundos,
  usuarios reportan lentitud, timeouts intermitentes,
  métricas de latencia elevadas en dashboards.
---

## Diagnóstico

1. Identificar qué endpoint tiene mayor latencia:
   ```bash
   # Revisar métricas de latencia por ruta
   curl -s http://prometheus:9090/api/v1/query?query=histogram_quantile(0.95,rate(http_request_duration_seconds_bucket[5m]))
   ```
2. Revisar si la latencia es homogénea o concentrada en un servicio.
3. Verificar si hay queries lentas en la base de datos:
   ```sql
   SELECT query, mean_time, calls
   FROM pg_stat_statements
   ORDER BY mean_time DESC
   LIMIT 10;
   ```

## Solución inmediata

1. Si es una query lenta, crear índices faltantes o optimizar.
2. Si es un servicio específico, escalar réplicas de ese servicio.
3. Si es general, revisar infraestructura (CPU, memoria, disco).

## Prevención

- Implementar APM (Application Performance Monitoring).
- Establecer SLOs de latencia por endpoint.
- Revisar queries lentas periódicamente.
- Monitorear uso de CPU y memoria por servicio.
