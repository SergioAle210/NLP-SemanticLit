# Documentación de GameRAG

Sistema RAG para siete videojuegos, con evaluación principal sobre The Legend of Zelda y Ninja Gaiden (NES). La interfaz vigente utiliza Gradio en el puerto 7860; la API utiliza FastAPI en el puerto 8000.

| Documento | Contenido |
| --- | --- |
| [Problema y alcance](overview/problem-and-scope.md) | Usuario, objetivos, criterios de éxito y límites |
| [Juegos](overview/games.md) | Cobertura y modelos de progreso |
| [Arquitectura](architecture/overview.md) | Flujos de usuario e ingesta, componentes y estado |
| [Control de acceso](architecture/access-control.md) | Permisos, progreso, evidencia y límites del control de spoilers |
| [Contratos](contracts/README.md) | Generación, respuesta, evidencia y traza |
| [API](api/README.md) | Rutas, errores, configuración efectiva y auditoría |
| [Herramientas](tools/README.md) | Router, consultas deterministas y acciones no ejecutadas |
| [Interfaz](ui/README.md) | Puesto de Control, Gradio y comprobación visual |
| [Despliegue](deployment/README.md) | Ejecución local, Docker, bootstrap y volúmenes |
| [Fuentes](data/sources.md) | Licencias declaradas, manifiestos y gobernanza |
| [Datos sensibles](data/sensitive-data.md) | Redacción y retención de auditoría |
| [Ingesta](ingestion/README.md) | Limpieza, segmentación y metadatos |
| [Recuperación](retrieval/README.md) | BM25, E5, RRF y experimentos |
| [Evaluación](evaluation/metrics.md) | Definiciones, bancos y resultados reproducibles |
| [Auditoría de evaluación](evaluation/audit-current.md) | Corridas de cierre, artefactos y limitaciones |
| [Seguridad](security/controls.md) | Controles y [reporte de pruebas](security/report.md) |
| [Hoja de ruta](roadmap.md) | Estado de implementación, verificaciones y trabajo futuro |
| [Anteproyecto](course/informe.md) | Documento de 16 secciones solicitado por el equipo |
| [Informe final](course/informe-final.md) | Informe académico técnico |
| [Defensa](course/defensa.md) | Guion de 15 minutos y escenarios de demostración |
| [Plan de la presentación](course/plan-presentacion.md) | Diapositivas en el orden del §13, cada una con su criterio de la rúbrica |
| [Presentación del equipo](course/presentacion-equipo.pdf) | PDF de 20 diapositivas proporcionado por el equipo |
| [Video de presentación](https://youtu.be/ZC5XwdeHOQ4) | Enlace incluido en el informe final |
| [Matriz de cumplimiento](course/auditoria-cumplimiento.md) | Requisito, evidencia y alcance de verificación |
| [Entregables y maquetación](course/README.md) | Generación del PDF y comprobación de correspondencia con el Markdown |
| [Instrucciones](course/instructions.md) y [presentación del curso](course/presentation.md) | Fuentes oficiales de requisitos, conservadas sin modificaciones |

## Documentación vigente e historia

Las guías de componentes describen el contrato vigente. Las cifras se citan con banco, configuración, fecha y artefacto; no se sustituyen resultados antiguos por mediciones de otra versión. Los documentos de análisis de noviembre de 2026 y los [ADRs](architecture/decisions/README.md) conservan el razonamiento histórico. Una decisión posterior se documenta como tal y enlaza la anterior.

Una marca de implementación no acredita una prueba en vivo. Diferenciamos pruebas automatizadas, resultados históricos con LLM, ejecuciones de caché, evaluaciones sintéticas y revisiones humanas. Las referencias `§` remiten a las [instrucciones del curso](course/instructions.md).
