# Entregables académicos y maquetación

| Archivo | Propósito |
| --- | --- |
| [instructions.md](instructions.md) | Instrucciones oficiales del proyecto; conservadas sin modificaciones |
| [presentation.md](presentation.md) | Presentación oficial del curso; no es la presentación del equipo |
| [informe.md](informe.md) | Anteproyecto consolidado, con las dieciséis secciones originales |
| [informe-final.md](informe-final.md) | Fuente Markdown del informe técnico final |
| [informe-final.pdf](../../output/pdf/informe-final.pdf) | Exportación final: 14 páginas A4 y dos figuras |
| [informe-final.layout.json](../../output/pdf/informe-final.layout.json) | Manifiesto de correspondencia, hashes y paginación |
| [auditoria-cumplimiento.md](auditoria-cumplimiento.md) | Requisitos, evidencias y límites |
| [defensa.md](defensa.md) | Guion propuesto para la defensa de quince minutos |

## Generar el informe PDF

Desde la raíz del repositorio, con el entorno instalado según el README y [Graphviz](https://graphviz.org/download/) disponible como `dot` en `PATH`:

```powershell
dot -V
uv run --no-sync --with reportlab --with pypdf --with pillow python scripts/render_report.py docs/course/informe-final.md output/pdf/informe-final.pdf
```

`--no-sync` conserva el entorno del proyecto ya preparado; las dependencias de maquetación se proporcionan para esta ejecución mediante `--with`. El comando no depende de una ruta temporal de Python. Graphviz es una dependencia externa al entorno Python.

El script [render_report.py](../../scripts/render_report.py) interpreta las tablas y el subconjunto de Mermaid utilizado por el informe. Produce el PDF y un manifiesto `output/pdf/informe-final.layout.json` con hashes de fuente y PDF, número de páginas, cantidad de figuras y veredicto del rango de 10–15 páginas. Los PNG y archivos DOT intermedios se guardan en `tmp/pdfs/`.

El [manifiesto](../../output/pdf/informe-final.layout.json) es la referencia única para los hashes de la fuente y del [PDF entregable](../../output/pdf/informe-final.pdf), su número de páginas y sus figuras. Evitamos duplicar esos hashes en este documento para que cada exportación conserve una sola correspondencia verificable. El informe debe mantenerse entre 10 y 15 páginas A4.

Después de modificar el Markdown se debe volver a generar el PDF. Comprobar que el hash de la fuente corresponda al archivo entregado, que el manifiesto indique el rango requerido y que ambas figuras sean legibles. Revisar también tablas, acentos, saltos de página, encabezados y referencias. Un conteo correcto de páginas no sustituye la inspección visual.

El comando permite repetir el proceso de maquetación; no promete PDFs idénticos byte a byte entre versiones de librerías, fuentes o sistemas operativos. Los archivos generados y el manifiesto identifican la exportación concreta.

## Responsabilidad académica

Ambos informes emplean redacción formal en primera persona plural. La declaración de IA registra únicamente intervenciones conocidas. El guion no acredita ensayo, participación individual ni revisión humana; esas actividades requieren un registro del equipo.
