# Información sensible, gobernanza de datos y decisiones de diseño

Cubre el §5.2 (fuentes autorizadas, versión, frecuencia, tratamiento de información sensible) y la regla de gobernanza
del §15. Complementa [sources.md](sources.md) (fuentes y licencias) y [../security/controls.md](../security/controls.md)
(controles). Las pruebas medidas están en [../security/report.md](../security/report.md).

## 1. Qué datos maneja el sistema y cuáles son sensibles

| Dato | Origen | ¿Sensible? | Dónde vive | Tratamiento |
| --- | --- | --- | --- | --- |
| Corpus (wikis de juegos) | Wikis públicas con licencia abierta | No | `data/wiki_snapshot/` (en el repo, con atribución) | Escaneo de inyección en la ingesta; chunks con instrucciones para un modelo van a cuarentena ([report.md](../security/report.md)) |
| Manuales oficiales (© Nintendo) | Descarga pública | No personal, pero con copyright | `data/raw/` (gitignored) | **Descartados** y nunca versionados |
| Pregunta del usuario | Entrada libre | **Puede** contener PII o secretos pegados por error | Memoria; auditoría; caché del LLM | `PIIGuard` la redacta **antes** del recuperador y del LLM; la auditoría redacta de nuevo |
| Perfil de progreso | Semilla / confirmación humana | Bajo: pseudónimo + niveles; sin nombre, correo ni contacto | SQLite `state/` (gitignored) | Mínimo necesario; `/profiles` lista los perfiles de demo (pseudónimos, sin datos personales); la auditoría es solo para `admin` |
| Trazas de auditoría | Pipeline | Medio: preguntas (ya redactadas) y decisiones | SQLite `state/` | PII redactada, retención de 90 días, acceso solo `admin` |
| Clave de API de Anthropic | Entorno | **Crítico** | `.env` (gitignored); nunca en el repo | Nunca se registra ni se devuelve; el patrón `sk-ant-…` se redacta si alguien la pega en una pregunta |
| Caché y libro de costos del LLM | `gamerag/llm.py` | Bajo (contiene la pregunta ya redactada y fragmentos públicos) | `state/llm_cache/`, `state/llm_usage.sqlite3` (gitignored) | No salen de la máquina |

No hay datos personales reales en el corpus ni en los bancos de evaluación. Los casos de PII de la suite de seguridad usan
valores inventados.

## 2. Qué sale del sistema hacia un tercero (Anthropic)

Para generar, evaluar la evidencia o descomponer la consulta, el sistema llama a la API de Claude. Lo que **sí** se envía:
la pregunta ya redactada, el juego y fragmentos públicos del corpus. Lo que **no** se envía: el perfil de progreso, el
`user_id`, el rol, la clave del usuario, fragmentos bloqueados por los gates (se filtran **antes** de construir el prompt)
ni otras preguntas. Esto es una propiedad del diseño, no de una política: los gates y el `PIIGuard` corren antes del
generador, y las pruebas de la suite de seguridad verifican que el contenido bloqueado no llega al modelo (0/44 sondas,
frente a 42/44 sin gates).

## 3. Controles de información sensible

1. **Minimización:** el perfil guarda solo `user_id` pseudónimo, rol, progreso y nivel de pista. La API no pide nombre ni correo.
2. **Redacción en la entrada** (`guardrails/injection.py::PIIGuard`): correo, teléfono, tarjeta, identificador y claves de
   API se reemplazan por marcadores (`[EMAIL]`, `[SECRET]`, …). La pregunta redactada es la que ven el recuperador, el LLM
   y la caché; la pregunta original no se guarda. Falsos positivos medidos: 0 de 249 preguntas legítimas.
3. **Redacción en el log** (`store.py::redact_pii`): segunda barrera independiente sobre la pregunta y sus reformulaciones
   (variantes, subconsultas, reescrituras del evaluador).
4. **Control de acceso:** `/audit` y `/admin/*` (restablecer perfiles, purgar auditoría) exigen rol `admin`; un `player`
   recibe 403 (comprobado en la suite). `/profiles` es público porque solo contiene perfiles de demostración sin datos personales.
5. **Retención:** `audit_retention_days` (90 por defecto) se aplica al arrancar y con `POST /admin/purge-audit`.
6. **Credenciales:** `.env` está en `.gitignore`; `.env.example` no trae valores; el escaneo del repo no encontró claves.
7. **Salida:** `LeakGuard` bloquea respuestas que contengan el prompt del sistema o secretos.
8. **Sin datos confidenciales reales:** el proyecto no usa información confidencial de ninguna organización (nota del §4).

## 4. Decisiones de diseño sobre las fuentes

| Aspecto (§5.2) | Decisión | Razón |
| --- | --- | --- |
| Fuente formal | Wikis públicas: StrategyWiki, Wikipedia, Grand Theft Wiki, wikis de Fandom, Zeldapedia y ZeldaWiki; lista y URLs en `config/sources.yaml` | Acceso legal, contenido estructurado y licencias abiertas |
| Permiso de uso | CC BY-SA 3.0/4.0; las wikis de Zelda son GFDL y se mantienen separadas y atribuidas | Copyleft: se conserva la atribución por página (`manifest.json`: URL y `revid`) |
| Formato nativo | Wikitext (API de MediaWiki) | Preserva secciones, tablas y plantillas que la ingesta aprovecha |
| Versión | `revid` por página y fecha de descarga; el snapshot versionado es la referencia de la evaluación | Reproducibilidad: volver a descargar puede cambiar el corpus y los números |
| **Frecuencia de actualización** | **Decisión de diseño: snapshot estático, sin actualización automática.** Se refresca a mano con `scripts/fetch_corpus.py` y, si cambia, se rehace la evaluación | Las guías de juegos retro casi no cambian; un corpus congelado hace comparables todas las corridas del marcador. Un flujo de actualización continua añadiría complejidad (detectar cambios, reindexar, revalidar los gates) sin beneficio para este dominio |
| Información sensible en las fuentes | No aplica: son páginas públicas sin datos personales; se escanean en busca de instrucciones dirigidas a un modelo (1 de 10 462 chunks marcado, falso positivo revisado a mano) | El riesgo del corpus es la inyección indirecta, no la privacidad |
| Contenido restringido por spoilers | Los chunks de wikis extra sin ubicación quedan `restricted` hasta etiquetarlos; el filtro de procedencia oculta notas derivadas de contenido bloqueado | El "permiso" relevante en este sistema es qué puede ver cada jugador según su progreso |

## 5. Límites conocidos

- La redacción por patrones no detecta nombres propios ni direcciones; cubre lo estructurado (correo, teléfono, tarjeta,
  identificadores, claves).
- La caché del LLM guarda la pregunta redactada en disco sin cifrar; vive en `state/` (gitignored) y se borra con la carpeta.
- No hay autenticación real de usuarios: el rol se toma del perfil indicado (`user_id`). Es suficiente para la demo del
  curso; un despliegue real necesitaría autenticación delante de la API.
