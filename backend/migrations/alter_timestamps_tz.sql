-- Migración de zona horaria: las columnas de tiempo ahora usan TIMESTAMPTZ.
-- Los valores existentes se guardaron como UTC naive, por eso se convierten
-- explícitamente AT TIME ZONE 'UTC' para conservar el instante correcto.

ALTER TABLE users
  ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC';

ALTER TABLE incidents
  ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC';

ALTER TABLE status_history
  ALTER COLUMN changed_at TYPE TIMESTAMPTZ USING changed_at AT TIME ZONE 'UTC';

ALTER TABLE agent_sessions
  ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
  ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC';
