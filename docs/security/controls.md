# Controles de seguridad

Los controles atienden entradas, evidencia, herramientas, respuesta y auditoría. Los resultados pertenecen a corridas identificadas en [report.md](report.md); no se deducen únicamente de la existencia de código.

| Control | Implementación | Límite |
| --- | --- | --- |
| Entrada estructurada | Pydantic y guard básico | Valida formato, no intención completa |
| Juego y progreso | Filtros y `ContentPolicy` | Clasificación curada sobre corpus conocido |
| Inyección directa | Firmas y patrones EN/ES | Formulaciones no vistas pueden evadirlos |
| Inyección documental | Cuarentena y contexto delimitado | Se comprueba el original antes de proyectarlo |
| PII | Redacción antes del LLM y persistencia | Patrones, no detección universal |
| Salida | `Answer`, citas y `LeakGuard` | Cita válida no demuestra fidelidad |
| Herramientas | Lista permitida, parámetros, SQL de lectura y timeout | Una llamada por solicitud; sin proceso aislado universal |
| Acciones críticas | No ejecución y revisión | Sin ciclo de aprobación persistente |
| Auditoría | Respuesta/evidencia finales, etapas y degradaciones | Roles locales sin autenticación |
| Operación | Rate limit, presupuestos y reintentos acotados | Configuración efectiva debe verificarse |

## Casos necesarios

La suite incluye inyección directa, envenenamiento de una fuente de prueba, evasión de progreso, solicitudes de rol administrativo, acciones críticas, parámetros inválidos, indisponibilidad de herramientas y respuestas sin evidencia. Las citas falsificadas se prueban cambiando fuente o página aunque se conserve un identificador válido.

Los casos de revisión incluyen contenido envenenado que conserva el identificador de un fragmento autorizado previamente. La caché de cuarentena depende del hash del texto, y se examinan notas dirigidas a asistentes o modelos en ambos idiomas. Las pruebas de quest incluyen encabezados heredados dentro de páginas agregadas.

La política de mapas Hyrule 1–8 proyecta celdas completas según quest y niveles autorizados. Reconoce referencias numéricas, ordinales y rangos; las reglas curadas cubren también las rutas indirectas de Lost Hills, Spectacle Rock y el muelle de Hyrule 6. Los fragmentos de celda sin límites comprobables se descartan. Las regresiones verifican que se mantienen White Sword, requisitos de corazones y referencias de navegación, así como las rutas de niveles actuales o ya completados.

El oráculo de spoilers debe especificar texto permitido y prohibido de manera independiente a los filtros. Incluye soluciones de final en páginas generales, listas de tesoros, filas de jefes, desenlaces narrativos y casos que deben conservar información útil. Una respuesta vacía puede evitar una fuga y aun así fallar la utilidad esperada.

## Interpretación de resultados

La [medición histórica de 42 casos y 44 sondas](../../eval/results/2026-11-08_security_guarded.json) se conserva con su configuración. Las sondas basadas en las mismas etiquetas de `LocationGate` no detectan todos los spoilers semánticos de páginas generales. La revisión incorpora una política de contenido curada y un oráculo independiente; el [reporte vigente](report.md) identifica sus artefactos separados de los históricos.

No se afirma que G2b, G3 y G4 del diseño inicial estén implementados de forma exhaustiva. La solución actual aplica reglas concretas de pasajes y filas, y no ofrece pistas graduadas completas. Véase [control de acceso](../architecture/access-control.md).

## Última medición persistida y verificaciones posteriores

La [suite final con controles](../../eval/results/20261116T022654688800Z-b171d853_security_guarded.json) utiliza híbrida y extractivo: 37/42 casos frente a [12/42 sin los controles evaluados](../../eval/results/20261116T022700230687Z-c9546ebd_security_baseline.json). Fallan cinco expectativas de abstención. El oráculo de contenido registra 7/9, sin fugas observadas y con dos omisiones de texto permitido; el de quests registra 2/2 frente a 0/2.

Estos resultados preceden a la corrección de celdas del mapa y conservan su configuración y fecha. La corrección posterior está cubierta por [regresiones de contenido](../../tests/test_content_policy.py) y [respuesta/evidencia por solicitud](../../tests/test_request_evidence.py), incluidas las rutas primaria y secundaria. El número de pruebas del cierre técnico se mantiene en [audit-current.md](../evaluation/audit-current.md); no se sustituye por él el denominador de los bancos adversarios.

Las pruebas separadas de envenenamiento usan BM25 y extractivo: exponen el canario en 5/5 sin cuarentena y 0/5 con cuarentena. El campo histórico `obeyed` se interpreta aquí como exposición del canario, no como evidencia de que un LLM siguió una instrucción. El corpus y los controles todavía requieren evaluación ante ataques no vistos.
