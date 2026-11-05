# Diseño, Implementación y Defensa de un Sistema NLP/RAG Agéntico

**Curso:** CC3103 - Procesamiento de Lenguaje Natural  
**Ciclo:** 2-2026  
**Docente:** Luis Esturbán  
**Institución:** Universidad del Valle de Guatemala  
**Ponderación:** 30% de la nota final  
**Fuente:** Presentación «CC3103 - Procesamiento de Lenguaje Natural» (20 diapositivas).

Guía integral para construir sistemas de lenguaje confiables, verificables y orientados a producción.

## Diapositiva 1. Portada

**Diseño, Implementación y Defensa de un Sistema NLP/RAG Agéntico.**

Guía integral para la construcción de sistemas de lenguaje confiables, verificables y orientados a producción.

- Curso: CC3103 - Procesamiento de Lenguaje Natural.
- Ciclo: 2-2026.
- Docente: Luis Esturbán.
- Institución: Universidad del Valle de Guatemala.
- Ponderación: 30% de la nota final.

## Diapositiva 2. ¿Qué vamos a construir?

**Propósito del proyecto:** construir un sistema NLP que resuelva un problema realista con datos autorizados, modelos de lenguaje y componentes verificables.

| Elemento | Enfoque |
| --- | --- |
| 1. Problema | Necesidad concreta. |
| 2. Datos | Fuentes autorizadas. |
| 3. RAG/NLP | Pipeline robusto. |
| 4. Agentes | Uso de herramientas. |
| 5. Seguridad | Validación continua. |

## Diapositiva 3. El proyecto no es solamente un chatbot

### Enfoque insuficiente: demo simplista

```text
pregunta -> LLM -> respuesta
```

Un demo que responde de forma persuasiva no equivale a un sistema confiable para producción.

### Requisito del curso: sistema verificable

- **Problema y usuario:** especificación del impacto real.
- **Fuentes autorizadas:** recuperación con citas exactas.
- **Control de alucinación:** política activa de abstención.
- **Métricas formales:** evaluación cuantitativa y riesgos.

## Diapositiva 4. Integración del curso y entregables

No es obligatorio usar todas las técnicas, pero sí justificar rigurosamente cuáles son necesarias.

**Fundamentos integrados:**

- Embeddings.
- Transformers.
- Búsqueda híbrida.
- Reranking.
- Agentes y herramientas (tools).
- Guardrails.

**Paquete de entrega:**

- Documento técnico: 10 a 15 páginas formales.
- Código fuente: totalmente reproducible y documentado con README.
- Banco de pruebas: mínimo 20 casos estructurados.
- Pruebas de seguridad: inyección y permisos.
- Defensa: demostración en vivo de 15 minutos.

## Diapositiva 5. Definición del problema: débil vs. fuerte

**Formulación débil:**

> «Crear un chatbot empresarial con inteligencia artificial».

Es ambigua porque no define usuario, tarea, fuente autorizada ni métrica de éxito.

**Formulación fuerte:**

> «Ayudar al personal de soporte a localizar procedimientos vigentes en manuales internos y responder con citas verificables».

Es precisa porque delimita el rol del usuario, el corpus cerrado y el estándar de salida.

## Diapositiva 6. Definición del usuario y objetivos medibles

- **Perfil de usuario:** definir nivel técnico y permisos.
- **Impacto de falla:** identificar el riesgo de respuestas incorrectas.
- **Meta medible de ejemplo:** `Recall@5 >= 0.80` con citas de página.

> El valor `Recall@5 >= 0.80` se muestra como objetivo ilustrativo en la presentación, no como umbral mínimo universal establecido en el PDF.

## Diapositiva 7. Límites del alcance y enfoque en el MVP

**Regla de oro del MVP:** un proyecto pequeño, completamente integrado y evaluado es infinitamente superior a uno enorme e incompleto.

La diapositiva propone delimitar el sistema a:

1. Una fuente autorizada.
2. Una tarea concreta.
3. Una salida con citas de página.
4. Una métrica formal (`Recall@k`).
5. Una regla de abstención.

**Dentro del alcance (in-scope), como ejemplo:** manuales PDF autorizados, respuestas en español, citas por página y preguntas informativas.

**Fuera del alcance (out-of-scope), como ejemplo:** decisiones legales autónomas, modificación directa de bases de datos o soporte multiidioma no validado.

## Diapositiva 8. Datos autorizados y gobernanza

- **Licencia y permisos:** prohibido usar datos confidenciales o extraídos mediante scraping sin autorización.
- **Control de versiones:** depurar formalmente documentos cuando un manual queda obsoleto.
- **Control de acceso:** aplicar filtros de metadatos por rol para evitar fugas.
- **Auditoría y logs:** anonimizar información personal identificable (PII) en registros del sistema.

## Diapositiva 9. Arquitectura general del pipeline

### Fase A. Ingesta y estructuración

```text
Documentos PDF
  -> Extracción y limpieza
  -> Chunking semántico
  -> Metadatos y hash
  -> Base vectorial / índice
```

### Fase B. Consulta, validación y generación

```text
Consulta (query) + guardrails
  -> Recuperación híbrida
  -> Reranking de chunks
  -> LLM fundamentado (grounded)
  -> Respuesta con citas
```

## Diapositiva 10. ¿Cuándo usar RAG, SQL, API o agentes?

| Necesidad concreta | Componente idóneo | Justificación técnica |
| --- | --- | --- |
| Consultar manuales no estructurados | RAG | Documentación viva, citas requeridas y texto extenso. |
| Contar registros y métricas exactas | SQL / Base de datos | Agregaciones exactas que los LLM suelen generar incorrectamente. |
| Obtener datos en tiempo real | API externa | Estados dinámicos que no residen en el índice vectorial. |
| Operaciones numéricas complejas | Calculadora / Herramienta | Cálculo determinista con validación de tipos. |
| Selección dinámica entre herramientas | Agente / Router | Razonamiento condicional dependiente del contexto. |

## Diapositiva 11. Metadatos y generación fundamentada

**Ejemplo de chunk mostrado en la presentación:**

```json
{
  "text": "Procedimiento de reinicio...",
  "source": "manual_servidores.pdf",
  "page": 4,
  "chunk_id": 18,
  "version": "2026-1",
  "hash": "a1f9e2b8c..."
}
```

El ejemplo ilustra los campos para trazabilidad, incluido el `hash`.

**Recuperación híbrida:** combinación de búsqueda semántica (vectores) y búsqueda léxica (BM25), con reranker.

**Generación fundamentada:** el prompt debe forzar una abstención cuando la evidencia documental recuperada sea insuficiente.

## Diapositiva 12. Diseño de herramientas y ciclo agéntico

### Contrato de una herramienta

Toda herramienta debe disponer de interfaz estricta, permisos acotados y validación de tipos.

Ejemplo de firma incluida en la diapositiva:

```python
search_documents(
    query: str,
    role: UserRole,
    version: str
) -> RetrievalResult
```

### Ciclo de razonamiento

1. **Razonar:** analizar la intención y planificar pasos.
2. **Actuar:** invocar la herramienta precisa.
3. **Observar:** interpretar el resultado recibido.
4. **Decidir:** concluir o solicitar confirmación.

## Diapositiva 13. Banco de pruebas mínimo (20 casos)

| Categoría en la presentación | Casos |
| --- | ---: |
| Preguntas directas sobre hechos | 5 |
| Paráfrasis y reformulaciones | 3 |
| Identificadores y códigos exactos | 3 |
| Consultas de múltiples partes | 3 |
| Casos ambiguos y sin respuesta (abstención) | 4 |
| Variación entre versiones documentales | 2 |
| **Total** | **20** |

> La presentación agrupa cuatro casos ambiguos/sin respuesta. El documento PDF los desglosa en dos casos de ambigüedad contextual y dos casos sin respuesta (abstención obligatoria).

## Diapositiva 14. Métricas de evaluación del sistema

**Recuperación:**

- Recall@k y Precision@k.
- Mean Reciprocal Rank (MRR).
- Cobertura de fuentes relevantes.

**Generación:**

- Fidelidad estricta al contexto.
- Validez de las citas generadas.
- Calidad de la abstención activa.

**Operación:**

- Latencia media y percentil 95.
- Costo estimado por consulta.
- Tasa de errores y reintentos.

## Diapositiva 15. Seguridad, inyecciones y guardrails

### Guardrails de entrada

- Detección de prompt injection.
- Filtrado de datos personales (PII).
- Validación de roles y permisos.
- Rechazo de instrucciones adversariales.

### Guardrails de salida

- Validación del esquema estructurado.
- Verificación de citas contra fuentes.
- Supresión de alucinaciones sin soporte.
- Bloqueo de acciones críticas sin confirmación.

## Diapositiva 16. Manejo de errores y trazabilidad de auditoría

**Principio de transparencia operativa:** un sistema serio nunca enmascara fallas. Debe contemplar índices vacíos, falta de evidencia, respuestas de API inválidas y usuarios no autorizados.

**Cadena auditable en cada llamada:**

```text
pregunta
  -> intención
  -> filtros
  -> candidatos
  -> scores
  -> reranking
  -> contexto
  -> herramienta
  -> respuesta
  -> citas
```

## Diapositiva 17. Matriz de riesgos y mitigaciones

| Riesgo identificado | Impacto | Estrategia de mitigación |
| --- | --- | --- |
| Datos de corpus insuficientes | Alto | Definir fuentes alternativas autorizadas desde el inicio. |
| Baja precisión en recuperación | Alto | Implementar recuperación híbrida y reranking cross-encoder. |
| Inestabilidad en APIs externas | Medio | Diseñar fallbacks automáticos y mocks de respaldo. |
| Fuga de información confidencial | Alto | Aplicar control estricto de acceso basado en metadatos. |
| Alcance excesivo fuera de tiempo | Alto | Delimitar rigurosamente el MVP antes de expandir funcionalidades. |

## Diapositiva 18. Estructura de la defensa (15 minutos)

| Bloque | Contenido | Tiempo |
| --- | --- | ---: |
| Problema | Usuario y necesidad. | 2 min |
| Arquitectura | Decisiones técnicas. | 3 min |
| Demostración | Casos en vivo. | 4 min |
| Evaluación | Métricas y fallas. | 3 min |
| Seguridad | Ataques y pruebas. | 2 min |
| Conclusión | Lecciones y roadmap. | 1 min |
| **Total** | | **15 min** |

## Diapositiva 19. Rúbrica de evaluación (100 puntos)

| Criterio | Puntos |
| --- | ---: |
| Problema, usuario y alcance | 10 |
| Datos y gobernanza | 10 |
| Arquitectura del sistema | 15 |
| Implementación NLP / RAG | 15 |
| Herramientas y agentes | 10 |
| Evaluación y métricas formales | 15 |
| Seguridad y guardrails | 15 |
| Trazabilidad y formato | 5 |
| Reproducibilidad del código | 3 |
| Defensa técnica y respuestas | 2 |
| **Total** | **100** |

## Diapositiva 20. Actividad inicial: manifiesto del anteproyecto

Completar en equipo estas cinco frases:

1. **Nuestro usuario es...**
2. **Su problema concreto es...**
3. **La evidencia que utilizaremos está en...**
4. **Demostraremos que funciona mediante...**
5. **El principal riesgo identificado es... y lo mitigaremos mediante...**

---

*Markdown organizado por diapositiva a partir de la presentación del curso. Se mantuvieron sus ejemplos y criterios, diferenciando los ejemplos orientativos de los requisitos obligatorios establecidos en el PDF oficial.*
