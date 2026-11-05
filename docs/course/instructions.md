# Proyecto Final CC3103: Sistema NLP/RAG Agéntico Empresarial

**Curso:** CC3103 - Procesamiento de Lenguaje Natural  
**Docente:** Luis Esturbán  
**Valor:** 30% de la nota final  
**Modalidad:** Equipos de 3 a 4 estudiantes  
**Fuente:** Documento oficial del proyecto final (PDF, 10 páginas).

## 1. Descripción general

El equipo debe **diseñar, implementar, evaluar y defender** un sistema de procesamiento de lenguaje natural aplicado a un problema realista de una organización.

Se deben integrar, de manera justificada, los conocimientos trabajados durante el curso:

- Texto y preprocesamiento.
- Representación vectorial.
- Transformers o modelos modernos de NLP.
- Recuperación documental.
- Generación fundamentada.
- Herramientas o agentes.
- Evaluación.
- Seguridad y trazabilidad.

**Criterio central:** no basta con conectar un modelo de lenguaje a una interfaz y llamarlo «agente». Se requiere un problema definido, fuentes autorizadas, una arquitectura explicable, métricas, pruebas reproducibles y controles de seguridad.

## 2. Relación con el programa del curso

El proyecto integra cuatro competencias:

1. **Representación semántica:** tokenización, embeddings, similitud y búsqueda.
2. **Transformers:** uso de modelos preentrenados para tareas de NLP.
3. **Sistemas de diálogo y recuperación:** RAG, chunking, metadatos, reranking y prompting.
4. **Agentes, evaluación y despliegue:** herramientas, flujos de estado, métricas y seguridad.

El criterio oficial es diseñar, validar, medir y defender una solución agéntica corporativa de NLP, orientada a un problema real y respaldada por metodologías robustas de alineación y seguridad.

## 3. Resultados esperados

Al finalizar, el equipo debe poder:

- Formular un problema concreto de NLP.
- Identificar usuarios, fuentes y restricciones.
- Diseñar una arquitectura técnica coherente.
- Implementar una línea base reproducible.
- Incorporar recuperación semántica o híbrida cuando corresponda.
- Usar RAG con fuentes y metadatos verificables.
- Integrar al menos una herramienta externa cuando el problema lo justifique.
- Orquestar un flujo con estado, reglas y límites.
- Evaluar recuperación, generación, operación y seguridad.
- Analizar fallas y proponer mejoras basadas en evidencia.
- Defender decisiones técnicas y éticas.

## 4. Temas posibles

El equipo puede elegir otro dominio si cuenta con acceso legal a las fuentes y puede evaluar los resultados.

| Dominio sugerido | Descripción de la aplicación |
| --- | --- |
| Asistente institucional | Consultar reglamentos, procesos y políticas internas de la organización. |
| Soporte de TI | Analizar, clasificar y asistir en la resolución de tickets técnicos. |
| Documentación técnica | Consultar manuales de operación o documentación de software. |
| Gestión humana | Consultar políticas internas, beneficios y procedimientos para colaboradores. |
| Análisis de clientes | Clasificar y resumir estructuradamente reseñas y comentarios. |
| Gestión legal/contratos | Analizar y extraer información de contratos previamente autorizados. |
| Literatura científica | Buscar y sintetizar información temática de corpus de acceso abierto. |
| Triage operativo | Clasificar y enrutar inicialmente solicitudes internas no sensibles. |
| Reportería | Analizar y resumir métricas de reportes operativos periódicos. |

**Restricción:** no se permiten proyectos con información confidencial real sin autorización y protección demostrables.

## 5. Requisitos mínimos del sistema

### 5.1. Problema y usuario

Definir explícitamente:

- Usuario primario.
- Problema actual y contexto operativo.
- Tarea que se desea mejorar.
- Costo e impacto de una respuesta incorrecta.
- Alcance operativo y límites de cobertura.
- Criterio explícito de éxito.

### 5.2. Fuentes autorizadas

Documentar para cada fuente:

- Fuente formal del documento o registro.
- Permiso de uso legal o institucional.
- Formato nativo del dato.
- Fecha o versión del recurso.
- Frecuencia estimada de actualización.
- Mecanismos de tratamiento de información sensible.

### 5.3. Pipeline de ingesta

Construir un proceso programático y reproducible con estas fases:

1. **Carga:** conectar y leer el repositorio de origen.
2. **Extracción:** analizar el contenido textual y estructural.
3. **Limpieza:** normalizar, remover ruido y sanear el texto.
4. **Segmentación (chunking):** dividir en fragmentos con una estrategia justificada según el dominio.
5. **Metadatos:** enriquecer cada fragmento con contexto.
6. **Indexación:** almacenar en un motor vectorial o léxico.

Los fragmentos (`chunks`) deben conservar, como mínimo:

```json
{
  "text": "Contenido del fragmento",
  "source": "documento_origen.pdf",
  "page": 1,
  "chunk_id": "identificador_del_fragmento",
  "version": "version_del_documento"
}
```

> Este JSON es una representación ilustrativa de los campos obligatorios. El PDF no impone un tipo específico para `chunk_id` o `version`.

### 5.4. Recuperación

Justificar formalmente la estrategia seleccionada, entre otras:

- Búsqueda semántica pura.
- Búsqueda léxica.
- Búsqueda híbrida.
- Filtros por metadatos.
- Reranking.
- Diversidad mediante MMR.

**No es obligatorio implementar todas las variantes**, pero sí sustentar la elección técnica.

### 5.5. Generación fundamentada

Las respuestas deben:

- Emplear estrictamente el contexto recuperado como respaldo.
- Declarar cuándo no exista evidencia documental suficiente (abstención).
- Conservar y referenciar citas correspondientes.
- Evitar afirmaciones sin sustento en el corpus.
- Respetar el formato contractual de salida predefinido.

### 5.6. Herramienta o flujo agéntico

Implementar **al menos una** de las siguientes opciones:

1. **Herramienta externa:** API, base de datos SQL, motor de cálculo, clasificador o validador.
2. **Flujo de decisión:** enrutamiento condicional entre recuperación documental y otras acciones.
3. **Agente autónomo:** planificación de pasos y ejecución de herramientas bajo límites estrictos.

La alternativa elegida debe ser realmente necesaria para resolver el problema. No se aceptan agentes sin justificación funcional.

### 5.7. Evaluación

Construir un banco de pruebas representativo y reportar métricas **cuantitativas y cualitativas** de desempeño.

### 5.8. Seguridad

Incluir obligatoriamente:

- Validación estructurada de las entradas.
- Control de acceso a documentos y gestión de permisos.
- Mitigación activa de inyecciones de prompt.
- Validación y verificación de las salidas.
- Límites de llamadas y alcance para herramientas externas.
- Procedimiento para preguntas fuera de dominio o sin respuesta.
- Sanitización de información confidencial en logs de auditoría.

## 6. Arquitectura requerida

Se debe entregar un diagrama arquitectónico formal con **dos flujos**:

**Flujo de usuario:**

```text
Usuario
  -> Guardrails de entrada
  -> Router / análisis de intención
  -> Recuperación / herramienta / agente
  -> Validación de permisos
  -> Evidencia o resultado de herramienta
  -> Generación estructurada
  -> Guardrails de salida
  -> Respuesta final y trazabilidad
```

**Flujo de ingesta:**

```text
Fuentes originales
  -> Extracción de texto
  -> Limpieza
  -> Segmentación (chunking)
  -> Metadatos y versionado
  -> Embeddings / índice léxico
```

El diagrama debe identificar entradas, salidas, estado compartido, herramientas, índices, compuertas de decisión, puntos de validación, manejo de excepciones y control de acceso.

## 7. Fases del proyecto

| Fase | Denominación | Actividades y entregables clave |
| --- | --- | --- |
| 1 | Anteproyecto | Formular el problema, caracterizar al usuario, definir datos y alcance, diseñar arquitectura inicial, elaborar matriz de riesgos y métricas objetivo. |
| 2 | Línea base | Implementar la variante mínima medible: búsqueda léxica, clasificador elemental, RAG vectorial básico o prompt estructurado sin memoria. |
| 3 | Mejora técnica | Incorporar componentes justificados: mejores embeddings, recuperación híbrida, reranking, filtros de metadatos, herramientas o agentes. |
| 4 | Evaluación | Configurar el banco oficial de pruebas y comparar cuantitativamente línea base y versión mejorada. |
| 5 | Seguridad | Ejecutar pruebas adversarias de inyección, evasión de permisos, envenenamiento de fuentes, salidas no conformes y ejecución indebida. |
| 6 | Demostración y defensa | Sustentación técnica, demo funcional, métricas observadas, análisis de fallas y justificación de decisiones de diseño. |

## 8. Banco de pruebas

Se exige un conjunto de validación de **al menos 20 casos** con esta distribución:

| Tipo de prueba | Cantidad |
| --- | ---: |
| Preguntas directas con respuesta unívoca | 5 |
| Formulaciones con paráfrasis semántica | 3 |
| Consultas con identificadores léxicos exactos | 3 |
| Preguntas compuestas de partes múltiples | 3 |
| Escenarios con ambigüedad contextual | 2 |
| Casos sin respuesta posible en el corpus (abstención obligatoria) | 2 |
| Consultas dependientes de vigencia temporal o versión documental | 2 |
| **Total mínimo** | **20** |

Si se implementan herramientas externas, añadir casos para:

- Ejecución nominal.
- Selección errónea de herramienta.
- Parámetros fuera de rango.
- Acciones que requieran confirmación humana explícita.
- Degradación controlada ante indisponibilidad del servicio.

Cada registro del dataset debe contener **exactamente estos atributos requeridos, como mínimo**:

```json
{
  "id": "case_001",
  "question": "Pregunta del caso",
  "expected_behavior": "Comportamiento esperado del sistema",
  "expected_sources": ["fuente_relevante.pdf"],
  "expected_pages": [1],
  "answerable": true,
  "risk_level": "nivel_de_riesgo"
}
```

> Los valores del ejemplo son ilustrativos; el PDF define los nombres de los campos, pero no especifica un catálogo cerrado de niveles de riesgo.

## 9. Métricas mínimas

| Dimensión | Métricas y criterios de evaluación |
| --- | --- |
| Recuperación | Recall@k, posición del primer fragmento relevante (MRR) y redundancia/ruido contextual. |
| Respuesta | Fidelidad, cobertura fáctica, relevancia, precisión de citas y tasa de abstención cuando falta evidencia. |
| Operación | Latencia media, percentil 95 (P95), consumo de tokens, número de invocaciones al modelo y costo estimado. |
| Seguridad | Proporción de ataques bloqueados, denegaciones de acceso correctas, detección de salidas defectuosas y control de acciones críticas. |

La evaluación debe permitir contrastar **línea base** y **versión mejorada**.

## 10. Pruebas de seguridad

Diseñar casos adversarios para:

1. **Inyección de instrucciones:** intentos directos o indirectos de ignorar instrucciones y divulgar directrices internas o datos protegidos.
2. **Evasión de permisos:** consultas a documentación restringida o asignada a otros perfiles.
3. **Acciones críticas:** intentos de ejecutar operaciones sensibles sin autorización humana.
4. **Alucinación forzada:** preguntas que buscan obtener afirmaciones sin sustento documental.

Cada prueba debe documentar:

- Amenaza.
- Componente afectado.
- Comportamiento esperado.
- Resultado observado.
- Mitigación implementada.

## 11. Formato de salida

La respuesta del sistema debe cumplir un contrato validado con **Pydantic o JSON Schema**, que incluya:

- `answer` (`string`): respuesta redactada y fundamentada.
- `sources` (`array`): referencias con fuente, página y `chunk_id`.
- `abstained` (`boolean`): si se abstuvo por falta de evidencia.
- `tool_used` (`string` o `null`): herramienta invocada, si la hay.
- `needs_human_review` (`boolean`): si requiere escalamiento humano por incertidumbre o riesgo.

Ejemplo **ilustrativo** de estructura:

```json
{
  "answer": "Respuesta basada en la evidencia disponible.",
  "sources": [
    {"source": "manual.pdf", "page": 4, "chunk_id": 18}
  ],
  "abstained": false,
  "tool_used": null,
  "needs_human_review": false
}
```

## 12. Entregables finales

1. **Documento técnico (10 a 15 páginas):** resumen ejecutivo, problema, perfiles de usuario, fuentes, estado del arte, arquitectura detallada, banco de pruebas, métricas, auditoría de seguridad, limitaciones, trabajo futuro, conclusiones y bibliografía técnica.
2. **Código fuente:** repositorio estructurado con `README`, dependencias, configuración de entorno sin credenciales, pipelines reproducibles y scripts automatizados de benchmark.
3. **Dataset de evaluación:** archivo con casos estructurados, metadatos, fuentes esperadas y registros de resultados comparativos.
4. **Demostración práctica:** ejecución funcional en vivo que cubra consulta nominal, citas, abstención, herramientas, prueba de seguridad y diagnóstico de una falla real.
5. **Defensa oral:** explicación conceptual individual y resolución de preguntas técnicas del docente.

## 13. Presentación final: 15 minutos

| Bloque | Contenido | Tiempo |
| --- | --- | ---: |
| 1 | Problema, usuario e hipótesis | 2 min |
| 2 | Arquitectura del sistema y flujo de datos | 3 min |
| 3 | Demostración funcional en vivo | 4 min |
| 4 | Análisis de evaluación y métricas | 3 min |
| 5 | Pruebas de seguridad, guardrails y limitaciones | 2 min |
| 6 | Conclusiones y cierre | 1 min |
| **Total** | | **15 min** |

## 14. Rúbrica de evaluación

| Criterio | Puntos |
| --- | ---: |
| Problema, usuario y alcance | 10 |
| Fuentes, datos y gobernanza | 10 |
| Arquitectura y coherencia técnica | 15 |
| Implementación NLP/RAG | 15 |
| Herramientas y orquestación agéntica | 10 |
| Evaluación y métricas | 15 |
| Seguridad, guardrails y manejo de errores | 15 |
| Trazabilidad y formato estructurado | 5 |
| Documentación y reproducibilidad | 3 |
| Defensa individual y comunicación | 2 |
| **Total** | **100** |

Esta rúbrica representa el **30% de la nota final** del curso.

## 15. Reglas de integridad y uso de IA

- **Transparencia ética:** documentar el uso de herramientas generativas y su grado de intervención.
- **Dominio técnico:** cada integrante debe comprender y poder depurar el código entregado.
- **Reconocimiento académico:** citar fuentes, librerías, arquitecturas base y bibliografía externa.
- **Gobernanza de datos:** no incluir datos confidenciales sin autorización ni exponer credenciales o API keys en repositorios públicos o privados.

## 16. Criterio de éxito del proyecto

Un proyecto sólido no depende de cuántos componentes implemente, sino de demostrar:

**Problema claro + datos autorizados + arquitectura justificada + implementación funcional + evaluación reproducible + seguridad verificable + defensa técnica.**

---

*Documento Markdown estructurado a partir del PDF oficial «Proyecto Final CC3103: Sistema NLP/RAG Agéntico Empresarial». Los fragmentos JSON son ejemplos explicativos y no copias de código impuesto por la guía.*
