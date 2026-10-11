# 003 — Plan de E1 (caminos) y E2 (árboles)

- Estado: listo para empezar **cuando B0 esté integrado**. Usa el registro de sistemas, el presupuesto por sistema, los niveles de calidad y los parches de shader del ADR 0010.
- Origen: `docs/specs/003-entorno/propuesta.md`, aprobada el 11/10/2026.
- Carriles:
  - E1 toca el material del terreno, la única edición entre carriles que permite el ADR 0010 §2, y un paso nuevo del pipeline;
  - E2 es el carril L3 (vegetación).

  No comparten ficheros, así que van en paralelo, cada uno en su worktree (`scripts/worktree-setup.sh`).
- Reglas comunes:
  - prueba que falla primero;
  - salidas deterministas con manifiesto de procedencia, comprobadas por `penyal verify-generated`;
  - nada de geometría inventada: las medidas que falten se marcan como aproximación en `CREDITS.md` hasta que lleguen las fotos y medidas del usuario.

## E2 — Árboles y matorral reales (carril L3)

| Tarea | Objetivo | Ficheros | Aceptación | Comprobación | Tamaño | Responsable |
|---|---|---|---|---|---|---|
| E2.1 | Copas desde el LiDAR, como paso puro y determinista | `pipeline/src/penyal_pipeline/vegetation.py`, sus pruebas | (1) Detecta las copas de 3 m o más con un máximo local en ventana de 5 m sobre el modelo de copas a 1 m. (2) En la franja de 40 m del tramo piloto salen 186 ± 0 con los datos actuales; es un dato de referencia, no un ajuste. (3) Salida `vegetation.json` con posición, altura y radio estimado de cada copa, más el bloque de procedencia | `PENYAL_REQUIRE_DATA=1 uv run --project pipeline pytest -q tests/test_vegetation.py` | M | `implementer` |
| E2.2 | Descartar copas que ya no existen | idem | (1) Calcula el NDVI de la ortofoto 2024 en cada copa, con la banda 4 como infrarrojo; hay que confirmar con los metadatos del ICV que la banda 4 es infrarroja. (2) Si el NDVI cae por debajo de un umbral fijado con la distribución medida, la copa se marca como desaparecida y se excluye. (3) Se informa del número de copas excluidas | idem | S | `implementer` |
| E2.3 | Pino procedural | `pipeline/src/penyal_pipeline/blender/pine.py`, `vegetation.py` | (1) Tronco y ramas irregulares, con la copa abierta del pino carrasco, y tarjetas de acículas con las texturas `pine_tree_01` ya descargadas (fase 4). (2) De 3 a 5 variantes con semilla fija y escala por altura medida. (3) Nivel cercano ≤ 8.000 triángulos, nivel lejano y tarjeta. (4) GLB idéntico byte a byte en dos ejecuciones | `uv run --project pipeline pytest -q tests/test_pine.py` (incluye el sha256 de dos exportaciones) | M | `implementer` |
| E2.4 | Matorral | `vegetation.py` | (1) Instancias de `shrub_04`, `shrub_02` y `grass_medium_02` según la densidad de vegetación baja y media del LiDAR, en una rejilla con variación por semilla de la celda. (2) Nunca sobre el sendero (corredor del ADR 0006) ni sobre los firmes de E1. (3) Ninguna especie protegida | idem | S | `implementer` |
| E2.5 | Sistema `vegetation` en la app | `app/src/world/vegetation/**`, una entrada en `world/index.ts`, `budget.ts` (fila `vegetation`) | (1) Un `InstancedMesh` por variante y nivel de detalle, con selección por distancia. (2) Densidad y distancia según el nivel de calidad. (3) La prueba de presupuesto por sistema cumple la fila del ADR 0010: `medium` ≤ 40 llamadas y 250.000 triángulos. (4) Capturas antes y después desde los puntos fijos | `pnpm --filter @penyal/app e2e -- budget viewpoints`; `pnpm test` | M | `frontend-engineer` |

## E1 — Caminos en el material del terreno

| Tarea | Objetivo | Ficheros | Aceptación | Comprobación | Tamaño | Responsable |
|---|---|---|---|---|---|---|
| E1.1 | Máscara de firmes desde OSM | `pipeline/src/penyal_pipeline/surfaces.py`, sus pruebas | (1) Rasteriza las vías de OSM con su `surface` (empedrado, compactado, adoquín, asfalto, tierra y grava) a 0,25 m/px en la zona del parque y del acceso. Se codifica en **KTX2 UASTC lineal**, como dato y no como color: es la decisión tras la revisión, porque el PNG RGBA corría el riesgo de que Safari premultiplicara el alfa y ocupaba unos 4 MiB por tesela. Se carga solo para las teselas presentes. (2) El ancho de cada tipo es provisional y está marcado como aproximación hasta tener las medidas del usuario. (3) Salida por tesela o global con su procedencia, y determinista | `uv run --project pipeline pytest -q tests/test_surfaces.py`; `penyal verify-generated` | M | `implementer` |
| E1.2 | Materiales de los firmes | `data/catalog.toml` (fase 4), `scripts/make-material-textures.mjs` | (1) Una textura CC0 por firme, elegida comparando con las fotos del usuario. **La descarga necesita su aprobación** con nombre, origen, tamaño y licencia. (2) KTX2 con manifiesto, como en la fase 2 | `node scripts/make-material-textures.mjs`; `penyal verify-generated` | S | responsable técnico e `implementer` |
| E1.3 | El terreno pinta los firmes | `app/src/world/terrain/material.ts` (la edición permitida), un parche de shader nuevo | (1) Mezcla por máscara, con el borde suavizado, sobre el detalle cercano. **Acota la suma de canales a 1**: la compresión UASTC deja fugas entre clases de hasta unos 48/255 en las transiciones, medidas en la revisión de E1. La máscara se lee como dato lineal (`NoColorSpace`) y solo se carga para las teselas presentes (ADR 0010, enmienda 1). (2) Cero llamadas de dibujo adicionales. (3) En nivel `low`, solo color, sin texturas de detalle. (4) Clave de caché nueva y versionada | `pnpm --filter @penyal/app e2e -- viewpoints terrain-material budget` | M | `frontend-engineer` |
| E1.4 | Escalones como malla | `pipeline/src/penyal_pipeline/structures.py` (empieza L5) | (1) Las escaleras de 30 y de 10 peldaños, y también la de 6 de la boca oeste del túnel (`way/862108208`), con su barandilla, a lo largo de su línea de OSM y con su `step_count`. (2) Contrahuella uniforme y peldaños que siguen el perfil del MDT tallado: ninguna huella queda bajo el terreno que se ve. (3) Medidas provisionales hasta las del usuario | `uv run --project pipeline pytest -q tests/test_structures.py` | M | `implementer` |

## Orden y dependencias

1. B0 integrado en `main`.
2. **En paralelo:**
   - **E2:** E2.1 → E2.2 → E2.3 → E2.4 → E2.5;
   - **E1:** E1.1 → E1.3, usando como textura provisional `rocks_ground_05`, ya descargada en la fase 2 y reservada para el firme del sendero (`CREDITS.md`), sin descargar nada nuevo; después E1.2, que cambia por los materiales elegidos cuando lleguen las fotos, y E1.4.
3. Cada tarea termina con revisión de código independiente y su comprobación en verde.

## Riesgos

| Riesgo | Respuesta |
|---|---|
| El LiDAR es de 2016 y hay árboles que ya no existen | E2.2 los descarta con el NDVI de la ortofoto 2024 |
| La banda 4 de la ortofoto no es infrarroja | **Resuelto el 11/10/2026** comparando 5.000 puntos LiDAR por clase con la ortofoto. Se comporta como infrarroja, con NDVI mediano de +0,29 en vegetación alta, +0,20 en baja, +0,06 en suelo y +0,03 en edificios. Los metadatos del ICV no eran accesibles |
| Los anchos de camino son provisionales | Se marcan como aproximación y se sustituyen al llegar las medidas, con el paso del pipeline volviendo a generar la salida |
| Rendimiento en móvil | La fila del ADR 0010 y la prueba por sistema. A7, la medición en el móvil, calibra los milisegundos |
| **Memoria de GPU**, que el ADR 0010 no presupuesta: solo cubre llamadas de dibujo, triángulos y milisegundos | Añadir al presupuesto por sistema una columna con los MiB de textura estimados por formato y tamaño, con un tope provisional por nivel que se calibra en A7. Se propondrá como enmienda del ADR 0010 antes de E1.3 y E2.5 |

## Progreso

- [x] **E1.1, máscara de firmes** (`penyal surfaces`), integrada en `main` el 11/10/2026 (c9600ad, ba24f60, 2437b08).
  - 8 teselas en KTX2 UASTC lineal, 0,18 MB en total.
  - Cobertura: 2.288 m² de empedrado, 2.505 de compactado, 1.371 de adoquín y 2.602 de asfalto.
  - Los anchos son provisionales y se marcan por vía (`widthSource`).
  - Fuga entre canales medida: 48/255 como máximo.
- [x] **E1.4, escaleras** (`penyal structures`), integrada en `main` (d559200, 3d0e43b, 0a5511c, a25a044).
  - Tres vuelos con altura de peldaño uniforme que siguen el MDT tallado: centro con 30 peldaños de 0,166 m, escalera de 10 peldaños de 0,224 m y portal con 6 de 0,139 m.
  - En total, 914 triángulos. La holgura de las huellas es de −6 mm como mínimo.
  - Las medidas, el material y el lado de la barandilla son provisionales.
  - Pasó tres rondas de revisión independiente.
- [ ] E1.2, materiales: espera a las fotos y medidas del usuario.
- [ ] E1.3, el terreno pinta los firmes: espera a B0.
- [ ] E2.1–E2.4: segunda ronda de correcciones tras la revisión, en curso.
- [ ] E2.5: espera a B0.
