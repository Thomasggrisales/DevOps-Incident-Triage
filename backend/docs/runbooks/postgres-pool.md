---
title: "Saturación del pool de conexiones PostgreSQL"
applies_to: database
severity: high
symptoms: |
  Errores de timeout en consultas SQL, pool de conexiones agotado,
  mensajes "FATAL: too many connections" en logs de PostgreSQL,
  latencia elevada en endpoints que dependen de la base de datos.
---

## Diagnóstico

1. Verificar el número de conexiones activas:
   ```sql
   SELECT count(*), state FROM pg_stat_activity GROUP BY state;
   ```
2. Revisar `max_connections` en `postgresql.conf`:
   ```sql
   SHOW max_connections;
   ```
3. Identificar clientes que mantienen conexiones abiertas innecesariamente:
   ```sql
   SELECT pid, state, query_start, state_change, query
   FROM pg_stat_activity
   WHERE state != 'idle'
   ORDER BY state_change;
   ```

## Solución inmediata

1. Terminar conexiones idle que llevan más de 10 minutos:
   ```sql
   SELECT pg_terminate_backend(pid)
   FROM pg_stat_activity
   WHERE state = 'idle'
   AND state_change < now() - interval '10 minutes';
   ```
2. Si el problema persiste, reiniciar el servicio de pool de conexiones de la aplicación.

## Prevención

- Configurar `idle_in_transaction_session_timeout` en PostgreSQL.
- Implementar connection pooling en la aplicación (PgBouncer o pool nativo).
- Monitorear el uso de conexiones con alertas en `pg_stat_activity`.
- Revisar que las queries no mantengan transacciones abiertas innecesariamente.
