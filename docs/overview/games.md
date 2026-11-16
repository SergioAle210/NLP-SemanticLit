# Juegos y cobertura

Los juegos y modelos de progreso se definen en [config/games/](../../config/games/). La existencia de configuración y corpus no implica igual validación de preguntas o spoilers.

| Identificador | Juego | Modelo |
| --- | --- | --- |
| `zelda1` | The Legend of Zelda | `level_set`: quest y mazmorras |
| `ninja_gaiden_nes` | Ninja Gaiden (NES) | `linear_stage`: etapas |
| `oot` | Ocarina of Time | `level_set`: zonas/mazmorras |
| `ac2` | Assassin's Creed II | `linear_stage`: secuencias |
| `doom` | Doom | `linear_stage`: mapas |
| `gta_sa` | Grand Theft Auto: San Andreas | `linear_stage`: regiones de progreso |
| `rdr1` | Red Dead Redemption | `linear_stage`: clasificación amplia de historia |

El banco principal contiene 39 casos de Zelda y 15 de Ninja Gaiden. Los bancos complementarios estudian preguntas difíciles, fuentes adicionales, herramientas y seguridad. La clasificación amplia de un juego requiere curaduría adicional antes de prometer restricciones finas.

## Juegos principales

Zelda aporta progreso no lineal, dos quests, tablas de jefes, identificadores exactos y soluciones distribuidas entre objetos y ubicaciones. El snapshot primario inicial registra 41 páginas y aproximadamente 194 mil caracteres. First Quest y Second Quest son variantes del juego: pueden cambiar la respuesta a una pregunta, pero no sustituyen una prueba de revisión documental. La versión de una página se identifica mediante `revid`.

En los mapas de Hyrule, la política filtra celdas completas y rutas dependientes de mazmorras no autorizadas. Conserva contenido permitido, como la explicación de White Sword, sin confundir cantidades de corazones o números de sección con niveles. Las reglas cubren las formas y asociaciones declaradas en la configuración; no constituyen un detector universal de soluciones implícitas.

Ninja Gaiden aporta progreso lineal y escenas narrativas cercanas al combate en el mismo documento. El snapshot primario inicial registra 11 páginas y aproximadamente 75 mil caracteres. La configuración utiliza los 21 identificadores presentes en los encabezados, incluida la batalla final, aunque la descripción de la wiki emplee otro recuento de niveles.

Los desenlaces de una batalla requieren progreso posterior al tramo actual. La [política de contenido](../architecture/access-control.md) separa u oculta evidencia cuando una sección mezcla táctica y narración. Los bordes de fragmentos que no permiten verificar una unidad completa reciben un tratamiento conservador.

## Herramientas y límites

`query_game_facts` utiliza la tabla de jefes de Zelda. `next_available_levels` está disponible para juegos configurados con conjuntos de niveles, pero devuelve números pendientes y no resuelve prerrequisitos jugables. Una herramienta no declarada en la configuración no se habilita por similitud entre juegos.

Las fuentes de franquicia se distinguen de fuentes específicas del título y se excluyen por defecto de la búsqueda secundaria. Los [manifiestos](../../data/wiki_snapshot/README.md) registran páginas y atribución por origen.
