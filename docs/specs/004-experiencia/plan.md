# 004 — Plan de X0 (base de interfaz) y X1 (orientación)

- Estado: **aprobado para empezar el 12/10/2026**. El usuario aceptó la dirección de la interfaz mínima del boceto y la descarga de "lo necesario" de la §9 de la propuesta (≈ 33 MB).
- Origen: `docs/specs/004-experiencia/propuesta.md` (§3, §4.1, §6).
- Carril:
  - es L7 (interfaz y contenido, `docs/specs/002-fase-b-paralelizacion.md`);
  - toca `app/src/ui/`, `app/index.html` y la conexión en `app/src/main.ts`;
  - los contratos de ADR 0010 (`world/systems.ts`, `content/poi.ts`, `content/notebook.ts`) solo los cambia el integrador.
- Reglas comunes:
  - prueba que falla primero;
  - accesibilidad dentro de cada tarea (`docs/research/005-experiencia-referentes.md`, lista P0);
  - nada depende de un atajo de teclado;
  - icono y palabra en cada botón, con objetivos de 44 px;
  - textos en es, va y en desde `app/src/ui/strings.ts`;
  - ninguna cifra inventada: lo que no tenga dato no se muestra.

| Tarea | Objetivo | Ficheros | Aceptación | Comprobación | Tamaño | Responsable |
|---|---|---|---|---|---|---|
| D.1 | Descargar lo aprobado (§9 de la propuesta, grupos A–D) | `data/catalog.toml` (fase 5), `data/manifest.lock.json`, `pipeline/src/penyal_pipeline/fetch.py` (tipo `wms` para los recortes del ICV) | (1) `penyal fetch --phase 5 --dry-run` lista exactamente los ficheros aprobados, ni uno más. (2) Todos quedan en `data/raw/` con su sha256 en el lock. (3) Licencia y atribución de cada uno en el catálogo y en `CREDITS.md` cuando se usen | `uv run --project pipeline penyal fetch --phase 5 --dry-run`; `PENYAL_REQUIRE_DATA=1 uv run --project pipeline pytest -q tests/test_fetch.py` | M | `implementer` |
| X0.1 | Diseño de la interfaz: tokens, componentes y estados | `docs/specs/004-experiencia/diseno-interfaz.md` y un prototipo HTML sobre capturas reales (fuera del repo, en el directorio temporal) | (1) Cubre todas las piezas de X0 y X1 a 375, 768 y 1440 px, en vertical y apaisado. (2) Contraste medido sobre los peores fondos reales (cielo claro y roca clara), 4,5:1 en texto y 3:1 en iconos, con el tratamiento de sombra o halo. (3) Orden de foco, tamaños táctiles, movimiento y *reduced motion*. (4) Textos para niños en es, va y en | Revisión del responsable técnico con capturas | M | `design-engineer` |
| X1.1 | Imagen del minimapa desde la ortofoto | `pipeline/src/penyal_pipeline/minimap.py`, sus pruebas, una orden `penyal minimap` | (1) Recorte de la ortofoto 2024 que cubre el corredor completo, desde la entrada del parque hasta la cima y Carabiners, más un margen, a 0,5 m/px. (2) WebP o JPEG de 600 KB como máximo y un `minimap.json` con límites y escala en el marco local. (3) Manifiesto de procedencia comprobado por `verify-generated` y salida determinista | `uv run --project pipeline pytest -q tests/test_minimap.py`; `penyal verify-generated` | S | `implementer` |
| X0.2 | Estructura de la interfaz y "Más" | `app/src/ui/`, `app/index.html` | (1) Hora diminuta arriba a la derecha (Europe/Madrid; el tiempo solo cuando exista `weather.json`). (2) Tres botones abajo a la derecha (Ir a la cima, Cuaderno, Más) y "Créditos" pequeño. (3) "Más" abre una hoja con ajustes de idioma, tamaño de texto, contraste, comodidad y "solo paisaje", guardados en el dispositivo. (4) Todo operable por teclado, táctil y lector de pantalla | vitest de los componentes; `pnpm --filter @penyal/app e2e hud` (nuevo) a 375, 768 y 1440 px | M | `frontend-engineer` |
| X0.3 | Llegada a un sitio y su ficha | `app/src/ui/`, conexión con `discover` de `world/poi.ts` | (1) Al descubrir un punto aparece su nombre y "Toca para saber más ›". Se va solo y queda en el historial de "Más". (2) Al tocar se abre la ficha en DOM, con el foco gestionado, los hechos con su estado y las fuentes desplegables. (3) La región viva anuncia la llegada | vitest; e2e con la ficha `centre` | M | `frontend-engineer` |
| X0.4 | Cuaderno conectado | `app/src/content/notebook.ts` (ya existe), `app/src/ui/` | (1) Cada descubrimiento queda en el cuaderno con su fecha. (2) "Cuaderno" abre la hoja con los sellos de las paradas alcanzadas. (3) Sobrevive a recargar la página | vitest; e2e | S | `frontend-engineer` |
| X0.5 | "Ir a la cima" en pantalla | `app/src/ui/`, `app/src/player/autowalk.ts` (ya existe) | (1) El botón inicia la subida automática a ritmo real. (2) Mientras sube se ven "Pausa" y "Parar", grandes y con palabra. (3) Funciona igual con teclado, táctil y lector de pantalla | vitest; e2e | S | `frontend-engineer` |
| X1.2 | Minimapa y altitud | `app/src/ui/minimap*`, lee `minimap.json` y la posición del jugador unas 10 veces por segundo | (1) Redondo y con el borde fundido. Abajo a la izquierda con puntero fino y arriba a la izquierda en táctil. (2) Ruta, flecha, N y la próxima parada en el borde. El norte va arriba por defecto; girar es opcional y nunca con *reduced motion*. (3) Altitud real bajo el minimapa, del campo de colisión. (4) Al tocarlo se abre el mapa grande. (5) Cero llamadas de dibujo nuevas | vitest de la proyección; e2e con captura a 3 tamaños; prueba de presupuesto sin cambios | M | `frontend-engineer` |
| X1.3 | Mapa grande y viaje rápido | `app/src/ui/map*`, `teleport` en el controlador | (1) Ruta, paradas con nombre confirmado (sin nombre confirmado: "Mirador") y tu posición. GPS simulado rotulado como tal y perfil de altitud. (2) "Ir ahora": fundido de 150–300 ms (corte con *reduced motion*). Las teselas del destino se piden antes de terminar, se llega mirando la vista, se anuncia y hay "Volver". (3) "Caminar hasta aquí" usa la subida automática. (4) Nunca se sale del corredor | vitest; e2e del viaje a la cima y del regreso | M | `frontend-engineer` |
| X1.4 | ¿Dónde estoy? | `app/src/ui/` | Botón en "Más" que anuncia, en la región viva y en voz si el usuario la activa, el lugar, la altitud, el rumbo y la distancia a la próxima parada | vitest; e2e que lee la región viva | S | `frontend-engineer` |

## Orden

1. **En paralelo:** D.1, X0.1 y X1.1. No comparten ficheros.
2. X0.2 → X0.3 → X0.4 → X0.5, sobre el diseño de X0.1.
3. X1.2 → X1.3 → X1.4, que necesitan X1.1 y X0.2.
4. Cada tarea termina con revisión de código independiente, sus pruebas en verde y capturas a 375, 768 y 1440 px.

## Progreso

- [~] **D.1** (85acab9, e244450): 21 de 25 descargados (31,8 MB) y bloqueados por sha256.
  - Faltan 4 documentos, porque Python no confía en sus raíces TLS (HARICA en el IGN, FNMT en el Catastro): la reseña y la ficha del vértice IGN 84878, y los dos PDF de licencia del Catastro.
  - No se ha desactivado la verificación. No bloquean ninguna tarea.
- [x] **X0.1** `diseno-interfaz.md` (12/10/2026).
  - La sombra suave del boceto daba 1,8:1 sobre el cielo más claro. Un reborde oscuro fino y un halo lo llevan a entre 5,0 y 10,7:1.
  - Decisiones del responsable técnico sobre sus preguntas abiertas:
    - hasta X2 se ve "Luz de ejemplo" bajo la hora;
    - la ruta va en ámbar con funda oscura;
    - en vertical, "Créditos" va bajo la hora y el aviso de llegada sube;
    - las teclas de una letra no actúan con el foco en un control;
    - correr se queda como está, sin anunciarse;
    - los términos en valenciano marcados quedan pendientes de revisión.
- [x] **X1.1** `penyal minimap` (001f9a2): 1658 × 1711 px a 0,5 m/px y 591 KB. Cubre el corredor con 60 m de margen; `verify-generated` da 12 artefactos al día.
- [ ] X0.2 · [ ] X0.3 · [ ] X0.4 · [ ] X0.5 · [ ] X1.2 · [ ] X1.3 · [ ] X1.4
