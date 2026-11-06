# Interfaz mínima (Streamlit)

Interfaz de demo y depuración sobre la [API](../api/README.md). El diseño definitivo se hace aparte, contra los mismos endpoints.

## Uso

```bash
uv run uvicorn gamerag.api:app                     # terminal 1: API en :8000
uv run streamlit run src/gamerag/ui/app.py         # terminal 2: interfaz en :8501
```

| Variable | Default | Para qué |
| --- | --- | --- |
| `GAMERAG_API_URL` | `http://127.0.0.1:8000` | Dirección de la API (en Docker, el nombre del servicio) |
| `GAMERAG_UI_DEFAULT_GAME` | `zelda1` | Juego preseleccionado |

## Qué muestra

- **Barra lateral:** estado de la API (versión, recuperador y generador servidos), juego, perfil con su progreso y modo:
  - **Responder** (`POST /ask`): respuesta con citas. Una respuesta bloqueada por spoiler se muestra con 🔒 y una abstención, como información.
  - **Solo buscar** (`POST /search`): el contexto que recibiría el generador, sin generar.
- **Contexto recuperado:** los fragmentos con su página, sección, score RRF, `chunk_id` y enlace a la wiki. Una sección larga se divide en varios chunks con el mismo nombre; por eso la etiqueta incluye el `chunk_id` y el inicio del texto.
- **Traza:** variantes de la consulta (multi-consulta), guards de entrada y de salida, latencia por etapa, candidatos con `blocked_by` y contexto entregado.
- **Auditoría** (perfil `admin`): últimas consultas desde `GET /audit`, con la PII redactada.

## Diseño

- **La interfaz solo habla con la API;** nunca importa el pipeline. Así se puede reemplazar por otro frontend sin tocar el backend, y lo que se ve en la interfaz es lo mismo que sirve la API.
- **En el modo Responder, el texto del contexto sale de `/search`,** porque `/ask` devuelve solo las citas. La búsqueda es determinista, así que el contexto coincide con el que usó `/ask`. Lo verifica un test (`test_ask_and_search_return_the_same_context`).
- **Cliente HTTP separado** ([client.py](../../src/gamerag/ui/client.py)): se prueba contra la API real en memoria sin necesidad de Streamlit ([tests/test_ui_client.py](../../tests/test_ui_client.py)). `app.py` solo dibuja.
- **API caída o con errores:** el cliente convierte los fallos de conexión y los códigos 4xx en `ApiError`, y la interfaz los muestra como mensajes, no como trazas de Python.

## Verificación de punta a punta

Se manejó la interfaz con `streamlit.testing.AppTest` contra la API real (híbrida e5, estructural, multi-consulta):
- en Zelda, las mismas preguntas exploratorias dan los mismos ranks que el pipeline (Boomerang rank 1; Shields rank 1);
- en Ninja Gaiden, "Bomberhead" trae primero el Stage 2-3;
- con el perfil `admin`, la auditoría funciona.

Esa prueba encontró un error: el juego preseleccionado era el primero en orden alfabético (Ninja Gaiden), y las preguntas de Zelda se buscaban en NG. Se corrigió con `GAMERAG_UI_DEFAULT_GAME`. De paso confirmó que el gate G1 funciona, porque no se coló ningún fragmento de Zelda.
