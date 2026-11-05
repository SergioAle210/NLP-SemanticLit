# Control de acceso: gates de spoilers

Cubre el control de acceso del §5.8. La decisión de modelar el acceso como control de spoilers está en [ADR-0003](decisions/0003-access-control-as-spoiler-gates.md).

No requiere un servicio externo: el control se hace con **metadatos en cada chunk + un perfil en SQLite + validación de la salida**.

## Criterio de qué es spoiler

> Lo que dice el **manual oficial** es público por diseño: el desarrollador quería que el jugador lo supiera.
> Lo que **solo** aparece en la wiki se evalúa según su ubicación en el juego y el tipo de información.

- Que Ganon (Zelda) o el Jaquio (Ninja Gaiden) son los villanos es la **premisa**, no un spoiler.
- Sí son spoiler:
  - dónde y cómo se vence al jefe final;
  - lo que revelan las escenas posteriores a cada jefe;
  - el final.
- La lista concreta de entidades bloqueadas (G3) se arma leyendo el corpus y los manuales.

## Perfil

```json
{
  "user_id": "novato", "role": "player",
  "progress": {
    "zelda1": {"quest": "first", "completed_levels": [1], "current_level": 2},
    "ninja_gaiden_nes": {"current_stage": "1-2"}
  },
  "hint_level": 1
}
```

| Rol | Ve |
| --- | --- |
| `player` | Lo desbloqueado por su progreso en el juego activo, hasta su `hint_level` |
| `completionist` | Todo |
| `admin` | Todo, más ingesta y logs de auditoría |

Los perfiles de demo y su persistencia están en [ADR-0004](decisions/0004-sqlite-and-demo-profiles.md).

## Metadatos de acceso por chunk

Cada chunk lleva un objeto `location` ([ingestion/metadata.md](../ingestion/metadata.md)). En la fase 3 se agregan `entities`, `hint_tier`, `premise` y, en Ninja Gaiden, `segment` (`intro`, `stage`, `boss` u `outro`).

## Gates

| Gate | Zelda | Ninja Gaiden | Fase |
| --- | --- | --- | --- |
| **G1. Juego** | `chunk.game == juego activo` | Ídem | 3a |
| **G2. Ubicación** | `level ∈ completed ∪ {current}` o `level is None`; la `quest` coincide | `stage <= current_stage` según el orden de la config | 3a / 3b |
| **G2b. Narrativa intra-acto** | — | Un `outro` solo es visible si el acto ya se completó | 3b |
| **G3. Entidad de solución** | Diccionario corto (Silver Arrow, debilidad de Ganon, ubicación de Level-9, final) | Diccionario corto (jefes del Act 6, final) | 3c |
| **G4. Nivel de pista** | `hint_tier <= hint_level` | Ídem | 3a |

**Por qué hace falta G3:** algunos datos de solución están fuera de las páginas de la ubicación. Por ejemplo, la página de *Items* de Zelda dice que la Silver Arrow "is required to save Princess Zelda". G3 se aplica por fila en las páginas agregadas (Bosses, Items), para no bloquear la página entera. Los chunks con `premise = true` ignoran G3.

## Dónde se aplica (defensa en profundidad)

1. **Pre-filtro en la búsqueda** (`where` de Chroma y filtro equivalente en BM25): lo bloqueado nunca llega como candidato.
2. **Recheck de permisos** después del reranking: si algo pasó el pre-filtro por error, se descarta y se registra.
3. **Guardrail de salida:** las citas deben estar entre los chunks permitidos, la respuesta no debe nombrar entidades bloqueadas y `answer.game` debe ser el juego activo.

Cuando la respuesta existe pero está bloqueada, el sistema no la revela: devuelve `blocked_by_spoiler = true` y ofrece desbloquear, que es una acción con confirmación humana.

**Limitación aceptada:** el progreso lo declara el usuario. El objetivo es proteger del spoiler *accidental*.
