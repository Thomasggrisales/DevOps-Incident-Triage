---
title: "Errores 5xx en API Gateway"
applies_to: api-gateway
severity: high
symptoms: |
  Respuestas HTTP 502, 503 o 504 desde el API Gateway,
  usuarios reportan que la aplicación no responde,
  tasa de errores superior al 5% en métricas de entrada.
---

## Diagnóstico

1. Revisar logs del API Gateway para identificar el patrón de errores:
   - 502 (Bad Gateway): Backend no responde o se desconectó.
   - 503 (Service Unavailable): Backend sobrecargado o en mantenimiento.
   - 504 (Gateway Timeout): Backend responde demasiado lento.
2. Verificar la salud de los servicios backend:
   ```bash
   curl -s http://backend:8000/health
   ```
3. Revisar métricas de latencia del backend:
   - Si p95 > 5s, hay un problema de rendimiento en el backend.
   - Si p95 normal pero 502, el backend está caído.

## Solución inmediata

1. Si el backend está caído, reiniciarlo:
   ```bash
   docker restart backend
   ```
2. Si hay alta latencia, escalar instancias del backend:
   ```bash
   docker-compose up -d --scale backend=3
   ```
3. Si el problema es de timeout, ajustar `proxy_read_timeout` en nginx del API Gateway.

## Prevención

- Configurar health checks en el load balancer.
- Implementar circuit breaker en el API Gateway.
- Monitorear la tasa de errores y latencia del backend.
- Revisar que los servicios backend tengan recursos suficientes (CPU, memoria).
