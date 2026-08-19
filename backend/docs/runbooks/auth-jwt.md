---
title: "Fallos de autenticación JWT"
applies_to: auth-service
severity: medium
symptoms: |
  Usuarios no pueden iniciar sesión, tokens rechazados con 401,
  errores "jwt_validation_failed" en logs del gateway,
  refresh tokens revocados inesperadamente.
---

## Diagnóstico

1. Revisar logs de auth-service para identificar el tipo de error:
   - Token expirado: relogin normal.
   - Token inválido: posible rotación de clave JWT.
   - Refresh token revocado: revisar si hubo logout masivo.
2. Verificar que la clave JWT no haya cambiado:
   ```bash
   # Comparar la clave actual con la usada para firmar tokens
   echo $JWT_SECRET_KEY
   ```
3. Revisar si hay múltiples instancias de auth-service con claves diferentes.

## Solución inmediata

1. Si la clave JWT cambió, coordinar rollout de todos los servicios que validan tokens.
2. Si hay refresh tokens revocados, limpiar la tabla de tokens en la base de datos.
3. Si el problema es de expiración, revisar la configuración de TTL.

## Prevención

- Usar rotación gradual de claves JWT con JWKS.
- Implementar refresh token rotation en el cliente.
- Monitorear la tasa de errores 401 en el gateway.
- Mantener un período de gracia al rotar claves.
