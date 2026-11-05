# ADR-0003: El control de acceso se modela como gates de spoilers

**Estado:** aceptado (2026-11-04)

## Contexto

El curso exige control de acceso a documentos y pruebas de evasión de permisos (§5.8 y §10). En un corpus público no hay documentos confidenciales, pero sí hay información que el usuario **no debería ver todavía**: soluciones, historia y finales posteriores a su progreso.

## Decisión

- El acceso se decide por **progreso del jugador + rol**, con cuatro gates: juego, ubicación, entidad de solución y nivel de pista. El detalle está en [access-control.md](../access-control.md).
- Criterio de qué es spoiler: **lo que dice el manual oficial es público por diseño**.
- Se aplica en tres puntos: pre-filtro de la búsqueda, recheck después del reranking y guardrail de salida.
- El modelo de progreso depende del juego:
  - Zelda, **no lineal:** conjunto de mazmorras completadas + quest.
  - Ninja Gaiden, **lineal:** la etapa actual.

## Alternativas consideradas

- **Progreso como "mazmorra más alta completada".** Falla en Zelda, que no es lineal: alguien que completó los Levels 3 y 8 vería spoilers del 1.
- **Un servicio de permisos aparte (p. ej. Postgres con tablas de ACL).** Es excesivo: los metadatos en el índice resuelven el filtro de forma más simple y verificable.
- **Bloquear por nombre de entidad** (p. ej. "Ganon"). Bloquearía la premisa del juego y degradaría la recuperación sin proteger nada.

## Consecuencias

- Las pruebas de evasión de permisos se vuelven concretas y medibles: spoilers filtrados (meta: 0).
- El progreso lo declara el usuario. Se protege del spoiler accidental, no del usuario que lo busca a propósito.
- La ingesta debe producir metadatos de ubicación confiables ([ingestion/metadata.md](../../ingestion/metadata.md)).
