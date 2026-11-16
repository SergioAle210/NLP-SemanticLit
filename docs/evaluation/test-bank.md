# Bancos de pruebas y procedencia

Los bancos cumplen el esquema mínimo del §8 del curso y añaden atributos para reproducir recuperación, perfiles y expectativas. El conjunto principal está en [eval/cases.jsonl](../../eval/cases.jsonl). Su idioma principal es inglés; disponer de embeddings multilingües no acredita una evaluación equivalente en español.

## Esquema

```json
{
  "id": "document_revision_1",
  "question": "Where is the training key stored?",
  "expected_behavior": "Answer shelf A and cite synthetic revision 101.",
  "expected_sources": ["Revision Fixture/Training key"],
  "expected_pages": [0],
  "answerable": true,
  "risk_level": "medium",
  "category": "version",
  "game": "revision_fixture",
  "profile": "fixture",
  "evidence": [["shelf A"]],
  "author": "assistant"
}
```

El ejemplo corresponde a la revisión documental sintética y no a un videojuego real. Los campos obligatorios son `id`, `question`, `expected_behavior`, `expected_sources`, `expected_pages`, `answerable` y `risk_level`.

| Extensión | Significado |
| --- | --- |
| `category`, `game`, `lang` | Agrupación y dominio |
| `profile` | Perfil con el que se realiza la consulta |
| `evidence` | Partes esperadas, cada una con alternativas literales |
| `author` | Etiqueta de procedencia registrada; no prueba revisión humana |
| `expect`, `fault` en herramientas | Comportamiento estructurado y fallo inyectado |
| Patrones de oráculo | Expresiones permitidas y prohibidas declaradas antes de ejecutar |

`expected_pages` usa ordinales de sección de wiki, no páginas impresas. El identificador de revisión está en el documento y su evidencia; la quest del juego se modela por separado.

## Banco principal: 54 casos

| Categoría | Zelda | Ninja Gaiden | Total | Mínimo del curso |
| --- | ---: | ---: | ---: | ---: |
| Directas | 5 | 3 | 8 | 5 |
| Paráfrasis | 3 | 2 | 5 | 3 |
| Identificadores exactos | 3 | 2 | 5 | 3 |
| Compuestas | 3 | 1 | 4 | 3 |
| Ambiguas | 2 | 0 | 2 | 2 |
| Sin respuesta, categoría explícita | 2 | 2 | 4 | 2 |
| Variante del dominio | 2 | 1 | 3 | Revisiones documentales: ver banco específico |
| Robustez | 19 | 4 | 23 | Adicional |
| **Total** | **39** | **15** | **54** | **20** |

El caso `zelda_team_06`, de robustez, también tiene `answerable: false`. Por ello el banco contiene cinco casos no respondibles y 49 respondibles, aunque la categoría explícita «sin respuesta» tenga cuatro.

Los casos de Ladder en First/Second Quest prueban una variante de contenido del juego; el nombre europeo de Ninja Gaiden prueba denominación regional. No sustituyen las dos pruebas de actualización documental del banco de revisiones.

## Procedencia y contaminación experimental

El campo `author: team` identifica nueve preguntas del banco principal con una etiqueta heredada del desarrollo. El registro histórico las describió como aportes de un integrante sin consultar el corpus. Esa etiqueta no acredita revisión humana del juez, independencia permanente ni una auditoría de cómo se redactó cada pregunta.

Las preguntas del equipo y las de `author: assistant` se utilizaron para diagnosticar y ajustar glosarios o reglas. Después de inspeccionarlas no deben presentarse como un conjunto nuevo no visto. Conservamos la etiqueta para reproducir particiones históricas, con su limitación.

Los quince casos de Ninja Gaiden están etiquetados `assistant`. Algunos términos del banco, como errores ortográficos y nombres de mecánicas, ya habían aparecido en exploraciones. La generación sintética y la curaduría de corpus pueden producir ejemplos útiles, pero requieren una evaluación nueva para estimar generalización.

## Bancos complementarios

| Archivo | Casos o propósito | Interpretación |
| --- | --- | --- |
| [cases_hard.jsonl](../../eval/cases_hard.jsonl) | 21; preguntas difíciles | 18 respondibles y 3 no respondibles |
| [cases_extra.jsonl](../../eval/cases_extra.jsonl) | 61; fuentes adicionales | Todos respondibles; no estima sensibilidad de abstención |
| [cases_extra_franchise.jsonl](../../eval/cases_extra_franchise.jsonl) | 23; alcance de franquicia | Separado del corpus secundario predeterminado |
| [cases_tools.jsonl](../../eval/cases_tools.jsonl) | 26; herramientas | Banco de desarrollo después de corregir reglas |
| [cases_tools_heldout.jsonl](../../eval/cases_tools_heldout.jsonl) | 13; frases adicionales | 11/13 antes de corregir; 13/13 posterior ya inspeccionado |
| [security_cases.jsonl](../../eval/security_cases.jsonl) | 42; suite adversaria | Expectativas de inyección, acceso, acciones y abstención |
| [cases_versions.jsonl](../../eval/cases_versions.jsonl) | 2; revisiones sintéticas | Reingesta e invalidación de índice |
| [security_content_oracle.jsonl](../../eval/security_content_oracle.jsonl) y [v2](../../eval/security_content_oracle_v2.jsonl) | Contenido permitido/prohibido | Versiones conservadas como bancos distintos |
| [security_quest_oracle.jsonl](../../eval/security_quest_oracle.jsonl) y [v2](../../eval/security_quest_oracle_v2.jsonl) | Aislamiento entre quests | Encabezados y páginas agregadas |

Los bancos de herramientas cubren ejecución nominal, selección errónea, parámetros inválidos, acciones que requieren revisión y fallos o timeouts. Las acciones críticas se detectan sin modificar el estado; no se acredita un circuito completo de confirmación.

## Revisiones documentales controladas

[document_versions.json](../../eval/fixtures/document_versions.json) define una fuente ficticia y dos revisiones: 101 sitúa una llave de entrenamiento en el estante A; 102 la sitúa en B. El evaluador prepara y vuelve a leer el documento en la misma ruta, reconstruye BM25 o el índice denso y comprueba que desaparezca la respuesta obsoleta.

```powershell
uv run --no-sync python -m gamerag.evaluation.versions
uv run --no-sync python -m gamerag.evaluation.versions --dense
```

La corrida con E5 local [registrada en este artefacto](../../eval/results/20261116T022250583253Z-b13d858d_versions_synthetic-document-revisions.json) superó los dos casos. Se identifica como sintética, conserva la huella del fixture y no modifica el corpus de producción ni ofrece selección temporal desde la API.

## Oráculos de contenido

Los oráculos inspeccionan por separado la respuesta y el texto final autorizado. Conservan patrones prohibidos, contenido útil requerido, errores y fallas de disponibilidad. No deducen lo prohibido de `LocationGate` ni restan el contexto que el propio filtro consideró permitido.

```powershell
uv run --no-sync python -m gamerag.evaluation.spoiler_oracle --serving-profile base --retriever hybrid --cases eval/security_content_oracle_v2.jsonl
uv run --no-sync python -m gamerag.evaluation.spoiler_oracle --serving-profile base --retriever hybrid --cases eval/security_quest_oracle_v2.jsonl
```

La versión 2 explicita el permiso de nombres genéricos de objetos sin asociarlos a ubicaciones futuras. Los bancos anteriores se conservan para mostrar el cambio de criterio; no se reetiquetan retroactivamente como éxitos. Las últimas mediciones persistidas se citan desde [seguridad](../security/report.md).

Las regresiones posteriores de los mapas Hyrule se encuentran en [test_content_policy.py](../../tests/test_content_policy.py) y [test_request_evidence.py](../../tests/test_request_evidence.py). Comprueban celdas, variantes de nivel, quests, límites de fragmentos y contexto final; no agregan casos retroactivamente a los oráculos ni modifican sus resultados guardados.

## Integridad y límites

Las pruebas automatizadas validan campos, identificadores, distribución y presencia de evidencia de referencia. Los artefactos de esquema 2 rechazan IDs duplicados, casos ajenos al banco, preguntas o etiquetas incompatibles y evidencia sin hash válido.

Esas verificaciones no equivalen a revisar humanamente todas las respuestas ni garantizan que los casos representen todas las necesidades del jugador. La revisión humana del juez, nuevos ejemplos no inspeccionados y cobertura amplia en español siguen requiriendo trabajo documentado del equipo.
