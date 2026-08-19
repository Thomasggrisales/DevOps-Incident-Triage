---
title: "Cache Redis lenta o evicción agresiva"
applies_to: cache
severity: medium
symptoms: |
  Latencia elevada en endpoints que dependen de caché,
  tasa de evicciones alta en métricas de Redis,
  errores de timeout en conexiones a Redis.
---

## Diagnóstico

1. Revisar métricas de Redis:
   - `evicted_keys`: claves evictadas por política de memoria.
   - `used_memory` vs `maxmemory`: uso de memoria.
   - `connected_clients`: conexiones activas.
2. Revisar la política de evicción:
   ```bash
   redis-cli CONFIG GET maxmemory-policy
   ```
3. Identificar claves que consumen más memoria:
   ```bash
   redis-cli --bigkeys
   ```

## Solución inmediata

1. Aumentar `maxmemory` si hay espacio disponible:
   ```bash
   redis-cli CONFIG SET maxmemory 4gb  # era 2gb
   ```
2. Cambiar política de evicción a `allkeys-lru` si se está usando `volatile-lru`:
   ```bash
   redis-cli CONFIG SET maxmemory-policy allkeys-lru
   ```
3. Pre-cargar claves críticas después de limpiar caché.

## Prevención

- Monitorear `evicted_keys` y alertar si supera umbral.
- Revisar que las claves tengan TTL apropiado.
- Implementar caché de nivel 2 (local) para claves críticas.
- Revisar patrones de acceso para identificar claves frías.
