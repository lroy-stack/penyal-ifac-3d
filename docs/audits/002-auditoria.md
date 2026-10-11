# 002 — Auditoría del estado actual

- Fecha: 11/10/2026, 13:10–14:00 CEST. Solo lectura: no se ha modificado código.
- Autoría: revisión independiente (agente `code-reviewer`) más comprobaciones y mediciones del responsable técnico.
- **El repositorio estaba en movimiento.** Durante la auditoría seguían trabajando dos agentes de desarrollo:
  - T1.8b y T1.10: túnel en la app y paseo automático (`app/src/world/tunnel*.ts`, `app/src/player/autowalk.ts`, `app/src/main.ts`).
  - T2.2: material del terreno (`app/src/world/terrain/material*.ts`, `quality.ts`, `scripts/make-material-textures.mjs`).

  Sus hallazgos llevan la marca **[EN CURSO]** y conviene revisarlos de nuevo cuando terminen.
- Evidencia guardada en `docs/audits/002-capturas/`:
  - capturas en 7 puntos fijos;
  - `metrics.json` (modo desarrollo);
  - `prod-net.json` (producción, sin caché, solo tráfico de red);
  - `throttle.json` (red móvil simulada).

**Actualización a las 15:00:**
- T2.2 (material del terreno) terminó durante la auditoría.
- Coste medido en la GPU real (Apple M1 Pro, Metal, 2560×1440), p95 de 120 fotogramas:
  - calidad baja: 2,9–3,6 ms;
  - calidad alta: 3,6–4,3 ms.
- Un fallo puntual de 14 pruebas del túnel que comunicó el agente no se reproduce: al volver a ejecutar `pipeline/tests/test_tunnel.py` da "45 passed", y `ruff check` pasa.
- T1.8b y T1.10 seguían en curso.

## Resumen

El pipeline de datos, el candado de entradas y las pruebas unitarias están en buen estado. Los controles automáticos pasan, salvo el lint, que falla por un fichero de configuración suelto. Lo más grave no es técnico: **no existe ningún commit, remoto ni CI**, así que todo el proyecto vive en un solo disco. Además:

- **Atribución:** la app muestra datos CC BY y ODbL sin decirlo en pantalla, así que no se puede enseñar en público.
- **Accesibilidad:** con solo teclado no se puede girar.
- **Rendimiento:** en un móvil real sigue sin medirse. Bajo SwiftShader las llamadas de dibujo son muy bajas (5–18). Con red "4G lento" el terreno tarda 21 s en verse.

## Comandos ejecutados

| Comando | Resultado |
|---|---|
| `pnpm lint` | **Falla.** Biome: 2 errores en `app/playwright.mine.config.ts` (`outputDir` duplicado, líneas 10–11). `ruff check` y `ruff format --check` pasan por separado. |
| `pnpm typecheck` | Pasa: `tsc` limpio; basedpyright "0 errors, 0 warnings, 0 notes". |
| `pnpm test` | Pasa: vitest 26 ficheros / 276 tests; pytest "349 passed", 0 omitidos (los datos están presentes). |
| `uv run --project pipeline penyal doctor` | Sale con 0 y todo OK (python 3.13.16, bpy 5.2.2 LTS, rasterio 1.5.2, pyproj 3.8.0, laspy 2.7.0, node 24.21.0, pnpm 12.10.1, gltf-transform 4.5.1, ktx 4.4.2). |
| `penyal fetch --phase 1 --verify` | "verified 8 source(s): all files match manifest.lock.json". |
| `penyal fetch --phase 2 --verify` | "verified 12 source(s): all files match manifest.lock.json". |
| `git log` | "tu rama actual 'main' no tiene ningún commit todavía"; identidad de git vacía; sin remoto ni `.github/`. |
| Medición en 7 anclas (Playwright headless, SwiftShader, desarrollo y producción) | Ver la tabla siguiente. |

## Mediciones

Producción (`vite build` en una carpeta temporal), sin caché, solo bytes de red (se excluyen las URL `blob:` y `data:`). La calidad elegida por defecto bajo SwiftShader es "baja".

| Punto | Bytes hasta poder caminar | Bytes con el terreno asentado | Reparto al asentar |
|---|---|---|---|
| Torniquete | 1,86 MB | 9,16 MB | JS 0,85 · colisión 0,92 · teselas 6,69 · transcodificador 0,58 |
| Torniquete, `?terrain=high` | 4,32 MB | **17,08 MB** | texturas de material 7,93 (incluye el juego 2k) |
| Cima | 3,34 MB | 8,36 MB | teselas 5,90 |

Red simulada (CDP), producción, torniquete, calidad baja. El servidor de prueba no comprime, así que con brotli o gzip las cifras bajarían.

| Perfil | Primer paso posible | Terreno lejano visible |
|---|---|---|
| "4G lento" (150 ms, 1,6 Mbps) | 9,9 s | **21,3 s** |
| "4G rápido" (40 ms, 9 Mbps) | 2,0 s | 7,4 s |

Desarrollo, SwiftShader, 1280×720. Los tiempos de fotograma no son representativos porque el bucle recorta el delta a 0,1 s; ver m2.

| Ancla | Llamadas de dibujo | Triángulos | Teselas mostradas (LOD0/LOD1/LOD2) |
|---|---|---|---|
| turnstile | 18 | 296.001 | 8 / 8 / – |
| viewpoint-1795591637 | 18 | 296.001 | 8 / 8 / – |
| viewpoint-3635481356 | 15 | 277.559 | 7 / 9 / – |
| tunnel-east | 13 | 291.313 | 6 / 9 / 1 |
| bifurcation | 16 | 291.859 | 9 / 7 / – |
| summit | 13 | 254.257 | 5 / 10 / 1 |
| carabiners | 5 | 98.228 | 4 / 4 / 8 |

Sin errores de consola ni de página en las 7 anclas.

## Conformidad con los criterios de la spec 001

| AC | Estado | Evidencia |
|---|---|---|
| AC1 terreno reproducible, entradas fijadas | **Cumple, con reserva** | Los dos `--verify` pasan. Las pruebas byte a byte pasan (`pipeline/tests/test_terrain_tiles.py:162`, `test_tunnel.py:651,674`). Reservas: no hay commits (B2) y el fichero curado del túnel no consta en los manifiestos de salida (M4). |
| AC2 alturas ±0,5 m, puntos ±2 m | **Parcial** | LOD0 ≤ 0,25 m frente al DEM triangulado; frente a la interpolación bilineal solo en el p99, por las celdas de acantilado (`test_terrain_tiles.py:114`). Cima probada (`test_trail.py:252`). Bocas del túnel aproximadas. No hay prueba de ±2 m para el centro de visitantes. |
| AC3 ruta completa por el túnel | **[EN CURSO]** | Existe `app/e2e/route.spec.ts`; T1.8b y T1.10 sin cerrar; no se ha ejecutado en esta auditoría. |
| AC4 controles y cámaras | **Parcial** | Teclado y ratón, táctil y cambio de cámara funcionan. Faltan mando, giro con teclado (M3) y colisión de la cámara fuera del túnel (T2.7). |
| AC5 fichas y cuaderno | No empezado | Solo existe el registro de datos. |
| AC6 sin textos ni fuentes que falten | **Parcial** | Fuentes y estados validados (`app/src/content/registry.test.ts`); los enunciados de `facts.json` solo están en castellano y la interfaz tiene castellano escrito en el código (m7). |
| AC7 rendimiento y presupuesto | **Parcial, sin medir en móvil** | Descarga antes del primer paso: 1,86–4,32 MB (presupuesto 15 MB). Calidad alta asentada: 17,08 MB. No hay medición en un móvil real (T1.11). |
| AC8 WCAG y alternativa en texto | No empezado | Región de estado accesible, pero oculta a la vista (m11); sin guía en texto; teclado incompleto (M3). |
| AC9 sol real | No empezado | Fase 3. |
| AC10 pantalla de créditos | No empezado | Sin pantalla y sin atribución en la app (M1); `CREDITS.md` incompleto (M2). |

## Hallazgos, de más a menos grave

### Bloqueantes

**B1. Fichero suelto rompe `pnpm lint`.**
- Dónde: `app/playwright.mine.config.ts:10-11`.
- Qué pasa: `outputDir` aparece dos veces y el primero es una ruta de esta sesión (`/private/tmp/...`). Probablemente lo dejó un agente.
- Efecto: el control de cierre y la Definition of Done quedan en rojo.
- Arreglo: borrarlo; `playwright.config.ts` ya admite `E2E_PORT` y `E2E_OUTPUT_DIR`.
- Bloquea el cierre de F1: sí.

**B2. Ni commits, ni remoto, ni identidad de git, ni CI.**
- Efecto: `data/manifest.lock.json`, `data/curated/tunnel.toml`, los ADR y todo el código existen en un único disco. La vuelta atrás del plan ("reconstruir el commit anterior") es imposible y ningún hook de git está instalado.
- Arreglo: identidad (spec Q5), commits por tarea, un remoto privado y CI con lint, tipos y tests.
- Bloquea el cierre de F1: sí.

### Mayores

**M1. La app no muestra ninguna atribución.**
- Qué pasa: se ve la ortofoto y el MDT del ICV (CC BY 4.0) y el sendero y el túnel derivados de OSM (ODbL), sin crédito en pantalla. `app/index.html` no menciona ICV ni OpenStreetMap.
- Efecto: cualquier versión compartida incumple la cláusula 3(a) de CC BY 4.0 y la 4.3 de ODbL.
- Arreglo: una línea de atribución permanente ya; la pantalla completa en F4.
- Bloquea F1: no, pero sí cualquier demostración pública.

**M2. `CREDITS.md` no coincide con lo que se publica.**
- Faltan las texturas de Poly Haven (`marble_cliff_05`, `rocks_ground_05`), ya en `assets/generated/materials/`.
- Falta, entre las aproximaciones, la caliza sustituida por mármol.
- Faltan los avisos de terceros del bundle: three.js MIT, zod MIT, transcodificador Basis Apache-2.0, meshoptimizer MIT.

**M3. Con teclado no se puede girar.**
- Dónde: `app/src/input/mapping.ts:11-12`.
- Qué pasa: las flechas izquierda y derecha desplazan de lado y mirar exige ratón con bloqueo de puntero o arrastre táctil. El paseo automático (tecla P) no tiene control táctil.
- Efecto: incumple WCAG 2.1.1 (AC8) y AC4 para usuarios de teclado.

**M4. Los recursos generados no son trazables del todo.**
- `materials/*.ktx2` no tiene manifiesto: ni sha256 de entrada ni parámetros de `ktx`.
- `terrain/manifest.json` y `collision.json` no registran `data/curated/tunnel.toml`, que modifica `t_2_-4` y `collision.bin`.
- Efecto: si se edita el fichero curado, una tesela desfasada no se detecta.
- Arreglo: añadir a cada manifiesto `inputs: [{file, sha256}]` y versiones de herramientas.

**M5 [EN CURSO]. La carcasa del túnel asoma por fuera de la roca en la boca este.**
- Captura: `docs/audits/002-capturas/tunnel-east.jpg`. Se ve una pared beige lisa y una rendija por la que aparece el mar bajo el terreno.
- Coincide con el riesgo que anotó T1.8a: la bóveda sobresale del DEM en los primeros ~3 m interiores.
- Revisar cuando cierre T1.8b.

**M6. Terreno invisible durante 11 s en "4G lento".**
- Qué pasa: se puede caminar a los 9,9 s, pero el terreno lejano aparece a los 21,3 s, así que el visitante "camina" sobre mar y cielo.
- Arreglo:
  - cargar el anillo lejano y los LOD2 antes de permitir caminar, o como mínimo antes que la colisión completa;
  - servir con compresión;
  - medir de nuevo.

### Menores

- **m1.** Según la auditoría, el presupuesto de residencia es más flojo de lo documentado (`app/src/world/terrain/residency.ts:24-36`): el streamer solo pasa las entradas desalojables, así que LOD0 puede llegar a "en uso + 6".
- **m2 [EN CURSO].** La métrica de fotograma infravalora los tirones: el delta se recorta a 0,1 s antes de medirlo, y `percentile()` ordena 120 muestras en cada fotograma.
- **m3 [EN CURSO].** La luz del túnel está siempre en la escena con intensidad 0, así que todo el terreno la evalúa. Hay que medir su coste.
- **m4 [EN CURSO].** Se publican texturas sin usar: `rocks_ground_05` en KTX2 ocupa 12,3 MB y nada la referencia aún. La producción completa ocupa 34 MB, 19 de ellos de materiales.
- **m5 [EN CURSO].** Todos los iPhone reciben la calidad baja, porque Safari no expone `navigator.deviceMemory` (`app/src/world/terrain/quality.ts:10-32`).
- **m6.** El ADR 0009 solo se cumple en parte: el TOML curado no recoge la anchura de la franja, ni el número de celdas, ni el descenso máximo. Además el ADR sigue pendiente de confirmación.
- **m7.** Textos de interfaz escritos en el código, en castellano (`main.ts`, `renderer.ts`, `touch.ts`), y un error en inglés dentro de un mensaje en castellano en el paseo automático.
- **m8.** Falta el mensaje del ADR 0006 al salir del pasillo: `corridorHit` se publica pero no se muestra nada.
- **m9.** La documentación no coincide con el código en varios puntos:
  - el plan habla de `THREE.LOD` y `three-mesh-bvh`;
  - la interfaz cita `heightfield.f32` y rutas que ya no existen;
  - T0.7 dice "MDT in progress";
  - `CLAUDE.md` da otra ruta de recursos generados;
  - el ADR 0008 remite a `data/README.md` para los pasos del mantenedor, y no están ahí.
- **m10.** Pruebas débiles en algunos puntos:
  - todo el E2E corre con SwiftShader;
  - la calidad alta solo se prueba con `?terrain=high`;
  - una prueba de tiempo de fotograma no puede fallar;
  - en un clon limpio sin datos, las pruebas dependientes se omiten y los controles pasan sin geometría. Propuesta: `PENYAL_REQUIRE_DATA=1`.
- **m11.** Sin indicación visible de carga: `#status` está oculto a la vista (`app/index.html:53`) y no hay ayuda de controles en pantalla.
- **m12.** No está decidido si la colisión y la tesela `t_2_-4`, con huellas derivadas de OSM, son "obra producida" o "base de datos derivada" según la ODbL. Hay que documentarlo en el ADR 0007.
- **m13.** Costura de textura visible entre teselas vecinas con distinto nivel de detalle (captura `turnstile.jpg`, borde vertical a la izquierda).

### Detalles

- Dos comentarios de documentación superpuestos en `startAnchor` (`app/src/world/trail.ts`).
- Versiones no exactas: `uv_build>=0.12.24,<0.13.0` en `pipeline/pyproject.toml` y `engines.node ">=24"`.
- Al canvas le falta `role="img"`.
- `pnpm-lock.yaml` tiene permisos 0600.
- `window.__appState` y `?timescale` llegan a producción; conviene limitarlos al modo desarrollo o a las pruebas.

## Comprobado y correcto

- **Fetcher:** reanudación con `If-Range` y `Content-Range`, cuarentena ante cambios del candado, bloqueo de concurrencia, escrituras atómicas, y sin reintentos ante errores de certificado.
- **NAT64:** solo cambia el destino TCP; `Host`, SNI y el certificado usan el nombre real.
- **`tools/install-ktx.sh`:** comprueba sha256 y la firma Developer ID de Khronos.
- **Silene:** ninguna coordenada de *Silene hifacensis* en el código, los datos ni las salidas.
- **Separación ODbL:** `trail.json` y `tunnel.json` llevan ODbL y la atribución a OSM.
- **Versiones:** exactas en los `package.json` y en las dependencias de Python, con lockfiles presentes.
- **Streaming:** selección propia por error en pantalla, 2 cargas simultáneas, un único KTX2Loader compartido.
- **Móvil:** DPR limitado a 1,5 y sin MSAA con puntero grueso.
- **Registro de datos:** 55 datos (40 verificados, 11 en discrepancia, 4 sin verificar), validados con zod.
- **Túnel:** valores curados con su evidencia y marcados como aproximados.
- **Cima:** se mantiene en los 326,857 m del DEM, sin ajustar a la cifra oficial.
