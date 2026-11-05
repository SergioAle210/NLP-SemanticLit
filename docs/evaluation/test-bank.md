# Banco de pruebas

Cubre el §8 de [course/instructions.md](../course/instructions.md). Los casos se escriben en inglés ([ADR-0001](../architecture/decisions/0001-english-first.md)), leyendo los chunks reales.

## Esquema (`eval/cases.jsonl`)

Campos obligatorios del curso, más los propios:

```json
{
  "id": "zelda_direct_001",
  "question": "Which button swings the sword?",
  "expected_behavior": "Answers 'A', citing the Controls page",
  "expected_sources": ["The Legend of Zelda/Controls"],
  "expected_pages": [0],
  "answerable": true,
  "risk_level": "low",
  "category": "direct",
  "game": "zelda1",
  "profile": "novato",
  "lang": "en"
}
```

- `risk_level`: `low` | `medium` | `high` (spoiler) | `critical` (acción o seguridad).
- `profile`: uno de los perfiles de demo ([ADR-0004](../architecture/decisions/0004-sqlite-and-demo-profiles.md)).

## Distribución (borrador)

| Categoría | # | Zelda | Ninja Gaiden |
| --- | ---: | --- | --- |
| Directas | 5 | "Which button swings the sword?" · "What item is in Level-3 (first quest)?" · "How much does the Blue Candle cost?" | "Which button makes Ryu jump?" · "How many spirit points does the Windmill Star cost?" |
| Paráfrasis | 3 | "How do I get across water?" (Raft / Ladder) | "How can I climb walls?" (wall jump) |
| Identificadores exactos | 3 | "What does the old man in Level-4 say?" · "What is on the dock at D-4?" | "What happens in Stage 4-3?" · "Is *Shadow Warriors* the same game?" |
| Compuestas | 3 | "Where do I buy the Blue Candle and how much is it?" | "Which weapon works best against Bomberhead and how much spirit does it use?" |
| Ambiguas | 2 | "How do I beat Gleeok?" (2, 3 o 4 cabezas) | "How do I beat the Act 6 boss?" (tres jefes) |
| Sin respuesta | 2 | "How do I use the Hookshot?" (no existe en Zelda 1) | 🔶 Se elige tras leer el corpus |
| Versión / vigencia | 2 | "Where is the Ladder?" en Q1 frente a Q2 | — |
| Multijuego (fase 3b) | 2 | "How does the boomerang work?" con NG activo · pregunta de NG con Zelda activo | |
| Herramientas | 5 | Nominal · parámetro fuera de rango (`level=15`) · desbloqueo sin confirmar · API caída | Herramienta errónea: "Which levels can I do now?" |
| Seguridad / spoilers | ≥ 10 | Ver [security/controls.md](../security/controls.md) | |

**Orden de escritura:** en la fase 2, los 20 casos base de Zelda; en la 3b, los de Ninja Gaiden y los multijuego; en la 3d (opcional), de 8 a 10 casos traducidos al español.
