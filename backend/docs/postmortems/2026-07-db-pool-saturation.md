---
title: "Saturación del pool de conexiones - 2026-07-15"
applies_to: database
severity: critical
date: "2026-07-15"
duration: "45 minutos"
impact: "100% de los usuarios afectados, pérdida de transacciones"
root_cause: "Aumento de max_connections sin ajustar el pool de la aplicación"
---

## Resumen

El 15 de julio de 2026, a las 14:30 UTC, se detectaron errores masivos de timeout en la base de datos principal. El pool de conexiones estaba saturado al 100%, causando que todas las consultas SQL fallaran. La duración total del incidente fue de 45 minutos.

## Cronología

- 14:20 - Despliegue de cambio en `max_connections` de 100 a 200.
- 14:30 - Primeras alertas de timeout en monitoreo.
- 14:35 - Equipo de DBA notificado, inicia investigación.
- 14:45 - Se identifica que el pool de la aplicación sigue configurado con 50 conexiones.
- 15:00 - Se ajusta el pool de la aplicación a 100 conexiones.
- 15:15 - Servicio recuperado, errores eliminados.

## Causa raíz

El cambio de `max_connections` en PostgreSQL no fue acompañado de un ajuste en el pool de conexiones de la aplicación. Cuando múltiples instancias de la aplicación intentaron usar más conexiones de las disponibles en su pool, se agotaron todas las conexiones disponibles en el servidor.

## Lecciones aprendidas

1. Los cambios de infraestructura deben coordinarse con los cambios de aplicación.
2. Es necesario tener alertas de saturación de pool de conexiones.
3. El connection pooling debe ser revisado periódicamente.

## Acciones correctivas

- [ ] Implementar alertas de pool de conexiones al 80%
- [ ] Revisar configuración de pool en todos los servicios
- [ ] Agregar documentación sobre coordinación de cambios
