# Problema, usuario y alcance

Cubre el requisito §5.1 de [course/instructions.md](../course/instructions.md).

## Problema

Los juegos de NES se diseñaron para jugarse con su manual. Hoy el jugador que no lo tiene busca en wikis y se encuentra con:
- soluciones, giros de historia y finales que no quería ver;
- información de otras versiones o remakes;
- respuestas inventadas por chatbots genéricos.

## Usuarios

- **Primario:** jugador casual que juega un título retro por primera vez (NES Classic, Nintendo Switch Online) y no quiere leer una guía completa.
- **Secundario:** jugador experto o *completionist* que quiere toda la información.

## Tarea

Responder preguntas sobre controles, mecánicas, objetos, jefes y etapas con **citas verificables**, **sin revelar contenido posterior al progreso del jugador** y con el nivel de detalle que el jugador elija.

## Costo de una respuesta incorrecta

| Falla | Impacto | Tratamiento |
| --- | --- | --- |
| Alucinación | Medio: el jugador pierde tiempo buscando algo que no existe | Generación con contexto cerrado, citas obligatorias y abstención |
| Spoiler | Alto: irreversible para la experiencia | Se trata como **fuga de información** ([control de acceso](../architecture/access-control.md)) |

## Alcance

**Dentro:**
- *The Legend of Zelda* (Q1 y Q2) y *Ninja Gaiden* (NES); ver [games.md](games.md).
- Preguntas y respuestas **en inglés**, el idioma del corpus ([ADR-0001](../architecture/decisions/0001-english-first.md)). La interfaz puede estar en español.
- Preguntas de tipo *qué, dónde, qué necesito, cómo vencer*.
- Fichas por mazmorra o acto, con pistas escalonadas.

**Opcional, al final:** preguntas en español sobre el mismo corpus (fase 3d de la [hoja de ruta](../roadmap.md)). Solo se declara soportado si se valida con casos de prueba propios.

**Fuera:**
- Navegación cuarto por cuarto en tiempo real.
- Imágenes y mapas oficiales.
- Otros juegos de las sagas, remakes y ports.
- Speedruns y glitches.
- Login y registro de usuarios ([ADR-0004](../architecture/decisions/0004-sqlite-and-demo-profiles.md)).

## Criterios de éxito 🔶

Son metas a confirmar con la línea base:

| Métrica | Meta |
| --- | --- |
| Recall@5 (preguntas con respuesta) | ≥ 0.80 |
| Precisión de citas | ≥ 0.90 |
| Abstención correcta | ≥ 90% |
| Spoilers filtrados | 0 |
| Respuestas con contenido del juego equivocado | 0 |
| Latencia P95 (CPU local) | < 6 s |

## Manifiesto del anteproyecto

1. **Nuestro usuario es** un jugador que prueba por primera vez un juego retro de NES sin el manual a la mano.
2. **Su problema concreto es** que necesita entender controles, objetos y cómo avanzar, pero las fuentes disponibles mezclan versiones y revelan soluciones, giros de historia y finales.
3. **La evidencia que utilizaremos está en** StrategyWiki (CC BY-SA 4.0, snapshots congelados con `revid`) y en los manuales oficiales publicados por Nintendo.
4. **Demostraremos que funciona mediante** un banco de más de 20 casos con Recall@k, MRR, precisión de citas y abstención por juego, comparando la línea base contra la versión mejorada, y pruebas adversarias de spoilers, contaminación entre juegos e inyección.
5. **El principal riesgo identificado es** revelar spoilers o alucinar contenido, y **lo mitigaremos mediante** gates de acceso por juego, ubicación, narrativa, entidad y nivel de pista, generación con contexto cerrado y citas, y validación de la salida.
