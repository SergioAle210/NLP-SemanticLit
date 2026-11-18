# Plan de la presentación final

Organizamos la defensa de quince minutos a partir de las veinte diapositivas de la [presentación del equipo](presentacion-equipo.pdf). Numeramos las diapositivas por su posición en el PDF. La demostración se realiza en la aplicación después de la diapositiva 13 y antes de la 14; no requiere una diapositiva adicional. Este documento es un plan vigente, no un registro de ensayo ni de defensa realizada.

Seguimos los seis bloques del §13 de las [instrucciones](instructions.md). El [guion de defensa](defensa.md) desarrolla los casos, la preparación y el diagnóstico de fallas. Las cifras proceden del [informe final](informe-final.md), los [resultados históricos](../evaluation/scorecard.md), la [auditoría de evaluación](../evaluation/audit-current.md) y el [reporte de seguridad](../security/report.md).

## Distribución de los quince minutos

| Tiempo acumulado | Bloque oficial | Material | Propósito |
| --- | --- | --- | --- |
| 0–2 min | Problema, usuario e hipótesis | Diapositivas 1–6 | Presentar necesidad, alcance, fuentes y metas del equipo |
| 2–5 min | Arquitectura y flujo de datos | Diapositivas 7–13 | Explicar ingesta, recuperación, herramientas, evidencia y decisiones |
| 5–9 min | Demostración funcional en vivo | Pausa después de la diapositiva 13 | Mostrar consulta, cita, abstención, herramienta, seguridad y una falla |
| 9–12 min | Evaluación y métricas | Diapositivas 14–16 | Comparar configuraciones y explicar denominadores y limitaciones |
| 12–14 min | Seguridad, controles y limitaciones | Diapositivas 17–19 | Explicar resultados adversarios, trazabilidad y riesgos |
| 14–15 min | Conclusiones | Diapositiva 20 | Resumir contribuciones y siguientes verificaciones |

La apertura y la descripción técnica deben ser breves para conservar los cuatro minutos de demostración. El ensayo deberá confirmar que el recorrido completo cabe en quince minutos; no contamos aquí con un registro que lo acredite.

## Contenido de las veinte diapositivas

| N.º | Título o tema del PDF | Mensaje que desarrollaremos | Criterio de la rúbrica |
| --- | --- | --- | --- |
| 1 | GameRAG | Presentar proyecto e integrantes, sin consumir el tiempo de explicación técnica | Defensa y comunicación |
| 2 | El jugador necesita una respuesta puntual | Explicar el costo de una instrucción incorrecta y de revelar contenido posterior | Problema, usuario y alcance |
| 3 | Una respuesta que puede verificarse | Formular la hipótesis: recuperar evidencia autorizada y conservar su respaldo permite responder de manera comprobable | Problema y trazabilidad |
| 4 | Alcance académico y límites | Distinguir siete juegos configurados de los dos con evaluación principal; aclarar que no validamos soporte equivalente en español | Alcance e implementación |
| 5 | Corpus con procedencia y revisión | Presentar 2759 fragmentos primarios y 10 462 multifuente; distinguir licencias CC BY-SA y GFDL, sin atribuir una licencia común | Fuentes, datos y gobernanza |
| 6 | Objetivos medibles | Explicar metas propias: acierto de 80 %, precisión de citas de 90 %, dos indicadores de abstención de 90 % y P95 menor de seis segundos | Objetivos y evaluación |
| 7 | Arquitectura RAG de punta a punta | Separar preparación documental y consulta; aclarar que reutilizamos índices hasta que cambian texto, revisión o restricciones | Arquitectura e implementación |
| 8 | Ingesta reproducible | Justificar ventanas de referencia de 225 palabras y solapamiento de 30; distinguir la segmentación por secciones | Ingesta e implementación |
| 9 | Arquitectura de consulta | Explicar las dos rutas: generación documental y respuesta determinista desde filas autorizadas; las herramientas no pasan por el generador | Arquitectura y herramientas |
| 10 | Recuperación léxica y semántica | Explicar BM25, E5 y fusión de posiciones; mencionar la selección de hasta cinco fragmentos y el reranker experimental | Implementación NLP/RAG |
| 11 | Herramientas para tareas concretas | Justificar consultas de hechos y progreso, límites de lectura y ausencia de modificaciones automáticas | Herramientas y orquestación |
| 12 | La cita conserva el contexto exacto | Mostrar fuente, sección, identidad, revisión y texto autorizado; una cita válida no demuestra por sí sola fidelidad | Trazabilidad y formato |
| 13 | Orquestación con decisiones acotadas | Distinguir modo local y flujo ampliado con revisión de evidencia y búsquedas adicionales; anunciar el paso a la aplicación | Herramientas y arquitectura |
| 14 | Bancos con propósitos diferentes | Explicar 54, 21 y 61 consultas, sus denominadores y la diferencia entre acierto, cobertura y ordenamiento | Evaluación |
| 15 | La recuperación híbrida mejora el acceso | Identificar verbalmente las tres configuraciones del gráfico y señalar que se trata de la comparación histórica inicial | Evaluación comparativa |
| 16 | Las citas y la abstención siguen limitando la calidad | Separar precisión de citas, exactitud global de abstención y sensibilidad; reconocer las metas incumplidas | Evaluación y análisis de fallas |
| 17 | Controles de seguridad y fallas observadas | Identificar 12 de 42 en comparación y 37 de 42 con controles; explicar las cinco fallas de abstención | Seguridad y manejo de errores |
| 18 | Trazabilidad y reproducción | Separar 489 pruebas archivadas de las 520 posteriores; delimitar el arranque Docker sin llamadas remotas | Trazabilidad y reproducibilidad |
| 19 | Riesgos que orientan el siguiente trabajo | Explicar curaduría adicional, revisión humana, bancos nuevos y autenticación; las correcciones de mapas ya están implementadas | Seguridad y limitaciones |
| 20 | Contribución y aprendizaje | Relacionar recuperación, evidencia exacta y evaluación independiente con el problema inicial | Conclusiones y defensa |

## Demostración fuera de las diapositivas

Al terminar la diapositiva 13, abrimos la aplicación. Regresamos a la diapositiva 14 al minuto nueve. El recorrido detallado se encuentra en [defensa.md](defensa.md).

1. Consultar White Sword y abrir la evidencia exacta con su revisión.
2. Consultar el jefe del nivel 2 y mostrar la fila autorizada de Dodongo.
3. Mostrar una abstención que se haya comprobado previamente con la configuración elegida.
4. Ejecutar un intento de inyección y una solicitud de cambio de progreso.
5. Diagnosticar una falla real con una respuesta y traza archivadas, identificándolas como evidencia histórica.

La combinación archivada de búsqueda BM25 y extracción permite demostrar abstención ante contexto vacío mediante una consulta sintética sin coincidencias. Ese resultado no prueba comprensión semántica ni debe trasladarse automáticamente a búsqueda híbrida o generación remota. Si elegimos otra configuración, comprobaremos antes su caso de abstención. No asumimos que disponer de una clave o seleccionar el perfil completo demuestre una llamada remota exitosa.

## Cifras y aclaraciones para la exposición

### Diapositiva 15: comparación inicial

Los tres grupos de barras, de izquierda a derecha, representan estas configuraciones. Los rótulos del gráfico identifican cada alternativa; durante la exposición precisaremos la configuración generativa utilizada.

| Configuración histórica | Acierto entre cinco resultados | Precisión de citas |
| --- | ---: | ---: |
| Búsqueda léxica y extracción | 79.59 % | 26.53 % |
| Búsqueda híbrida y extracción | 95.92 % | 31.29 % |
| Búsqueda híbrida, Haiku y flujo de decisión | 95.92 % | 76.74 % |

La mejora de recuperación es de 16.33 puntos porcentuales. El banco contiene 54 consultas; calculamos el acierto sobre 49 respondibles. Estas cifras no constituyen una nueva medición del código posterior a las correcciones.

### Diapositiva 16: evaluación generativa posterior

El 77.08 % de precisión de citas corresponde a otra corrida histórica del banco principal y no sustituye el 76.74 % de la comparación inicial. Obtuvimos tres abstenciones correctas entre cinco preguntas no respondibles: sensibilidad de 60 %, aunque la exactitud global fue 94.44 %. El P95 fue 5.733 segundos en el principal, 9.055 en el difícil y 6.162 en fuentes adicionales. El P95 no es la duración de cada respuesta y excluye transporte HTTP, interfaz, arranque y carga inicial de modelos.

### Diapositiva 17: seguridad

Las barras representan 12 de 42 comportamientos esperados en la configuración de comparación y 37 de 42 con controles. La comparación conserva la restricción por juego, la clasificación de solicitudes y la autorización administrativa; no es un sistema sin ninguna protección. Las cinco fallas corresponden a preguntas sin respaldo que recibieron respuestas extractivas.

Las sondas históricas entregaron contexto bloqueado en 0 de 44 casos con controles y 43 de 44 en comparación. Su detector textual registró cero en ambas configuraciones: por ello no presentamos ese cero como ausencia demostrada de spoilers. El oráculo independiente de contenido obtuvo 7 de 9, sin fugas observadas y con dos omisiones de escenas permitidas; el de variantes obtuvo 2 de 2. En el ensayo de documentos contaminados, el marcador apareció en 5 de 5 sin cuarentena y en ninguno con ella. Todos estos resultados tienen el alcance y la configuración documentados en el reporte.

### Herramientas, abstención y trazabilidad

- El banco de desarrollo de herramientas obtuvo 26 de 26. El segundo banco pasó de 11 de 13 a 13 de 13 después de corregir sus casos; esa última medición no representa validación independiente. No hubo falsas selecciones de herramientas en 165 consultas documentales.
- El generador extractivo puede abstenerse ante contexto vacío o referencias inválidas. Sus fallas documentadas aparecen cuando recupera texto relacionado que no responde la pregunta. El uso de un modelo remoto tampoco garantiza abstención correcta.
- Las 520 pruebas posteriores y las siete comprobaciones HTTP de mapas se verificaron en consola. El registro previo conserva 489 pruebas y 36 comprobaciones HTTP; no contiene las ejecuciones posteriores.
- Los perfiles son de demostración, el control de spoilers utiliza reglas curadas y la derivación a revisión no constituye una aprobación humana realizada.
- Reconocemos la asistencia sustancial de IA declarada en el informe final; no la presentamos como revisión humana independiente.

## Preparación que debe confirmar el equipo

- [ ] Acordar intervenciones y comprobar que cada integrante puede explicar el sistema completo.
- [ ] Confirmar la configuración efectiva, los controles y el funcionamiento de la interfaz.
- [ ] Repetir los casos de demostración, incluido el de abstención, bajo esa configuración.
- [ ] Si se utiliza generación remota, comprobar una llamada exitosa y su trazabilidad; conservar una alternativa local.
- [ ] Preparar la respuesta y la traza archivadas del diagnóstico de falla, con datos sensibles ocultos.
- [ ] Ensayar los seis bloques completos en quince minutos y registrar duración y fallas.
- [ ] Verificar el acceso al video proporcionado y confirmar su contenido y participantes; la presencia del enlace no acredita esa revisión.

No marcamos estas tareas como realizadas sin evidencia del equipo. La demostración en vivo y la defensa conceptual individual siguen siendo requisitos del curso aunque exista un video de presentación.
