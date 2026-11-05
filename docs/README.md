# Documentación

Asistente RAG para juegos retro de NES (*The Legend of Zelda* y *Ninja Gaiden*) con protección de spoilers. Proyecto final de CC3103 (UVG).

| Carpeta | Contenido |
| --- | --- |
| [overview/](overview/) | Problema, usuario, alcance, criterios de éxito y los dos juegos |
| [architecture/](architecture/) | Componentes, flujos, stack, control de acceso y [decisiones (ADRs)](architecture/decisions/) |
| [data/](data/) | Fuentes, licencias y gobernanza del corpus |
| [ingestion/](ingestion/) | Pipeline de ingesta: limpieza, secciones, chunking y metadatos |
| [evaluation/](evaluation/) | Banco de pruebas y métricas |
| [security/](security/) | Controles de seguridad y pruebas adversarias |
| [roadmap.md](roadmap.md) | Fases, estado, riesgos y decisiones abiertas |
| [course/](course/) | Requisitos oficiales del curso (instrucciones y presentación) |

## Convenciones

- Cada documento cubre una sola parte del sistema; los detalles se enlazan en vez de repetirse.
- Las decisiones de diseño se registran como **ADRs** en [architecture/decisions/](architecture/decisions/): contexto, decisión, alternativas y consecuencias. Un ADR no se reescribe; si la decisión cambia, se crea uno nuevo que lo reemplaza.
- 🔶 marca decisiones abiertas.
- Las referencias a requisitos usan la numeración de [course/instructions.md](course/instructions.md) (p. ej. §5.3).
