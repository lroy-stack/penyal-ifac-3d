# 006 — Plan del hito H1

- Spec: `spec.md`, en esta carpeta.
- Hoja de ruta: `docs/roadmap.md` §2, H1. El método agéntico es el de §3 (ciclo de tarea, integración, puertas).
- **Tareas que viven en otra spec:** aquí solo se ordenan, sin redefinirlas.
  - 004: X0.2–X0.5 y X1.2–X1.4 (`docs/specs/004-experiencia/plan.md`);
  - 003: E1.2 (`docs/specs/003-entorno/plan.md`).
- **Tareas nuevas:** el resto. Llevan la definición completa en la tabla y siguen el formato de `workflow.md`.
- Reglas que no cambian:
  - prueba que falla primero;
  - salidas deterministas con manifiesto de procedencia (`penyal verify-generated`);
  - cada objeto colocado lleva su evidencia;
  - lo aproximado se marca en el código y en `CREDITS.md`;
  - las descargas, siempre con aprobación.

## 1. Lo que ya sabemos de los datos (12/10/2026)

| Elemento | Evidencia disponible | Consecuencia |
|---|---|---|
| Barcos | La ortofoto 2024 del ICV (25 cm) muestra varios cientos de embarcaciones amarradas en los 6 pantalanes de OSM (`man_made=pier`, 589 m), a 90–125 m del corredor. Se distinguen el casco, la eslora, la manga y el rumbo; la flota pesquera, junto a la lonja; y los yates grandes del muelle sur. La capacidad publicada es de 264 amarres en 7 pantalanes (`004-recursos-pobla-puerto.md`) | Se colocan midiendo, como las copas con el LiDAR. El tipo exacto (vela o motor) no siempre se ve: se aproxima por la forma y se rotula |
| Muros de roca | No hay `barrier=wall` ni `retaining_wall` de OSM a menos de 330 m del corredor. Las fotos de 2013–2014 (`004-recursos-acceso-centro.md`) muestran muros de piedra seca junto al centro, y las obras de 2016 hicieron "muros de mampostería" en el sendero (`004-recursos-sendero-alto.md`) | Hay que **detectarlos** en el LiDAR (escalón lineal en el terreno) y la ortofoto, y confirmar cada tramo con una foto o con las dos fuentes |
| Rocas | Afloramientos de caliza a lo largo del camino. Se ven en la ortofoto (claros y sin NDVI) y en el LiDAR (relieve local sobre el MDT) | Se detectan y se instancian modelos CC0 escaneados, a la escala de la huella medida |
| Barandillas | Talanqueras de rollizos con dos travesaños, según las fotos. Sin medidas oficiales | Tramos situados por evidencia. Medidas de tipología comercial y CTE DB-SUA como último recurso, rotuladas |
| Fuentes, torniquete, panel, aseos | Nodos de OSM | Posición directa |
| Pérgolas del aparcamiento | 4 pérgolas de madera visibles en la ortofoto (592 m²) | Se trazan sobre la ortofoto |
| Firme | Lajas poligonales de caliza clara con mortero. `stone_tiles_02` CC0 ya descargada, igual que `gravel_floor_04` y `patio_tiles` | E1.2 puede empezar ya |

## 2. Tareas

**Carriles** (`docs/roadmap.md` §3.2). Van en paralelo solo los que no comparten ficheros.
- **A:** interfaz.
- **B:** entorno 3D.
- **C:** sonido.
- **D:** contenido.
- **E:** calidad.
- **F:** publicación.

| Id | Carril | Objetivo | Ficheros | Aceptación | Comprobación | Tamaño | Responsable |
|---|---|---|---|---|---|---|---|
| H1-A1 | A | 004 X0.2–X0.5 (en curso) | 004 plan | 004 plan | 004 plan | M | `frontend-engineer` |
| H1-A2 | A | 004 X1.2 minimapa y altitud | 004 plan | 004 plan | 004 plan | M | `frontend-engineer` |
| H1-A3 | A | 004 X1.3 mapa grande y viaje rápido | 004 plan | 004 plan | 004 plan | M | `frontend-engineer` |
| H1-A4 | A | 004 X1.4 "¿Dónde estoy?" | 004 plan | 004 plan | 004 plan | S | `frontend-engineer` |
| H1-A5 | A | Tocar para caminar (002 B10) | `app/src/input/`, `app/src/player/` | (1) Tocar o hacer clic en un punto del corredor lleva al jugador hasta él a ritmo real. Si el punto está en la ruta, la sigue; si no, va en línea recta acotada al corredor. (2) Un punto fuera del corredor no hace nada y lo dice ("Solo por el sendero"). (3) El joystick o una tecla lo cancelan. (4) No interfiere con arrastrar para mirar | vitest de la selección y del trayecto; e2e táctil y de ratón | M | `frontend-engineer` |
| H1-A6 | A | Calidad automática (002 B11) | `app/src/core/quality.ts` (integrador), `app/src/core/` | (1) Mide 2–3 s al arrancar y baja de nivel si p95 > 33,3 ms, con histéresis. (2) Resolución dinámica entre 0,7 y 1,0 con su propia histéresis. (3) `?quality=` sigue mandando. (4) El cambio se anuncia sin interrumpir | vitest con reloj falso; e2e con limitación de CPU | M | `implementer` |
| H1-B1 | B | 003 E1.2 materiales del firme | 003 plan | 003 plan, con `stone_tiles_02` aclarada hacia `#D5CAB8` | 003 plan | S | `implementer` |
| H1-B2 | B | Inventario por evidencia del tramo y del acceso | `pipeline/src/penyal_pipeline/inventory.py`, sus pruebas, `data/curated/h1-inventory.geojson`, `docs/research/006-inventario-h1.md` | (1) Detecta candidatos de muro (escalón lineal ≥ 0,4 m en el LiDAR 2016 sobre el MDT, a ≤ 25 m del corredor), de roca (relieve local ≥ 0,5 m sin vegetación en el LiDAR y con NDVI bajo en la ortofoto) y de barandilla. (2) Cada objeto del GeoJSON curado lleva tipo, geometría, altura medida si la hay y `evidence` con una o más fuentes (LiDAR, ortofoto, OSM o foto fechada con autor y licencia). Un candidato sin confirmar no entra. (3) Fuentes, torniquete, panel y aseos salen de OSM. (4) Informe con mapa de candidatos aceptados y descartados | `uv run --project pipeline pytest -q tests/test_inventory.py`; revisión del responsable técnico sobre la ortofoto | M | `implementer` + agente de investigación (fotos) |
| H1-B3 | B | Muros de piedra seca | `pipeline/src/penyal_pipeline/walls.py` (generador Blender), estructuras en la app | (1) Un muro por tramo del inventario, a lo largo de su línea, con altura medida o la de la foto rotulada. Mampostería con la textura `stacked_stone_wall`, ya descargada en la fase 4, y una albardilla de piedras. (2) Nivel cercano y lejano. (3) Se dibuja con el sistema `structures` existente, sin sistema nuevo. (4) Determinista | `pytest tests/test_walls.py` (sha256 de dos exportaciones); e2e `structures`; capturas | M | `implementer` |
| H1-B4 | B | Rocas | `pipeline/src/penyal_pipeline/rocks.py`, sistema de instancias en la app | (1) Cada roca del inventario es una instancia de un modelo de caliza escaneado (CC0, H1-R1), escalada y girada a su huella medida y apoyada en el terreno. (2) Nunca dentro del corredor. (3) Nivel cercano, lejano e impostor. (4) Reutiliza el código de instancias de `vegetation`, que el integrador extrae a un módulo compartido sin copiarlo | vitest; e2e `budget`; capturas | M | `implementer` (pipeline) + `frontend-engineer` (sistema) |
| H1-B5 | B | Barcos y pantalanes medidos | `pipeline/src/penyal_pipeline/boats.py`, sus pruebas, sistema `marina` en la app | (1) Detecta las embarcaciones en la ortofoto 2024 dentro del agua del puerto: máscara del agua con la costa de OSM y el NIR, cascos claros conectados, y caja orientada con centro, rumbo, eslora y manga. (2) Clases por eslora y proporción (bote < 6 m, motor o vela de 6–15 m, yate > 15 m, pesquero junto a la lonja), rotuladas como aproximadas. (3) Una muestra de 30 barcos revisada a mano contra la ortofoto: eslora ± 1 m y rumbo ± 10°. (4) Pantalanes de OSM como tableros de 2,5 m (ancho aproximado, rotulado). (5) Modelos procedurales o de biblioteca CC0 o CC BY, según H1-R1, por clase y con niveles de detalle. Flotan al nivel del mar del ADR 0004. (6) Determinista y con manifiesto | `pytest tests/test_boats.py`; recuento e informe de la muestra; e2e `budget`; capturas desde el tramo | L, se divide: detección / modelos / sistema | `implementer` + `frontend-engineer` |
| H1-B6 | B | Pórtico, torretas y patio del centro (E3+) | `pipeline/src/penyal_pipeline/buildings.py` y el generador Blender | Arcos de medio punto con pilares blancos y suelo de baldosa roja (`patio_tiles`), torretas almenadas y lucernario, colocados en las aristas descritas en `004-recursos-acceso-centro.md` §2.3. Medidas de arcos aproximadas (luz ≈ 2,0 m, clave ≈ 3,0 m), rotuladas | `pytest tests/test_buildings.py`; capturas desde el torniquete y el centro | M | `implementer` |
| H1-B7 | B | Mobiliario del acceso (E4) | `pipeline/src/penyal_pipeline/furniture.py`, `structures` | Torniquete, dos fuentes, panel informativo, talanqueras de rollizos en los tramos del inventario y pérgolas del aparcamiento. Medidas de tipología o del CTE rotuladas como aproximación. Nada sin evidencia | `pytest tests/test_furniture.py`; capturas | M | `implementer` |
| H1-R1 | B | Buscar assets reales con licencia | `docs/research/006-assets-h1.md` | Modelos CC0 o CC BY de rocas de caliza escaneadas, de barcos (llaüt o pesquero, velero, lancha, yate) o la justificación de hacerlos procedurales, y texturas de madera de rollizo y de metal galvanizado. Por cada uno: licencia, autor, triángulos, tamaño y adecuación. Lista de descargas para aprobar | Revisión del responsable técnico | S | agente de investigación |
| H1-C1 | C | Sonido básico (002 B4, carril L2) | `app/src/audio/` (nuevo sistema), `content/` o catálogo | (1) Arranca con el primer gesto y tiene volumen y silencio en "Más". (2) Capas: mar (más fuerte cerca de la costa), gaviota patiamarilla (xeno-canto, CC BY), viento suave y pasos sobre grava al caminar, todos de la fase 4. (3) Nada sin registro en el parque: sin cigarras. (4) Licencias en `CREDITS.md` (ADR 0011). (5) Cero llamadas de dibujo y presupuesto de CPU medido | vitest; e2e `audio` que comprueba que no suena antes del gesto | M | `frontend-engineer` |
| H1-D1 | D | Fichas del tramo (002 B9) | `content/pois/*.json`, `content/facts.json` | El Centre (ya en borrador), la reserva y el torniquete (con la discrepancia de 10 frente a 4 días, a la vista), el mirador (OSM 1795591637, rotulado "Mirador": su nombre no está confirmado) y la Pobla vista desde él. Cada frase lleva su hecho. Traducción a va y en | `pnpm --filter @penyal/app exec vitest run src/content/registry.test.ts`; revisión del valenciano | M | responsable técnico + `scribe` (traducción) + usuario (revisión) |
| H1-D2 | D | Consulta al parque | `docs/specs/002/consulta-parque.md` | Se añaden las 5 preguntas nuevas de `004-recursos-sendero-alto.md` §7 y lo que H1-B2 no pueda confirmar (muros, barandillas). El usuario la envía | Fecha de envío anotada | S | responsable técnico + usuario |
| H1-E1 | E | Base sana (H0) | `app/e2e/` | Capturas de referencia regeneradas a propósito tras A1, prueba de presupuesto que falló bajo carga repetida en serie, batería completa en verde | `pnpm --filter @penyal/app e2e` en serie | S | `test-engineer` |
| H1-E2 | E | Accesibilidad automática | `app/e2e/a11y.spec.ts`, `@axe-core/playwright` (versión exacta) | axe sin errores críticos ni serios en la pantalla por defecto, "Más", ficha, cuaderno y mapa, a 375 y 1440 px | e2e `a11y` | S | `test-engineer` |
| H1-E3 | E | Comparación con fotos fechadas | `docs/research/006-comparacion-fotos.md` | 2–3 fotos CC o de dominio público con fecha y hora conocidas (EXIF o descripción) desde puntos del tramo. La captura del juego se hace a la misma hora solar con el protocolo de `002-verificacion.md` §4, y se informa sin umbral inventado. El sol real llega en H2; hasta entonces la comparación es de geometría y encuadre | Informe con los pares de imágenes | S | agente de investigación + responsable técnico |
| H1-E4 | E | Medición en móviles reales (A7) | `docs/specs/006-h1-paseo-con-sentido/medicion-a7.md` | `?perf` en los dos móviles de referencia, en 4 puntos del tramo y en los tres niveles. Calibra `MS_CALIBRATION` de `budget.ts` | Informe con p50, p95 y p99 | S | usuario (móviles) + responsable técnico |
| H1-E5 | E | Prueba con cinco vecinos, a distancia | `docs/specs/002/pruebas-vecinos.md` (se adapta a distancia) | Cinco personas siguen el guion por videollamada o solas con un formulario anónimo sin datos personales. Se anotan tiempos y problemas, y lo grave se corrige o se registra | Notas en el documento | M | usuario (organiza) + responsable técnico |
| H1-F1 | F | Dirección de prueba privada | `docs/adr/0012-*.md` (alojamiento), configuración del proveedor | Una URL sin indexar (`noindex`), sin analítica y con cabeceras de seguridad básicas, para los móviles y los vecinos. Se publica desde `main` con un comando documentado. **Necesita la decisión y la aprobación del usuario** (proveedor y publicación) | La URL carga en un móvil fuera de la red local | S | `devops-engineer` + usuario |
| H1-G1 | — | Caminante animado (002 B7), opcional | ADR 0008 | Solo si el usuario descarga el zip de Quaternius: andar, quieto y correr, en tercera persona | e2e de cámara; licencia comprobada en el zip | M | `implementer` |

## 3. Orden y paralelismo

```
Ahora:      A1 (en curso) · R1 · B1 · B2 · B5-detección · C1 · D2 · F1 (decisión del usuario)
Tras A1:    E1 → A2 → A3 → A4 · A5 · E2 · D1
Tras R1:    aprobación de descargas → B4 · B5-modelos · B7 (madera, metal)
Tras B2:    B3 (muros) · B4 (rocas) · B7 (barandillas)
Tras B5:    B5-sistema `marina`
            B6 en cualquier momento (solo toca `buildings`)
Tras F1:    E4 (A7) → A6 (calibrada) → E3 → E5 (cinco vecinos, cierre)
```

- Como mucho 4 agentes programando y 3 investigando a la vez (`roadmap.md` §3.2).
- **No pueden ir a la vez:**
  - B3, B6 y B7 tocan el pipeline de estructuras y edificios: van en serie o en ficheros separados;
  - A2 a A5 tocan `app/src/ui/`: un único agente en serie.
- **Cambios que hace el integrador:**
  - extraer el módulo de instancias compartido (para B4 y B5);
  - las filas nuevas de `budget.ts`;
  - `quality.ts` (A6).

## 4. Presupuesto (nivel `medium`, propuesto y calibrado en E4)

| Sistema | Llamadas | Triángulos | MiB de textura | Nota |
|---|---|---|---|---|
| `structures` (escaleras, muros, mobiliario) | 11 → 16 | 58.000 → 90.000 | 0 → 4 | Muros y mobiliario entran en el sistema que ya existe |
| `rocks` (nuevo) | 6 | 80.000 | 4 | Instancias por modelo y nivel |
| `marina` (nuevo) | 8 | 60.000 | 3 | Barcos por clase y nivel, más los pantalanes |
| `audio` | 0 | 0 | 0 | Solo CPU y memoria de audio |

Hoy el total de `medium` ronda las 35 llamadas, y estas filas añaden hasta 19. Con ellas queda por debajo del objetivo de 100 llamadas y del tope de 48 MiB de textura (ADR 0010, enmienda 1). Las filas se escriben en `budget.ts` antes de integrar los sistemas.

## 5. Lo que depende de personas en H1

| Qué | Quién | Para |
|---|---|---|
| Aprobar las descargas de H1-R1 (rocas, barcos si son de biblioteca, madera y metal) | Usuario | B4, B5, B7 |
| Elegir proveedor y aprobar la dirección de prueba | Usuario | F1 → E4, E5 |
| Dos móviles de referencia | Usuario | E4 |
| Revisar el valenciano | Usuario o servicio lingüístico | D1 |
| Enviar la consulta al parque | Usuario | D2 |
| Reunir a cinco vecinos | Usuario | E5 |
| Zip de Quaternius | Usuario, opcional | G1 |
| Facturación de GitHub Actions | Usuario | Integración continua |

## 6. Riesgos

| Riesgo | Respuesta |
|---|---|
| La detección de barcos confunde espuma, pantalanes o reflejos | Máscara del agua con el NIR, tamaño mínimo y revisión manual de una muestra. Si la precisión de la muestra no llega, la clase dudosa no se coloca |
| Los muros del LiDAR de 2016 ya no existen, o son de 2016 en adelante | Cada tramo necesita una segunda fuente: la ortofoto 2024 o una foto fechada |
| No hay barcos realistas con licencia libre | Modelos procedurales por clase, con eslora y manga medidas. A 100–300 m bastan |
| Los vecinos no pueden probar sin la dirección pública | F1 se decide al empezar H1, no al final |
| El presupuesto en móvil no llega con rocas y barcos | Los niveles bajan primero la densidad de rocas y los barcos lejanos (impostores) |

## 7. Progreso

**12/10/2026, primera tanda en marcha.**
- Interfaz: A1 (004 X0).
- Entorno: B1 (firmes), B2 (inventario por evidencia) y B5, parte de detección de barcos.
- Recursos: R1 (assets con licencia).
- Publicación: F1. El usuario eligió Cloudflare Pages; se prepara sin publicar y cada publicación necesitará su confirmación.
- Contenido: D2 hecha (83804f3), con 7 preguntas nuevas en `consulta-parque.md`. Falta que el usuario la envíe.
- C1 (sonido) espera a que se integre A1, porque comparte "Más".

- [~] H1-A1 (004 X0.2–X0.5) · [ ] A2 · [ ] A3 · [ ] A4 · [ ] A5 · [ ] A6
- [~] H1-B1 · [~] B2 · [ ] B3 · [ ] B4 · [~] B5 (detección) · [ ] B6 · [ ] B7 · [~] R1
- [ ] H1-C1 · [ ] D1 · [x] D2 (falta el envío) · [ ] E1 · [ ] E2 · [ ] E3 · [ ] E4 · [ ] E5 · [~] F1 · [ ] G1 (opcional)
