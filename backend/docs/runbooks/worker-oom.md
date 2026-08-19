---
title: "OOM / crash loop en workers"
applies_to: worker
severity: critical
symptoms: |
  Procesos terminados con OOMKilled, crash loop en Kubernetes,
  uso de memoria superior al 90%, jobs de cola fallando repetidamente.
---

## Diagnóstico

1. Verificar métricas de memoria del worker:
   - RSS (Resident Set Size) vs límite configurado.
   - Heap usage en dashboards de monitoreo.
2. Revisar logs del worker para identificar el patrón de crash:
   - ¿Ocurre después de procesar un tipo específico de job?
   - ¿Ocurre gradualmente (fuga) o de golpe (pico)?
3. Si hay heap dump disponible, analizar los objetos que más memoria consumen.

## Solución inmediata

1. Reiniciar el worker afectado:
   ```bash
   kubectl rollout restart deployment/worker
   ```
2. Aumentar temporalmente el límite de memoria:
   ```yaml
   resources:
     limits:
       memory: "2Gi"  #era 1Gi
   ```
3. Reducir la cola de jobs pendientes para evitar acumulación.

## Prevención

- Configurar alertas de memoria al 80% del límite.
- Implementar heap dumps automático antes del OOM.
- Revisar fugas de memoria en el código del worker.
- Ajustar `--max-old-space-size` en Node.js o equivalentes.
