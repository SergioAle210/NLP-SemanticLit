# Documentación

Asistente RAG para juegos retro de NES (*The Legend of Zelda* y *Ninja Gaiden*) con protección de spoilers. Proyecto final de CC3103 (UVG).

| Carpeta | Contenido |
| --- | --- |
| [overview/](overview/) | Problema, usuario, alcance, criterios de éxito y los dos juegos |
| [architecture/](architecture/) | Componentes, flujos, stack, control de acceso y [decisiones (ADRs)](architecture/decisions/) |
| [contracts/](contracts/README.md) | Interfaces entre componentes: generación, filtros de acceso, guardrails, pipeline |
| [api/](api/README.md) | API HTTP (FastAPI): endpoints, errores, auditoría en SQLite |
| [tools/](tools/README.md) | Router de intención y herramientas (§5.6) |
| [ui/](ui/README.md) | Interfaz mínima (Streamlit) sobre la API |
| [deployment/](deployment/README.md) | Docker compose: servicios, volúmenes y decisiones |
| [data/](data/) | Fuentes, licencias y gobernanza del corpus |
| [ingestion/](ingestion/) | Pipeline de ingesta: limpieza, secciones, chunking y metadatos |
| [retrieval/](retrieval/README.md) | Recuperación: BM25 (línea base); vectorial e híbrida (fase 3) |
| [evaluation/](evaluation/) | Banco de pruebas, métricas y [resultados](evaluation/results.md) |
| [security/](security/) | Controles de seguridad y pruebas adversarias |
| [roadmap.md](roadmap.md) | Fases, estado, riesgos y decisiones abiertas |
| [course/](course/) | Requisitos oficiales del curso (instrucciones y presentación) |

## Convenciones

- Cada documento cubre una sola parte del sistema; los detalles se enlazan en vez de repetirse.
- Las decisiones de diseño se registran como **ADRs** en [architecture/decisions/](architecture/decisions/): contexto, decisión, alternativas y consecuencias. Un ADR no se reescribe; si la decisión cambia, se crea uno nuevo que lo reemplaza.
- 🔶 marca decisiones abiertas.
- Las referencias a requisitos usan la numeración de [course/instructions.md](course/instructions.md) (p. ej. §5.3).
