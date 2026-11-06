# Banco de pruebas

Cubre el §8 de [course/instructions.md](../course/instructions.md). Archivo: [eval/cases.jsonl](../../eval/cases.jsonl). Los casos se escriben en inglés ([ADR-0001](../architecture/decisions/0001-english-first.md)), leyendo el corpus limpio.

## Esquema

Campos obligatorios del curso, más los propios:

```json
{
  "id": "zelda_exact_01",
  "question": "What does the old man in Level-4 of the first quest say?",
  "expected_behavior": "Quotes the hint 'Walk into the waterfall.'",
  "expected_sources": ["The Legend of Zelda/Underworld/Quest 1/Dungeon 4"],
  "expected_pages": [3],
  "answerable": true,
  "risk_level": "low",
  "category": "exact_id",
  "game": "zelda1",
  "profile": "completionist",
  "lang": "en",
  "evidence": [["Walk into the waterfall."]]
}
```

| Campo | Significado |
| --- | --- |
| `expected_sources` / `expected_pages` | Páginas de la wiki y el índice de sección donde aparece la evidencia (alineados por posición) |
| `evidence` | Partes de la respuesta, cada una con alternativas literales del corpus. Define la relevancia ([ADR-0008](../architecture/decisions/0008-relevance-by-evidence-text.md)) |
| `risk_level` | `low` · `medium` (ambiguas, versión, sin respuesta) · `high` (spoiler) · `critical` (acción o seguridad) |
| `author` | `assistant` (escrita conociendo el corpus) o `team` (escrita por el equipo sin verlo: conjunto independiente) |
| `profile` | Perfil de demo con el que se hace la pregunta. Los casos de recuperación usan `completionist` para que los gates no oculten la evidencia; los de spoilers usarán perfiles `player` |

Implementación: [src/gamerag/evaluation/cases.py](../../src/gamerag/evaluation/cases.py).

## Casos actuales: Zelda (39)

| Categoría | # | Ejemplos |
| --- | ---: | --- |
| Directas | 5 | "Which button swings the sword?" · "How much does the Blue Candle cost?" |
| Paráfrasis | 3 | "How can I sail across the sea?" (Raft) · "How can I win cash by gambling?" (Money Making Game) |
| Identificadores exactos | 3 | "What does the old man in Level-4 of the first quest say?" · "What can I buy at D-4 in section 2?" · "register my name as ZELDA" |
| Compuestas | 3 | "Where can I buy the Blue Candle, and what can it be used for?" |
| Ambiguas | 2 | "How do I beat the dragon boss?" (Aquamentus y Gleeok son dragones) · "How do I defeat Gleeok?" (2, 3 o 4 cabezas) |
| Sin respuesta | 2 | "How do I use the Hookshot?" · "Can I ride a horse in this game?" |
| Versión | 2 | "In the first/second quest, which dungeon has the Ladder?" (Level-4 frente a Level-6) |
| **Robustez** (propia) | 19 | "How can I attack?" · "can i blow up walls with **bombz**?" · "how do i use my secondary item" · las 9 del equipo (abajo) · "how do i save my game?" (lenguaje de un jugador real: coloquial, vago o con errores) |

**Conjunto del equipo** (`author: team`): 9 preguntas escritas por un integrante como jugador, **sin ver el corpus ni el sistema**: "how do i atack?", "how can i heal?", "where do i find money?", "what is the best weapon?", "how do i open a locked door?", "what do i do if ig im stuck" (sin respuesta: debe abstenerse), "how do i defeat the dragon?", "where do i get bombs?", "how do i unlock the bow?". Se reportan aparte (`team`) porque miden si una mejora **generaliza** más allá de las preguntas escritas conociendo el corpus.

**Integridad garantizada por tests** ([tests/test_retrieval.py](../../tests/test_retrieval.py)):
- la distribución por categoría coincide con la del curso;
- cada (fuente, sección) esperada contiene la evidencia;
- cada caso con respuesta tiene al menos un chunk relevante;
- los casos sin respuesta no tienen texto de apoyo en el corpus.

**Revisión pendiente:** los casos son un borrador redactado a partir del corpus. Conviene que cada integrante revise y proponga casos propios, para reducir el sesgo hacia lo que el sistema ya encuentra.

## Pendientes

| Categoría | Fase | Ejemplos previstos |
| --- | --- | --- |
| Ninja Gaiden (20 base) | 3b | "Which button makes Ryu jump?" · "How many spirit points does the Windmill Star cost?" · "How do I beat the Act 6 boss?" |
| Multijuego | 3b | "How does the boomerang work?" con NG activo |
| Herramientas | 3a | Nominal · parámetro fuera de rango · desbloqueo sin confirmar · API caída · herramienta errónea |
| Seguridad / spoilers | 5 | Ver [security/controls.md](../security/controls.md) |
| Español | 3d | De 8 a 10 casos traducidos |
