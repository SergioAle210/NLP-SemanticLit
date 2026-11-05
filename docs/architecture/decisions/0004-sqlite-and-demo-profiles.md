# ADR-0004: SQLite y perfiles de demo, sin login

**Estado:** aceptado (2026-11-05)

## Contexto

- El log de auditoría es obligatorio (§5.8) y debe sobrevivir a reinicios del contenedor.
- El control de acceso necesita perfiles con progreso.
- El sistema corre localmente con Docker y pocos recursos.

## Decisión

- **SQLite** en un archivo dentro del volumen `state/`. Guarda los perfiles, su progreso, las tablas de datos exactos y el log de auditoría.
- **Sin login ni registro.** Cinco perfiles de demo se siembran al arrancar desde `data/seed/profiles.json`, y la interfaz los ofrece en un selector:

  | Perfil | Rol | Zelda | Ninja Gaiden |
  | --- | --- | --- | --- |
  | `novato` | player | Q1, completados [1], actual 2 | 1-2 |
  | `intermedio` | player | Q1, completados [1-4], actual 5 | 3-2 |
  | `segunda_vuelta` | player | Q2, completados [1-3], actual 4 | — |
  | `completionist` | completionist | Todo | Todo |
  | `admin` | admin | Todo + ingesta y logs | Todo |

- Un endpoint de `admin` restablece los perfiles al estado sembrado, para repetir la demo y la evaluación.

## Alternativas consideradas

- **Postgres.** Requiere otro contenedor y más recursos sin ningún beneficio a esta escala.
- **Estado en memoria** (sesión de Streamlit). Se pierde al recargar y no cumple el requisito de auditoría.
- **Autenticación real.** No la evalúa la rúbrica y consume tiempo; queda como trabajo futuro.

## Consecuencias

- Costo de recursos casi nulo: un archivo de unos KB, sin servidor.
- Los perfiles alcanzan para demostrar y evaluar el control de acceso.
- `state/*.sqlite3` está en `.gitignore`; lo que se versiona son los perfiles sembrados.
