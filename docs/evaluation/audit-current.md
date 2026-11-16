# Auditoría y mediciones actuales

**Mediciones persistidas:** 15 de noviembre de 2026 en Guatemala; artefactos registrados el 16 de noviembre en UTC. **Cierre técnico posterior:** 520 pruebas aprobadas, sin omisiones.

Hemos implementado captura de evidencia final por solicitud, validación de citas completas, telemetría
aislada, un juez que recibe el contexto autorizado, pruebas de revisiones documentales y oráculos de
contenido independientes de los controles de producción. Conservamos los resultados históricos de
Haiku y los separamos de las mediciones actuales del perfil `base`, que utiliza recuperación híbrida y
generación extractiva. En el entorno de esta auditoría no contamos con una clave de Anthropic y no
realizamos llamadas pagadas ni una nueva revisión humana de respuestas.

La verificación técnica posterior incorporó la proyección por celda de los mapas Hyrule 1–8 y sus
regresiones sobre respuesta, evidencia, búsqueda primaria y secundaria. Conservamos las instrucciones
permitidas, como White Sword, y restringimos las rutas de mazmorras aún no desbloqueadas, incluidas las
referencias indirectas de Lost Hills y Spectacle Rock. Los resultados numéricos de esta página proceden
de las corridas enlazadas y no se recalcularon después de esa corrección. El XML de 489 pruebas conserva
una ejecución anterior; no representa la suite posterior de 520.

## Última medición persistida del perfil base

Regeneramos los corpus principales y secundarios de siete juegos: 2,759 y 10,462 fragmentos,
respectivamente. Ejecutamos 136 consultas en los tres bancos documentales, sin errores de ejecución y
sin consumo de tokens de un LLM. El perfil base consulta el corpus principal; el banco de preguntas
que exige fuentes secundarias permanece fuera de su cobertura.

| Banco | Casos | Hit-rate@5 | Precisión de citas | Exactitud global de abstención | Recall de abstención | P95 (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Principal | 54 | 0.9388 | 0.3061 | 0.9074 | 0/5 = 0.0000 | 0.023 |
| Difícil | 21 | 1.0000 | 0.3704 | 0.8571 | 0/3 = 0.0000 | 0.019 |
| Solo fuentes extra | 61 | 0.0000 | 0.0000 | 1.0000 | No evaluable: 0 no respondibles | 0.027 |

Medimos la latencia de `pipe.ask` después de preparar corpus, modelos e índices. El P95 conserva el
estadístico de orden inferior `floor(0.95 × (n − 1))` utilizado en las corridas previas. Las cifras no
incluyen el arranque en frío ni la descarga de modelos. La precisión de citas mide relevancia según
la evidencia esperada del banco; no equivale al soporte semántico de cada afirmación.

Observamos una pérdida de recuperación en `zelda_robust_06`, «how do i use my secondary item», frente
a la corrida intermedia anterior a corregir las quests. Después de actualizar los metadatos e índices,
`zelda1:controls:000` salió del contexto de cinco fragmentos y entró `zelda1:walkthrough:005`. Conservamos
ambas corridas; no modificamos la etiqueta ni la evidencia esperada del caso.

Registramos incumplimiento de la meta de precisión de citas de 0.90 y del recall de abstención de
0.90 en los bancos con preguntas no respondibles. La exactitud global del banco principal supera 0.90
porque 49 de sus 54 preguntas son respondibles, aunque no obtuvimos ninguna abstención en sus cinco
preguntas no respondibles. En el banco extra todas las preguntas son respondibles, por lo que su
exactitud de abstención de 1.00 no acredita cobertura factual.

El [marcador del perfil base](scorecard-base.md) incluye denominadores, procedencia y metas; el
[marcador histórico](scorecard.md) conserva las cifras de las corridas de noviembre con Haiku. No
utilizamos la ausencia de regresiones numéricas sobre los archivos históricos para afirmar que la
implementación actual cumple las metas.

## Controles de seguridad y disponibilidad

| Comprobación | Controles activos | Controles desactivados |
| --- | ---: | ---: |
| Banco adversario principal | 37/42 | 12/42 |
| Oráculo independiente de contenido, versión 2 | 7/9 | 2/9 |
| Fugas de contenido en respuesta / evidencia, versión 2 | 0 / 0 | 2 / 5 |
| Oráculo de aislamiento de quests, versión 2 | 2/2 | 0/2 |
| Fugas entre quests en respuesta / evidencia | 0 / 0 | 1 / 2 |
| Canarios presentes de documentos envenenados, con / sin cuarentena | 0/5 / 5/5 | 0/5 / 5/5 |
| Comprobaciones de acceso por rol en la API | 6/6 | 6/6 |

Evaluamos la cuarentena con su propio par activado/desactivado y verificamos el control de roles en
ambas configuraciones; desactivar los filtros del pipeline no desactiva la autorización de la API.

Los cinco incumplimientos del banco adversario corresponden a `sec_033`–`sec_037`: Moon Pearl,
Dark World, la hermana de la princesa, vidas infinitas y una espada láser. El generador extractivo
devuelve fragmentos relacionados por vocabulario y marca `abstained=False`; no acredita que esos
fragmentos respondan a la pregunta. Mantenemos los casos como fallos de calibración.

Detectamos y corregimos exposición de fragmentos `[2nd Quest]` a perfiles de First Quest. La ingesta
ahora conserva la quest derivada de los encabezados y la política también protege corpus anteriores.
El control positivo de la hada que restaura vida verifica que seguimos mostrando la información de
la quest autorizada. También corregimos la cuarentena de instrucciones dirigidas a un asistente de
IA y la invalidación de su caché cuando cambia el texto de un mismo ID.

Los dos incumplimientos del oráculo de contenido corresponden a escenas de Ninja Gaiden ya
desbloqueadas. Encontramos las escenas en la evidencia autorizada, pero la respuesta extractiva las
trunca después de 400 caracteres. Las sondas sobre escenas todavía bloqueadas y Silver Arrows no
registraron fugas bajo los patrones declarados.

Conservamos el [banco inicial](../../eval/security_content_oracle.jsonl) y su resultado 5/8. La
[versión 2](../../eval/security_content_oracle_v2.jsonl) explicita que protegemos soluciones,
ubicaciones futuras y desenlaces, mientras permitimos mecánicas generales de objetos. Añadimos una
consulta sobre Magic Key que debe explicar su función sin revelar la ubicación posterior. Esta
aclaración cambia el criterio del banco y no constituye una mejora porcentual comparable entre las
versiones 1 y 2. Documentamos ambas versiones en [fixtures/README.md](../../eval/fixtures/README.md).

El [reporte de seguridad](../security/report.md) contiene los casos y resultados observados. Sus
sondas históricas de ubicación miden coherencia con metadatos; los oráculos nuevos inspeccionan
directamente respuesta y evidencia sin invocar los controles de producción. Los canarios expuestos
por una respuesta extractiva no prueban obediencia de un LLM.

## Herramientas y revisiones documentales

Verificamos 26/26 casos de herramientas, incluidos errores y timeouts inyectados, solicitudes de
confirmación y selección incorrecta. No observamos falsos disparos del router en 165 consultas
documentales. Capturamos las degradaciones y los extractos autorizados devueltos por herramientas.

En un corpus sintético independiente, reingestamos las revisiones 101 y 102 de un mismo documento
y volvimos a abrir la misma ruta del índice. La respuesta cambió de «shelf A» a «shelf B» y la cita
conservó la revisión correspondiente. Obtuvimos 2/2 con BM25 y 2/2 con el modelo denso E5 descargado
localmente. Las pruebas automatizadas también verifican invalidación cuando cambia únicamente la
revisión o el metadato de acceso, aunque el texto permanezca igual.

## Artefactos y reproducción

Utilizamos nombres únicos para las corridas y creación exclusiva de archivos. El esquema 2 registra
hash del banco, corpus, configuración efectiva y código/configuración del proyecto; estado de Git;
perfil del jugador; respuesta; citas completas; evidencia exacta con hashes; llamadas, reintentos,
errores, degradaciones y etapas por solicitud. En las tres corridas finales documentales comprobamos
que la huella de implementación no cambió durante la ejecución.

| Evidencia | Archivo |
| --- | --- |
| Principal, medición persistida | [Resultado](../../eval/results/20261116T022631268527Z-2ffd3153_e2e_audit-final-base-principal.json) |
| Difícil, medición persistida | [Resultado](../../eval/results/20261116T022649868252Z-e9fc6355_e2e_audit-final-base-hard.json) |
| Fuentes extra, medición persistida | [Resultado](../../eval/results/20261116T022651099719Z-d06db1c2_e2e_audit-final-base-extra.json) |
| Seguridad con controles | [Resultado](../../eval/results/20261116T022654688800Z-b171d853_security_guarded.json) |
| Seguridad sin controles | [Resultado](../../eval/results/20261116T022700230687Z-c9546ebd_security_baseline.json) |
| Herramientas, medición persistida | [Resultado](../../eval/results/20261116T022858581774Z-3a5bc434_tools_tools.json) |
| Revisiones documentales con E5 | [Resultado](../../eval/results/20261116T022250583253Z-b13d858d_versions_synthetic-document-revisions.json) |
| Manifiesto del perfil base | [Manifiesto](../../eval/scorecard_manifest_base.json) |

```bash
python -m gamerag.evaluation.e2e --serving-profile base --cases eval/cases.jsonl --label base-principal
python -m gamerag.evaluation.e2e --serving-profile base --cases eval/cases_hard.jsonl --label base-hard
python -m gamerag.evaluation.e2e --serving-profile base --cases eval/cases_extra.jsonl --label base-extra
python -m gamerag.evaluation.security --serving-profile base --retriever hybrid --offline
python -m gamerag.evaluation.security --serving-profile base --retriever hybrid --offline --baseline
python -m gamerag.evaluation.tools_eval
python -m gamerag.evaluation.versions --dense
python -m gamerag.evaluation.scorecard --manifest eval/scorecard_manifest_base.json --baseline eval/baseline_scorecard_base.json --output-json eval/results/scorecard_base_current.json --output-md docs/evaluation/scorecard-base.md
python -m gamerag.evaluation.scorecard --manifest eval/scorecard_manifest_base.json --check-targets
```

El último comando devuelve un código distinto de cero por las metas incumplidas o no evaluables y no
modifica archivos. No creamos automáticamente una línea base para convertir la medición actual en
un control aprobado. Para validar el perfil full necesitamos nuevas corridas con credenciales y
presupuesto; el juez `evaluation.compare A.json B.json --cases ...` conserva sus decisiones y recibe
la evidencia final autorizada de cada respuesta. Las pruebas del juez con clientes simulados validan
el contrato y el registro de errores, pero no constituyen una evaluación semántica del modelo.
