# Los dos juegos

Los datos de esta página están verificados en el snapshot de la wiki ([data/sources.md](../data/sources.md)). Las diferencias entre los juegos están codificadas en [config/games/](../../config/games/) ([ADR-0007](../architecture/decisions/0007-per-game-config.md)).

## Comparación

| Aspecto | The Legend of Zelda (1986) | Ninja Gaiden (1988/89) |
| --- | --- | --- |
| Corpus | 41 páginas, aprox. 194k caracteres | 11 páginas, aprox. 75k caracteres |
| Estructura | Overworld en 8 secciones + **9 mazmorras (Level-1 a 9) × 2 quests** | **6 actos**, con 21 identificadores de etapa en los encabezados (ver nota) |
| Orden | **No lineal.** Hay prerrequisitos: Level-4 requiere la Raft (de Level-3), Level-7 requiere Whistle y Ladder, Level-9 requiere las 8 piezas de la Trifuerza | **Lineal estricto:** "You may not select or skip any level" |
| ¿El jugador sabe dónde está? | El nombre "Level-N" aparece en el juego, y el subscreen muestra Trifuerza e inventario | El HUD muestra la etapa (p. ej. 2-1) |
| Versiones de contenido | **First Quest / Second Quest:** mismo mapa, mazmorras y objetos en otros lugares | No tiene. Alias de título: *Shadow Warriors*, *Ninja Ryūkenden* |
| Tipo de spoiler | Solución o secreto (dónde está algo, cómo vencer un jefe) | Narrativo (escenas al inicio y al final de cada acto) + jefes |
| Jefes | Uno por mazmorra; algunos se repiten con variantes (Gleeok de 2, 3 y 4 cabezas) | Barbarian, Bomberhead, Basaquer, Kelbeross, Malth; en el Act 6, Masked Devil → Jaquio → Demon |
| Datos exactos | Muchos: precios, corazones requeridos (5 para la White Sword, 12 para la Magic Sword), daño | Pocos: costo de spirit por arma, curación de la poción |
| Navegación en texto | Laberintos visuales: el texto cuarto por cuarto sirve poco | Plataformas lineales: el texto funciona mejor |
| Manual oficial | `CLV-P-NAANE.pdf` | `CLV-P-NACBE.pdf` |

**Second Quest de Zelda:** se desbloquea al terminar el juego, o desde el inicio si el jugador registra su nombre como "ZELDA". Es una segunda vuelta más difícil: las 9 mazmorras conservan su número, pero cambian de lugar y de contenido (la Dungeon 3 de la Q1 no es la de la Q2). La wiki las documenta en páginas separadas (`Underworld/Quest 1/…` y `Underworld/Quest 2/…`), y cada chunk guarda su quest en `location.quest`. Para el proyecto aporta:
- **Versión documental:** la misma pregunta tiene respuestas distintas según la quest ("which dungeon has the Ladder?": Level-4 en la Q1, Level-6 en la Q2).
- **Ambigüedad:** "where is dungeon 3?" sin decir la quest tiene dos respuestas válidas.
- **Control de acceso:** filtrar por la quest del perfil (gate G2) evita mostrarle la Q2 a quien va en la Q1, y da casos concretos para las pruebas de evasión de permisos.

**Nota sobre las etapas de Ninja Gaiden:** la wiki dice "20 levels", pero sus encabezados tienen 21 identificadores (1-1 … 6-4, más "Act 6-5", la pelea contra el Demon). La config sigue los encabezados para que cada chunk mapee a una etapa existente, y un test lo verifica.

**Segmentos dentro de cada acto de Ninja Gaiden:** la escena posterior al jefe está en la misma página que el acto, y por eso hace falta el gate G2b ([access-control.md](../architecture/access-control.md)). No todos los actos tienen escena de apertura: el Act 1 empieza directo en "Stage 1-1".

Ejemplos verificados de spoilers narrativos en el corpus:
- **Act 3:** después del jefe, Ryu encuentra a Dr. Smith gravemente herido y le roban la Light statue.
- **Act 5:** después de vencer a Malth, este le revela a Ryu que "his father is still alive".

Con el chunking fijo, estas escenas quedan en el mismo chunk que la pelea contra el jefe ([ingestion/chunking.md](../ingestion/chunking.md)).

## Qué aporta cada juego a la evaluación

| Requisito | Zelda | Ninja Gaiden |
| --- | --- | --- |
| Versión / vigencia | ✅ Q1 frente a Q2, más `revid` | ⚪ Solo el nombre regional (*Shadow Warriors* en Europa), más `revid` |
| Identificadores exactos | ✅ "Level-4", "D-4", frases de los ancianos | ✅ "Stage 2-3", "Stage 3-3", jefes |
| Ambigüedad | ✅ Gleeok de 2, 3 y 4 cabezas | ⚪ Posible (tres jefes seguidos en el Act 6); el mini banco todavía no tiene casos |
| Herramienta SQL (`query_game_facts`) | ✅ Tabla de jefes | ⚪ Sin tabla equivalente |
| Herramienta de progreso (`next_available_levels`) | ✅ No lineal: tiene sentido | ❌ Lineal: la config no la habilita ([tools/](../tools/README.md)) |
| Spoiler narrativo | ⚪ Casi no hay | ✅ Fuerte |
| Aislamiento entre juegos | ✅ Ambos tienen un "boomerang" (Zelda: el Boomerang; NG: el Windmill Star, que regresa "like a boomerang") | ✅ |

Los juegos son complementarios: juntos muestran que el diseño de gates es genérico y no está atado a un juego.

**Qué aporta Ninja Gaiden al proyecto:**
- **Generalidad:** tiene otro modelo de progreso (lineal, `linear_stage`, frente al conjunto de niveles de Zelda). El mismo pipeline sirve para los dos; solo cambia la configuración del juego ([ADR-0007](../architecture/decisions/0007-per-game-config.md)).
- **Spoilers narrativos:** las escenas posteriores a cada jefe ("his father is still alive") requieren el gate G2b, distinto de los spoilers de solución de Zelda.
- **Aislamiento entre juegos:** comparte vocabulario con Zelda ("boomerang", "sword", "heal"), así que sirve para verificar que G1 no mezcle juegos.
- **Router:** la config no habilita `next_available_levels` (en un juego lineal, la siguiente etapa es trivial); el test de "herramienta no habilitada" usa ese caso.
- **Validación de las técnicas:** con un mini banco de 15 casos y un glosario propio ("ninpo" → "spirit points"), el Recall@5 pasó de 0.85 a 0.92 ([evaluation/results.md](../evaluation/results.md)). Las técnicas de Zelda funcionaron en otro juego sin rediseño.
