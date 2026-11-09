# Interfaz "Puesto de Control" (Gradio)

Interfaz sobre la [API](../api/README.md), con el diseño del sistema de diseño **Puesto de Control**: una mesa de
inspección donde el jugador presenta su pasaporte (perfil y progreso), entrega una consulta y recibe un expediente con
su sello. Reemplaza a la interfaz mínima de Streamlit.

## Uso

```bash
uv run uvicorn gamerag.api:app                     # terminal 1: API en :8000
uv run --extra ui python -m gamerag.ui.puesto      # terminal 2: interfaz en :7860
```

| Variable | Default | Para qué |
| --- | --- | --- |
| `GAMERAG_API_URL` | `http://127.0.0.1:8000` | Dirección de la API (en Docker, el nombre del servicio) |
| `GAMERAG_UI_DEFAULT_GAME` | `zelda1` | Juego preseleccionado |
| `GAMERAG_UI_HOST`, `GAMERAG_UI_PORT` | `127.0.0.1`, `7860` | Dónde escucha la interfaz |

Para ver el perfil `full` (Haiku, grafo, segunda búsqueda) arranca la API con `GAMERAG_PROFILE=full` y una clave en `.env`.
Sin conexión a internet, la API necesita `HF_HUB_OFFLINE=1` para usar el modelo de embeddings en caché.

## Pantallas

- **Ventanilla.** Juego y perfil del viajero; su **pasaporte** (barra de progreso con texto alternativo, pista, rol);
  la **bandeja de pruebas** (inyección, spoiler, acción crítica, dato personal, sin evidencia) que rellena la consulta
  con un ataque de la suite de seguridad; el campo de consulta (500 caracteres) y **Entregar**. El resultado es un
  **expediente** con sello (Aprobado, Sin evidencia, Bloqueado, Rechazado, Revisión humana), respuesta con citas
  numeradas que se abren al fragmento exacto, y pie con generador, latencia, ruta y herramienta. Debajo, el
  **reglamento de inspección**: la explicación paso a paso (`explain`), donde el contenido retenido se cuenta pero
  nunca se nombra. Opción "Solo buscar" para ver el contexto sin generar.
- **Archivo.** Registro de consultas con datos personales redactados (`GET /audit`); solo perfil `admin`.
- **Informe.** Marcador de evaluación (`GET /scorecard`): Recall@5, cobertura, fidelidad, abstención, fugas de spoiler y
  falso disparo del router, cada una con su veredicto.
- **Telegrama.** Pie con el identificador de traza, ruta, latencia, generador y resultado de la última consulta.
- **Turno de día/noche.** Un botón alterna los dos turnos del sistema de diseño (modo oscuro de Gradio = noche).

## Diseño de la implementación

- **Solo habla con la API** ([client.py](../../src/gamerag/ui/client.py)); nunca importa el pipeline.
- **Tema generado desde `tokens.json`** ([theme.py](../../src/gamerag/ui/theme.py)): copia del sistema de diseño. Los
  cambios de diseño se hacen allí y se copian aquí (`tokens.json`, `puesto.css`).
- **Componentes como funciones puras** ([components.py](../../src/gamerag/ui/components.py)). **Todo texto dinámico se
  escapa** (`html.escape`): la respuesta de un LLM y el corpus no son confiables y estas cadenas se inyectan como HTML.
  Lo verifica un test con `<script>` en cada campo.
- **Accesibilidad:** texto mínimo de 15 px en `rem`, foco de dos tonos, objetivos de 44 px, alternativas de texto en
  barras y bloques tachados, alto contraste de Windows (glifos de texto), y sin movimiento con `prefers-reduced-motion`.
- **Pruebas** ([tests/test_ui_puesto.py](../../tests/test_ui_puesto.py)): componentes, veredictos, escape y los
  manejadores contra la API real en memoria.

## Pendiente

- No pude abrir la interfaz renderizada en el navegador integrado (navegación a localhost denegada): el aspecto visual
  y la ruta de teclado y lector de pantalla están sin verificar. Abre `http://127.0.0.1:7860` y revisa los dos turnos.
