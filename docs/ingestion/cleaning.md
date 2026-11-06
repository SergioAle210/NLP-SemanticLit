# Limpieza de wikitext

Implementación: [src/gamerag/ingest/clean.py](../../src/gamerag/ingest/clean.py). Decisión: [ADR-0005](../architecture/decisions/0005-wikitext-cleaning.md).

## Orden de procesamiento

1. **Parseo** con mwparserfromhell.
2. **Plantillas:** se renderizan primero los argumentos (de adentro hacia afuera) y después la plantilla.
3. **Enlaces:**
   - `[[File:]]`, `[[Image:]]` y `[[Category:]]` se eliminan;
   - `[[destino|texto]]` pasa a `texto`;
   - `[[A/B/C]]` pasa a `C`.
4. **Etiquetas HTML:**
   - `<gallery>`, `<imagemap>` y `<ref>` se eliminan;
   - `<br>` pasa a salto de línea;
   - las demás conservan su contenido.
5. **Tablas:** se aplanan a una línea por fila.
6. **Marcado residual:**
   - se quitan las negritas y cursivas y las palabras mágicas (`__TOC__`);
   - las listas pasan a `- `;
   - se normalizan los espacios.

Los encabezados `== X ==` **se conservan**, porque la segmentación los usa.

## Reglas de plantillas

Inventario hecho sobre ambos snapshots (2026-11-05).

| Regla | Plantillas | Ejemplo |
| --- | --- | --- |
| Descartar (navegación y maquetación) | `Header Nav`, `Footer Nav`, `floatingtoc`, `-`, `col`, `ToC`, `ContentBoxContainer`, `Zeldawiki`, `img`, `Scrolling_map`, `game disambig`, `desc`, `prettytable`, plantillas de navegación de cada juego, `DEFAULTSORT`, clasificaciones (`CERO`, `ESRB`, `PEGI`, `OFLC`) | — |
| Descartar (botones de otras consolas) | `gc`, `wii`, `wii-cc`, `3ds`, `switch` | El alcance es la versión de NES |
| Nombre del objeto o artículo | `im/loz`, `a`, `c`, `n/a` | `{{im/loz\|Item\|Raft}}` → `Raft` |
| Botón de NES | `nes` | `{{nes\|Up\|Dpad}}` → `Up (D-pad)`; `{{nes\|Neutral\|Dpad}}` → `D-pad` |
| Literal | `plus`, `(`, `)` | `{{plus}}` → `+` |
| Encabezado de lista | `h2`, `h3` | Línea propia |
| Nombre con original japonés | `nihongo` | `Ninja Gaiden (NINJA外伝)` |
| Lista | `colist`, `syslist` | Separada por comas |
| Ficha del juego | `Game` | Una línea `Campo: valor` por dato útil (título, título japonés, desarrollador, diseñadores, año, sistemas, género…); se omiten imagen y clasificaciones |
| Subsección | `ContentBox` | `=== White Sword ===` + contenido (fichas de Items) |
| Párrafo | `sidebar` | `Título: contenido` (como encabezado "robaría" el texto que sigue) |

**Plantillas desconocidas:** se descartan y se cuentan en `CleanStats.unknown_templates`, que aparece en `stats.fixed.json`. Un test exige que el conteo sea cero en todo el corpus.

## Tablas

Hay tres formatos de salida, según la tabla.

**Tabla con encabezados:** cada fila se convierte en una línea con pares `Encabezado: valor`, separados por ` | `.

```text
Name: Octorok | HP: 1 / 2 | Damage: 1 | Description: A common enemy and the first enemy ...
```

**Cuadrícula de mapa** (la esquina superior izquierda está vacía y cada fila empieza con una etiqueta): una línea por celda con su coordenada `Columna-Fila`, el mismo formato con que la wiki cita lugares en otras páginas ("dock at D-4").

```text
D-4: In this shop, you can buy (the ability to use) Arrows for 80 rupees, the Magical Shield for 130 rupees...
```

**Sin encabezados:** los valores de la fila.

**Cuadrícula de fichas** (encabezados, datos, encabezados, datos…, como en la página Items de Ninja Gaiden): cada fila de encabezados a mitad de tabla pasa a etiquetar las filas de datos que la siguen.

```text
Time Freeze: If you find one of these rare hourglasses... | Health: ... Collect one of these potions to restore six lost bars of health
```

Antes solo se usaba la primera fila de encabezados, así que todos los ítems quedaban etiquetados como "Bonus points:" o "Spirit points:". Si una fila de encabezados no tiene datos debajo (p. ej. una tabla de navegación hecha solo de celdas `!`), sale como texto plano.

Reglas comunes:
- `colspan` y `rowspan` se expanden antes de asignar columnas: la celda queda en su primera columna y las posiciones que ocupa se dejan vacías. Sin esto, una celda con `rowspan` desplaza todas las celdas de la fila siguiente a la columna equivocada.
- Se quitan los atributos de celda (`width="10%"| valor`).
- Las listas dentro de una celda (`*a` `*b`) pasan a `a; b`.
- Se descartan los valores sin caracteres alfanuméricos (`/`, `+*`, `—`), que son restos de las columnas de otras consolas vaciadas.
- Las columnas de imagen quedan vacías y se omiten.
- Si una fila no tiene la misma cantidad de celdas que los encabezados, se escriben solo los valores.

**Caso de la tabla de controles de Zelda:** tiene una columna por consola. Al descartar los botones de las demás consolas, cada fila queda como `NES: Start | Action: Bring up the sub-screen menu...`.

## Validación contra el original

Se midió qué palabras del wikitext original no aparecen en el texto limpio, descontando lo que se elimina a propósito (imágenes, galerías, mapas clicables, nombres de plantillas y atributos).

| | Palabras conservadas |
| --- | ---: |
| Zelda | 98.2% |
| Ninja Gaiden | 98.6% |

Lo restante corresponde a rutas de enlaces (`[[The Legend of Zelda/Underworld/...|texto]]` conserva solo `texto`), nombres de archivos de imagen y restos de atributos sin espacios (`width="24%"`), es decir, artefactos de la propia medición.

La validación encontró y corrigió dos pérdidas reales:
1. **La ficha `{{Game}}` se descartaba completa** (desarrollador, diseñadores, año, título japonés). Ahora se convierte en líneas `Campo: valor`.
2. **Las cuadrículas de los mapas perdían las coordenadas.** "B-2" quedaba como `2 | texto`, sin la columna, y un `rowspan` desplazaba las columnas de la fila siguiente. Ahora se emite `B-2: texto` y se expanden los spans.

Los hechos verificados a mano quedaron como test permanente (`KNOWN_FACTS` en [tests/test_ingest.py](../../tests/test_ingest.py)).

## Limitaciones conocidas

- Las coordenadas de mapas ("B-3, section six") se conservan como texto, pero sin la imagen tienen valor limitado.
- La última fila de la tabla de controles ("Switch between controller 1 and 2") es exclusiva de 3DS. Queda sin botón de NES, solo con la acción.
