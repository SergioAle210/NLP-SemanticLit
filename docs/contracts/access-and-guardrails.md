# Contratos de control de acceso y guardrails

Implementación: [src/gamerag/guardrails/base.py](../../src/gamerag/guardrails/base.py) y [src/gamerag/progress/models.py](../../src/gamerag/progress/models.py). El diseño de los gates está en [architecture/access-control.md](../architecture/access-control.md).

## Perfil

```python
class Profile(BaseModel):
    user_id: str
    role: Literal["player", "completionist", "admin"]
    progress: dict[str, LevelSetProgress | LinearStageProgress]   # game_id -> progreso
    hint_level: int  # 1..3
    unrestricted: bool  # propiedad: True para completionist y admin

LevelSetProgress(quest="first", completed_levels=[1, 2], current_level=3)   # Zelda
LinearStageProgress(current_stage="2-3")                                     # Ninja Gaiden
```

- **Perfiles sembrados:** [data/seed/profiles.json](../../data/seed/profiles.json) (`novato`, `intermedio`, `segunda_vuelta`, `completionist`, `admin`).
- `validate_profile` verifica que el progreso sea coherente con la config del juego (quest, niveles y etapas válidos).

## Filtros de acceso (gates)

```python
class AccessFilter(Protocol):
    name: str
    def allows(self, chunk: Chunk, profile: Profile, game: str) -> bool: ...
```

- El pipeline aplica **todos** los filtros, en orden, a cada candidato (se recuperan 50). El primero que bloquea queda en la traza (`CandidateTrace.blocked_by`). Los permitidos, hasta `top_k`, pasan al generador.
- Si **todos** los candidatos quedan bloqueados por un gate distinto de G1, el pipeline responde `blocked_by_spoiler = True` sin revelar contenido.
- **Metadatos disponibles en el chunk:** `chunk.game`, `chunk.location.{quest, level, act, stage}`, `chunk.source` y `chunk.section`. Los de la fase 3 (`entities`, `hint_tier`, `premise`, `segment`) se agregan en la ingesta ([ingestion/metadata.md](../ingestion/metadata.md)).

| Gate | Clase | Estado | Regla ([access-control.md](../architecture/access-control.md)) |
| --- | --- | --- | --- |
| G1 | `GameFilter` | ✅ | `chunk.game == game` |
| G2 | — | ⬜ | Zelda: `level ∈ completed ∪ {current}` o `level is None`, y la `quest` coincide. NG: `stage <= current_stage` según `GameConfig.stage_index` |
| G2b | — | ⬜ | NG: un `outro` solo es visible si el acto ya se completó (requiere el metadato `segment`) |
| G3 | — | ⬜ | Entidades de solución bloqueadas (requiere el metadato `entities`) |
| G4 | — | ⬜ | `hint_tier <= profile.hint_level` (requiere el metadato `hint_tier`) |

En [tests/test_contracts.py](../../tests/test_contracts.py) hay un G2 simplificado (`_LevelGate`) que muestra el patrón: respetar `profile.unrestricted` y dejar pasar el contenido general (`level is None`).

**Pre-filtro (optimización opcional):** el índice semántico ya guarda la ubicación en Chroma y acepta `where` ([retrieval/semantic.md](../retrieval/semantic.md)). El filtro posterior (`allows`) es el obligatorio. El pre-filtro solo reduce el trabajo, y no reemplaza al posterior (defensa en profundidad).

## Guardrails de entrada y salida

```python
@dataclass(frozen=True)
class GuardResult:
    allowed: bool
    reason: str = ""          # queda en la traza
    flags: list[str] = []     # señales no bloqueantes (p. ej. "pii_redacted")

class InputGuard(Protocol):
    name: str
    def check(self, question: str, profile: Profile) -> GuardResult: ...

class OutputGuard(Protocol):
    name: str
    def check(self, answer: Answer, context: list[Hit], profile: Profile) -> GuardResult: ...
```

| Guard | Clase | Estado | Qué hace |
| --- | --- | --- | --- |
| Entrada básica | `BasicInputGuard` | ✅ | Rechaza preguntas vacías o de más de 500 caracteres |
| Inyección | — | ⬜ | Heurísticas y regex ("ignore previous instructions", "system prompt"…) |
| PII | — | ⬜ | Detectar o redactar correos, teléfonos y nombres antes de buscar y de registrar |
| Citas | `CitationGuard` | ✅ | Las citas deben estar en el contexto y la respuesta debe ser del juego activo |
| Entidades bloqueadas | — | ⬜ | La respuesta no nombra entidades bloqueadas para el perfil (G3 en la salida) |

- Un `InputGuard` que bloquea hace que el pipeline responda con abstención (`outcome = rejected_input`) **sin buscar**.
- Un `OutputGuard` que bloquea reemplaza la respuesta por una abstención con `needs_human_review = True` (`outcome = rejected_output`).

Los casos adversarios para medir todo esto están en [security/controls.md](../security/controls.md).
