# Fixtures de validación

`document_versions.json` contiene un corpus sintético que no describe un videojuego real. El runner
`python -m gamerag.evaluation.versions` materializa dos snapshots documentales con revisiones 101 y 102,
los ingesta mediante el constructor ordinario y vuelve a abrir la misma ruta del índice. La consulta
debe cambiar de «shelf A» a «shelf B», conservando la identidad documental y citando la revisión actual.
`--dense` agrega la comprobación del índice semántico persistido con el modelo configurado localmente.

## Versiones del oráculo de spoilers

Conservamos `eval/security_content_oracle.jsonl` como versión 1 y su corrida inicial del 16 de noviembre
de 2026 en UTC (15 de noviembre en Guatemala). La regla inicial trataba cualquier nombre de objeto
posterior como una fuga. El resultado fue 5/8: un nombre genérico «Magic Key» y dos respuestas
extractivas que truncaron escenas ya permitidas, aunque estaban presentes en la evidencia.

La política declarada del proyecto protege soluciones, asociaciones con ubicaciones futuras y
desenlaces narrativos, y permite consultar mecánicas generales de objetos. Por esa aclaración explícita
creamos `eval/security_content_oracle_v2.jsonl`, sin modificar el banco ni la medición anteriores. La
versión 2 comprueba asociaciones de tesoros con niveles futuros y conserva las restricciones sobre
Silver Arrows y escenas no alcanzadas. Añadimos una consulta directa sobre Magic Key que debe explicar
su función y ocultar la ubicación posterior. Las pruebas positivas de escenas desbloqueadas conservan
la exigencia de aparecer tanto en la evidencia como en la respuesta; un truncamiento extractivo sigue
contando como fallo de disponibilidad.

Estos patrones se evalúan sin llamar a la política de producción ni descontar el contexto que dicha
política haya autorizado. Un patrón detecta las expresiones declaradas; no demuestra que se detecten
todas las paráfrasis. Las versiones 1 y 2 no son comparables como una mejora porcentual del sistema.

## Aislamiento de quests

`eval/security_quest_oracle_v2.jsonl` consulta una misma ubicación de Hyrule bajo perfiles de First Quest
y Second Quest. Exige preservar la descripción de la hada que restaura vida y prohíbe encabezados de la
otra quest en evidencia y respuesta. La versión inicial, `eval/security_quest_oracle.jsonl`, utilizaba
una consulta amplia que podía recuperar otras fuentes; la conservamos como sonda exploratoria y no
como prueba de disponibilidad de la ubicación. Este banco complementa los casos de revisiones
documentales: la quest es una variante del juego, no una revisión del documento.
