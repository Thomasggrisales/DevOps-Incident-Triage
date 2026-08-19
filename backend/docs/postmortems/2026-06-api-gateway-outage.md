---
title: "Caída del API Gateway - 2026-06-20"
applies_to: api-gateway
severity: critical
date: "2026-06-20"
duration: "2 horas"
impact: "Todos los usuarios afectados, aplicación completamente inaccesible"
root_cause: "Fuga de memoria en el servicio de autenticación que consumió todos los recursos del nodo"
---

## Resumen

El 20 de junio de 2026, a las 09:00 UTC, el API Gateway comenzó a retornar errores 502 para todas las peticiones. La aplicación estaba completamente inaccesible durante 2 horas. La causa fue una fuga de memoria en el servicio de autenticación que consumió todos los recursos del nodo, causando la caída del API Gateway.

## Cronología

- 08:30 - Despliegue de nueva versión de auth-service.
- 08:45 - Métricas de memoria de auth-service comienzan a subir gradualmente.
- 09:00 - API Gateway comienza a retornar 502.
- 09:10 - Alertas de OOM en el nodo de auth-service.
- 09:15 - auth-service cae, API Gateway no puede autenticar.
- 09:30 - Equipo de plataforma inicia investigación.
- 10:00 - Se identifica la fuga de memoria en auth-service.
- 10:30 - Se revierte el despliegue de auth-service.
- 11:00 - Servicio completamente recuperado.

## Causa raíz

La nueva versión de auth-service tenía una fuga de memoria en el manejo de refresh tokens. Cada petición de refresh incrementaba el uso de memoria en ~1MB, y después de ~4 horas el proceso consumió toda la memoria disponible, causando OOM y la caída del servicio.

## Lecciones aprendidas

1. Las fugas de memoria deben ser detectadas en staging antes de producción.
2. Es necesario tener alertas de memoria por servicio.
3. El API Gateway debe degradarse graciosamente cuando un servicio backend falla.

## Acciones correctivas

- [ ] Implementar pruebas de estrés en staging antes de producción.
- [ ] Agregar alertas de memoria al 80% del límite.
- [ ] Implementar circuit breaker en el API Gateway.
- [ ] Revisar el proceso de despliegue para incluir validación de memoria.
