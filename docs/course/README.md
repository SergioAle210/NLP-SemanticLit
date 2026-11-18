# Entregables académicos y maquetación

| Archivo | Propósito |
| --- | --- |
| [instructions.md](instructions.md) | Instrucciones oficiales del proyecto; conservadas sin modificaciones |
| [presentation.md](presentation.md) | Presentación oficial del curso; no es la presentación del equipo |
| [informe.md](informe.md) | Anteproyecto consolidado, con las dieciséis secciones originales |
| [anteproyecto.pdf](../../output/pdf/anteproyecto.pdf) | Anteproyecto de 11 páginas A4 sin carátula, con los campos y apartados de la plantilla proporcionada |
| [anteproyecto.layout.json](../../output/pdf/anteproyecto.layout.json) | Correspondencia entre la fuente del anteproyecto y su PDF, sin página de carátula |
| [informe-final.md](informe-final.md) | Fuente Markdown del informe técnico final |
| [informe-final.pdf](../../output/pdf/informe-final.pdf) | Exportación final: 15 páginas A4, incluida la carátula, y dos figuras |
| [informe-final.layout.json](../../output/pdf/informe-final.layout.json) | Manifiesto de correspondencia, hashes y paginación |
| [auditoria-cumplimiento.md](auditoria-cumplimiento.md) | Requisitos, evidencias y límites |
| [defensa.md](defensa.md) | Guion propuesto para la defensa de quince minutos |
| [plan-presentacion.md](plan-presentacion.md) | Contenido de la presentación por diapositiva, en el orden del §13 y con el criterio de la rúbrica que cubre cada una |
| [presentacion-equipo.pdf](presentacion-equipo.pdf) | Presentación del equipo de 20 diapositivas, con foliación continua y rótulos de las gráficas aclarados |
| [Video de presentación](https://youtu.be/ZC5XwdeHOQ4) | Enlace proporcionado por el equipo e incluido en el informe final |

## Generar los informes PDF

Desde la raíz del repositorio, con el entorno instalado según el README y [Graphviz](https://graphviz.org/download/) disponible como `dot` en `PATH`:

```powershell
dot -V
uv run --no-sync --with reportlab --with pypdf --with pillow python scripts/render_report.py docs/course/informe-final.md output/pdf/informe-final.pdf
uv run --no-sync --with reportlab --with pypdf --with pillow python scripts/render_report.py docs/course/informe.md output/pdf/anteproyecto.pdf --document-kind Anteproyecto
```

`--no-sync` conserva el entorno del proyecto ya preparado; las dependencias de maquetación se proporcionan para esta ejecución mediante `--with`. El comando no depende de una ruta temporal de Python. Graphviz es una dependencia externa al entorno Python.

El script [render_report.py](../../scripts/render_report.py) interpreta las tablas y el subconjunto de Mermaid utilizado por el informe. Produce el PDF y un manifiesto `output/pdf/informe-final.layout.json` con hashes de fuente y PDF, número de páginas, cantidad de figuras y veredicto del rango de 10–15 páginas. Los PNG y archivos DOT intermedios se guardan en `tmp/pdfs/`.

La carátula del informe final se obtiene del título, tipo de documento, institución, integrantes, curso y fecha situados antes del primer separador del Markdown. El [logotipo proporcionado por el equipo](assets/logo-uvg.png) se incluye sin modificar y su hash queda registrado en el manifiesto. La carátula no muestra folio; la numeración comienza en el cuerpo, que tiene 14 páginas. El total de 15 páginas incluye la carátula.

El anteproyecto sigue las dieciséis secciones de la plantilla de Word proporcionada por el equipo. Comienza con información general y conserva sus cuatro campos: título del proyecto, integrantes, dominio y usuario primario. No incluye carátula, video ni una declaración adicional de IA; estos últimos se conservan en el informe final. Su exportación tiene 11 páginas y un manifiesto independiente que registra cero páginas de carátula. El argumento `--document-kind Anteproyecto` identifica correctamente los encabezados y los metadatos del PDF. Las tablas pueden continuar en otra página con su encabezado repetido. El rango exigido de 10–15 páginas corresponde al informe técnico final.

Los párrafos de ambos informes utilizan texto sin negritas, cursivas ni tipografía de código. El informe final incluye el enlace al video de presentación y describe el apoyo de IA en términos generales. El desarrollo y la evaluación se describen por etapas o períodos mensuales, sin indicar días específicos en el cuerpo; conservamos la fecha de la carátula del informe final y los registros originales de procedencia. Las referencias internas de implementación se mantienen en la documentación técnica, mientras los informes explican métodos y resultados en lenguaje académico.

El [manifiesto](../../output/pdf/informe-final.layout.json) es la referencia única para los hashes de la fuente y del [PDF entregable](../../output/pdf/informe-final.pdf), su número de páginas y sus figuras. Evitamos duplicar esos hashes en este documento para que cada exportación conserve una sola correspondencia verificable. El informe debe mantenerse entre 10 y 15 páginas A4.

Después de modificar el Markdown se debe volver a generar el PDF. Comprobar que el hash de la fuente corresponda al archivo entregado, que el manifiesto indique el rango requerido y que ambas figuras sean legibles. Revisar también tablas, acentos, saltos de página, encabezados y referencias. Un conteo correcto de páginas no sustituye la inspección visual.

El comando permite repetir el proceso de maquetación; no promete PDFs idénticos byte a byte entre versiones de librerías, fuentes o sistemas operativos. Los archivos generados y el manifiesto identifican la exportación concreta.

## Responsabilidad académica

Ambos informes emplean redacción formal en primera persona plural. La declaración de IA registra únicamente intervenciones conocidas. El guion no acredita ensayo, participación individual ni revisión humana; esas actividades requieren un registro del equipo.

La presentación conserva el contenido y las cifras del PDF proporcionado por el equipo. Corregimos el salto en los folios y añadimos nombres de configuraciones al gráfico de recuperación, además de las etiquetas y el denominador de las barras de seguridad. El [plan de exposición](plan-presentacion.md) vincula sus veinte diapositivas con los seis bloques oficiales y sitúa la demostración de cuatro minutos después de la diapositiva 13.

## Procedencia de la ampliación del informe final

La ampliación utiliza respuestas y registros existentes; no representa nuevas consultas al sistema ni llamadas al proveedor.

- Recuperación: recontamos fragmentos relevantes en los cinco primeros resultados de las corridas del 9 de noviembre: [principal](../../eval/results/2026-11-09_e2e_final-principal.json), [difícil](../../eval/results/2026-11-09_e2e_final-dificil.json) y [adicional](../../eval/results/2026-11-09_e2e_final-extra.json). Los conteos son 62/245, 20/90 y 50/305. Todos los contextos evaluables de esas corridas tienen cinco fragmentos; el recall de unidades, promediado por pregunta, coincide allí con su cobertura de contexto.
- Calidad: el apoyo léxico y la fracción media de oraciones con bajo apoyo proceden del [marcador histórico](../../eval/results/scorecard_latest.json), con 50, 18 y 58 respuestas evaluadas. La cobertura fáctica y relevancia se examinan cualitativamente mediante los casos archivados `zelda_direct_02`, `extra_ac2_00` y `hard_01`; no se presenta una estimación semántica agregada ni validación humana independiente.
- Operación: los tres históricos registran cero errores finales, pero carecen de contadores completos de invocaciones, reintentos y degradaciones. La telemetría completa procede de las 136 consultas extractivas del [manifiesto base](../../eval/scorecard_manifest_base.json). Sus ceros no se atribuyen al proveedor remoto.
- Fuentes: las fechas, revisiones y licencias se contrastaron con los 24 manifiestos de adquisición y la [política de gobernanza](../data/sources.md). Las fechas identifican descarga, no publicación; los rangos de revisión no representan historiales completos.
- Seguridad: el [reporte de pruebas adversarias](../security/report.md) respalda los resultados por vector y sus límites. Los impactos de riesgo mantienen la valoración del anteproyecto.
