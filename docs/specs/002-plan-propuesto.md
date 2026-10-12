# 002 — Plan propuesto

> **12/10/2026:** el orden de lo que queda (resto de la fase B, B2, C y D) lo marca ahora `docs/roadmap.md`, con los hitos H0–H5. Los criterios de salida de este documento siguen vigentes y el roadmap los cita.


- Estado: **propuesto, pendiente de aprobación**. No sustituye todavía a `docs/specs/001-penyal-ifac-3d/plan.md`.
- Fecha: 11/10/2026.
- Base:
  - la propuesta del equipo, verificada en `docs/research/002-verificacion.md`;
  - la auditoría `docs/audits/002-auditoria.md`;
  - las decisiones del usuario en esta sesión.
- Principio de la propuesta: **cortes verticales**. Un tramo se termina con todas sus capas (terreno, luz, sonido, vegetación, contenido, interfaz y pruebas con personas) antes de extender nada. Así se sustituyen las fases horizontales del plan 001 (fidelidad → mundo vivo → contenido).
- Los esfuerzos son **estimaciones** del responsable técnico, en días de desarrollo. No incluyen el tiempo de espera de las personas implicadas.

## Decisiones ya tomadas

- Ritmo de marcha: **1,4 m/s, sin cambios** (decisión del usuario, 11/10/2026). La ruta principal son ≈ 21 min de marcha en la app; `?timescale=N` acelera la simulación para explorar.
- Se mantienen `WebGLRenderer` con WebGL2 (ADR 0002) y el resto de ADR.
- Pendientes de confirmación del responsable del proyecto: ADR 0008 (licencia QAL solo para el caminante) y ADR 0009 (correcciones locales del terreno con evidencia).

## Fase A — Estabilizar y cerrar F1

**Objetivo de salida (verificable):**
- Los controles automáticos pasan en CI, sobre un repositorio remoto con historial de commits.
- La ruta completa (torniquete → cima y → Carabiners) pasa la prueba E2E.
- La atribución CC BY y ODbL se ve en pantalla.
- Se puede girar con el teclado.
- Hay al menos una medición en un móvil de referencia registrada en `docs/specs/001-penyal-ifac-3d/perf.md`, con p50/p95/p99 y tirones.

**Esfuerzo:** 2–3 días. **Depende de:** la identidad de git y el remoto; los móviles de referencia.

| Tarea | Detalle | Responsable | Comprobación |
|---|---|---|---|
| A1 Historial y CI | Identidad de git, commits por tarea con Conventional Commits, remoto privado, CI con lint, tipos y tests (más un E2E headless sin datos). Borrar `app/playwright.mine.config.ts` (B1). | Responsable técnico + usuario | `pnpm lint && pnpm typecheck && pnpm test` en CI |
| A2 Cerrar T1.8b y T1.10 | Túnel en la app y paseo automático. Revisar M5 (carcasa del túnel asomando en la boca este). | `implementer` | `pnpm --filter @penyal/app e2e -- tunnel route` y captura en `tunnel-east` |
| A3 Atribución y créditos | Línea de atribución permanente (M1); `CREDITS.md` al día con Poly Haven, la caliza sustituida por mármol y los avisos de terceros (M2). | `implementer` | Captura con la atribución visible; revisión de `CREDITS.md` |
| A4 Teclado y carga | Girar con las flechas (M3); aviso de carga visible (m11); anillo lejano y LOD2 antes de permitir caminar (M6); servir con compresión. | `implementer` | Red "4G rápido": terreno visible ≤ 10 s; "4G lento": aviso ≤ 2,5 s |
| A5 Trazabilidad | `inputs: [{file, sha256}]` y versiones de herramientas en los manifiestos de terreno, colisión, túnel y materiales (M4); bloque `[corrections]` del ADR 0009 con prueba sobre datos reales (m6). | `implementer` | `uv run --project pipeline pytest -q` |
| A6 Métricas reales | Delta de `requestAnimationFrame` sin recortar; p50/p95/p99 y fotogramas > 50 ms; cálculo cada N fotogramas (m2). | `implementer` | Prueba unitaria + lectura en el móvil |
| A7 Medición en móvil | T1.11 en los dos móviles de referencia, servido por la red local. | Responsable técnico + usuario | `perf.md` con modelo, navegador y cifras |

### Progreso de la Fase A (11/10/2026)
- A1: identidad de git local configurada; 7 commits por áreas; CI de GitHub Actions escrita (`.github/workflows/ci.yml`). **Pendiente:** el remoto privado necesita `gh auth login` del usuario desde una red con IPv4 (el punto de acceso actual no llega a GitHub). B1 resuelto: el fichero suelto ya no existe.
- A2: T1.8b y T1.10 cerradas (túnel recorrible en ambas cámaras; paseo automático a la cima y a Carabiners). M5 corregido (commits b05d8dd, 9b3c2e7, 7d33ba4): las paredes y la bóveda se recortan contra el terreno tallado, sin tocar el suelo.
  - Superficie visible desde fuera, este: de 4,31 m² a 0,06 m². Protrusión máxima: de 3,05 m a 0,00 m.
  - Oeste: queda un resto de 0,06 m² que sobresale 1,22 m (medido cada 0,1 m) en el escalón del tallado del ADR 0009.
  - Es una aproximación conocida. La prueba la fija en ≤ 1,3 m y ≤ 0,1 m² para que no empeore (commit c07a0a4).
  - La boca queda irregular hasta tener las medidas reales del túnel (Q6).
- A3: hecho. `CREDITS.md` al día (M2); atribución permanente en pantalla y diálogo de créditos accesible (d7bf9aa).
- A4: hecho (303293d, 6deb97a, 51dfcba).
  - Controles: ← → giran, Q/E desplazan y el ratón mira arrastrando, sin bloqueo de puntero.
  - Carga: pantalla de carga con progreso. Primero se piden la malla lejana y el LOD grueso cercano; se camina solo con el terreno visible.
  - Ayudas: pistas de controles y aviso del corredor.
  - Medido (SwiftShader, medianas de 3 ejecuciones):
    - 4G rápido: terreno visible en 3,1–3,9 s (objetivo ≤ 10 s);
    - 4G lento: aviso pintado en ~1 s (objetivo ≤ 2,5 s); se puede caminar a los 11,9 s con brotli.
- A6: hecho (92cfcdf). Delta de rAF sin recortar; p50/p95/p99 y fotogramas > 50 ms; `?perf`.
  - Los ganchos de prueba solo existen en el servidor de desarrollo o con `VITE_E2E=true`; comprobado en el build de producción.
- A5: hecho (commits 3cdddbf, e6108e1): procedencia en manifiestos, `penyal verify-generated`, bloque ADR 0009 verificado sobre datos reales (39 celdas, 13,30 m) y `PENYAL_REQUIRE_DATA=1`. El manifiesto de materiales ya está regenerado: las 12 texturas KTX2 son idénticas byte a byte.
  - El terreno y el túnel están regenerados en su sitio, en ese orden. `penyal verify-generated` da "all 5 generated artefacts match their recorded inputs" y sale con 0.
- A7: pendiente de los móviles de referencia.

### Cierre de la Fase A (11/10/2026)
- **Estado:** cerrada en lo técnico. Quedan dos tareas que dependen del usuario:
  - A1, el remoto de GitHub y la CI: requiere `gh auth login` desde una red con IPv4;
  - A7, la medición en los móviles de referencia.
- **Revisión independiente:** tres rondas con el agente `code-reviewer`.
  - Primera ronda, cerrada:
    - la pantalla de carga podía quedarse para siempre si fallaba el terreno;
    - no había timeouts en las peticiones;
    - la procedencia del túnel no incluía el MDT;
    - el error fatal quedaba tapado;
    - las teclas seguían activas con el diálogo abierto;
    - las pistas se solapaban con la atribución en móvil.
  - Segunda ronda, cerrada: la espera del terreno pasa a ser un plazo de inactividad de 120 s sobre el reloj del bucle, con recuperación. La colisión tiene reintentos. Hay una única ruta de error fatal.
  - Tercera ronda, cerrada (df946db): tras un fallo con el paseo en marcha, solo la visibilidad cambia el estado.
- **Comprobaciones:**
  - `pnpm lint`, `pnpm typecheck` y `pnpm test` en verde: 364 tests de vitest y 402 de pytest con `PENYAL_REQUIRE_DATA=1`.
  - E2E completa (48/48) antes de la última tanda de arreglos, y E2E de las áreas tocadas después.
  - `penyal verify-generated` sale con 0.
- **Seguimientos** (no bloquean; van a la fase B o D):
  - **Espera del terreno:** debe alimentarse solo con los bytes y teselas del camino crítico. Hoy usa el total, y tras un fallo con recuperación previa al paseo los bytes de detalle podrían ocultar un segundo fallo. Además:
    - pruebas unitarias de la máquina de estados de la interfaz;
    - rearmar los recursos críticos agotados con el evento `online`.
  - **Colisión:** abortar la descarga hermana al reintentar y reintentar solo errores transitorios.
  - **4G lento:** caminar a los 11,9 s exige menos bytes en la malla lejana y en la colisión. Va con B11 y la fase D.
  - **Calidad visual:**
    - costuras entre teselas (m13);
    - en LOD1 la carcasa del túnel puede asomar hasta ~1 m;
    - el hueco al mar que señalaba la auditoría no se ha reproducido.

**Riesgos:** sin móviles de referencia no se puede cerrar A7; la fase se cierra igualmente, con la medición pendiente anotada.

## Fase B — Tramo piloto (escena E1) a calidad de entrega

**Ámbito:** desde la explanada del Centre d'Informació hasta el kilómetro 0,421 de la ruta (350 m después del torniquete, +44 m, ≈ 4,5 min a 1,4 m/s).

**Objetivo de salida (verificable):**
1. **Cinco vecinos** completan, sin ayuda, la sesión de prueba: llegar, caminar el tramo, abrir la ficha y guardarla en el cuaderno, en el idioma que elijan. Se anotan sus tiempos y comentarios, y todo problema grave queda corregido o registrado.
2. En **2–3 puntos del tramo**, la comparación forzada entre la foto real y la captura a la misma hora solar se hace con el protocolo de `002-verificacion.md` §4, y se informa del resultado sin umbral de aprobado inventado.
3. En los móviles de referencia, dentro del tramo: p95 ≤ 33,3 ms, p99 ≤ 50 ms y ≤ 200 llamadas de dibujo contando las sombras.
4. La ficha y la interfaz del tramo están completas en es, va y en, y la revisión de valenciano está firmada.

**Esfuerzo:** 9–13 días de desarrollo, más el tiempo de las personas. **Depende de:** la Fase A; el zip de Quaternius; las fotos de referencia; la persona que revise el valenciano; la confirmación del parque sobre el Mirador de Ponent.

| Tarea | Detalle | Responsable | Comprobación |
|---|---|---|---|
| B1 Sol y atmósfera | SunCalc para Calp, ajustes de día y atardecer, cielo con atardecer creíble, neblina con la luz del sol dispersada, y AgX frente a ACES decidido con las fotos. | `implementer` + `design-engineer` | Capturas a la hora de las fotos; registro de la decisión |
| B2 Sombras | Sombras en cascada (PCF) en calidad alta; sombras precalculadas por ajuste de luz en calidad baja; contadas en el presupuesto. | `implementer` | Fotogramas y llamadas de dibujo antes y después |
| B3 Material, ajuste fino | Afinar T2.2 en el tramo: costuras (m13), coste en móvil; texturas 2k solo en escritorio y cuando todo lo demás ha cargado. | `implementer` | Capturas en `turnstile` y `viewpoint-1795591637` |
| B4 Sonido ambiente | Paisaje sonoro con licencias revisadas (gaviotas, viento, mar lejano) que arranca con el primer gesto, más un control de volumen y silencio. | `implementer` | Licencias en `CREDITS.md`; la prueba con vecinos recoge su opinión |
| B5 Vegetación del tramo | Especies de las listas oficiales de la GVA, colocadas con la banda infrarroja de la ortofoto y las zonas arboladas de la cartografía 1:5000, con instancias. Nunca la posición real de la silene. | `implementer` + `docs-researcher` (especies) | Llamadas de dibujo ≤ presupuesto; capturas |
| B6 Mar visible | Shader de oleaje y espuma en costa, en lo que se ve desde el tramo. | `implementer` | Capturas desde E1 |
| B7 Caminante animado | Retarget de Quaternius (andar, quieto, correr) según el ADR 0008. | `implementer` | Capturas en 3.ª persona; licencia comprobada en el zip |
| B8 Escalones y edificio del centro | Los 30 escalones con barandilla según OSM; el edificio con la huella del ICV y las alturas del LiDAR (T2.3 y T2.5 del plan 001, limitados al tramo). | `implementer` | Pruebas de geometría; captura |
| B9 Punto de interés completo | La Pobla vista desde el Mirador de Ponent si el parque confirma que está en el tramo; si no, el Centre d'Informació. Ficha de ≤ 60 palabras con "ampliar", fuentes y discrepancias visibles, guardado en el cuaderno (`localStorage`), en es, va y en. | `implementer` + responsable técnico (contenido) | Prueba E2E de ficha y cuaderno; revisión del contenido |
| B10 Un pulgar y paseo automático | "Tocar para caminar" por defecto, joystick opcional, botón de paseo automático, objetivos ≥ 24 px y pistas de 3 s como máximo. | `implementer` + `ui-qa` | Prueba E2E táctil; revisión de accesibilidad |
| B11 Niveles de calidad | Tres niveles: heurística de partida, medición de 2–3 s al arrancar y bajada automática; resolución dinámica con histéresis. | `implementer` | Pruebas unitarias y medición en el móvil |
| B12 Prueba con cinco vecinos | Guion de tareas, observación y notas; corrección de lo encontrado. | Usuario (organiza) + responsable técnico | `docs/specs/002/pruebas-vecinos.md` |

**Riesgos:**
- El zip de Quaternius no llega o su licencia no sirve → la cápsula se queda en el piloto.
- La fluidez en móvil no alcanza el objetivo con sol, sombras y vegetación → la calidad baja recorta sombras y vegetación.
- La revisión de valenciano se retrasa.

## Fase B2 — Segundo hito: túnel → cima (escenas E3, E4 y E5)

**Objetivo de salida (verificable):**
- Las tres escenas tienen la calidad del piloto.
- El túnel lleva dimensiones citadas en `data/curated/tunnel.toml`, o la marca de aproximado bien visible en los créditos.
- Las fichas del túnel, Carabiners y la cima explican la diferencia entre 332 m y 326,9 m y muestran las cuatro formulaciones oficiales sobre menores con su fuente.
- Se repite la prueba con vecinos (pueden ser los mismos cinco).

**Esfuerzo:** 7–10 días. **Depende de:** la visita al túnel (medidas, escalones, fotos); el parque (posición de las paradas oficiales y aclaración de las discrepancias).

| Tarea | Detalle | Responsable |
|---|---|---|
| C1 Túnel definitivo | Sección medida, cuerdas, plataforma de salida (T2.4 del plan 001). | `implementer` + usuario (visita) |
| C2 Escenas E3–E5 | Puntos de observación cada 84–126 m (paradas oficiales, flora, aves); gaviotas en la bifurcación y halcón en las caras norte y noroeste. | `implementer` + `docs-researcher` |
| C3 Fichas del hito | Túnel, bifurcación, Carabiners, cima (vértice geodésico, Ibiza en días claros). | Responsable técnico (contenido) + revisión del parque |
| C4 Validación | Fotos en 2–3 puntos y prueba con vecinos. | Usuario + responsable técnico |

**Riesgos:** sin la visita, el túnel sigue siendo provisional; sin el parque, las paradas 2 a 5 no se pueden situar con rigor.

## Fase C — Tramo intermedio (E2) y los tres modos

**Objetivo de salida (verificable):**
- E2 con la calidad del piloto.
- **Ruta de clase:** preparación de 2 min, E1, salto a E3 y E5, 6–8 tareas con respuesta inmediata y síntesis imprimible. Una persona docente la prueba en 20–25 min.
- **Guía docente:** cita el Decreto 106/2022 más el 96/2026, y el 107/2022 más el 66/2024 con las anulaciones del TSJCV, y una persona docente la revisa.
- **Visita exprés** en 5 min con salto entre miradores e información práctica con fuente y fecha.
- **Paseo libre** con paseo automático, modo foto y retos de flora y aves.

**Esfuerzo:** 7–9 días. **Depende de:** una persona docente de Primaria y otra de ESO; el parque, para la información práctica (antelación de la reserva y precio, que hoy figuran como discrepancia o sin verificar).

## Fase D — Rendimiento, accesibilidad y publicación

**Objetivo de salida (verificable):**
- En los móviles de referencia, la ruta completa cumple p95 ≤ 33,3 ms y p99 ≤ 50 ms, con el terreno visible en ≤ 10 s con red "4G rápido".
- La interfaz cumple WCAG 2.2 AA, con auditoría axe y teclado completo, y hay una guía en texto para quien no tenga WebGL2.
- Modo sin conexión (PWA) para colegios.
- Alojamiento decidido, cabeceras de seguridad y guía de mantenimiento.
- Revisión de WebGPU antes de publicar, **sin migrar**.

**Esfuerzo:** 6–10 días. **Depende de:** la decisión de alojamiento; la matriz de dispositivos.

## Qué se mantiene, cambia o elimina del plan vigente (plan 001)

| Elemento del plan 001 | Decisión | Motivo |
|---|---|---|
| F0 y F1 (hechas) y T1.8b, T1.10, T1.11 | **Se mantienen**, dentro de la Fase A | Son la base y ya están verificadas |
| ADR 0002–0007 | **Se mantienen** | Nada en la verificación las contradice |
| T2.2 material del terreno | **Se mantiene**, como B3 | Ya implementa lo que propone la propuesta de realismo |
| T2.3 superficie del sendero y escalones; T2.5 centro y mobiliario | **Cambian:** se limitan primero al piloto (B8) | Corte vertical |
| T2.4 túnel definitivo | **Cambia:** pasa a la Fase B2 (C1) | Depende de la visita |
| T2.6 caminante | **Cambia:** pasa al piloto (B7) | Forma parte de la calidad de entrega |
| T2.7 cámara y controles | **Cambia:** el táctil de un pulgar, el botón de paseo automático y el giro con teclado se adelantan (A4, B10) | Hallazgos M3 y propuesta de interacción |
| T2.8 luz y sombras | **Cambia:** sube al primer puesto del piloto (B1, B2), con sol real, AgX frente a ACES y sombras por ajuste de luz | Propuesta de realismo verificada |
| T2.9 revisión con un vecino | **Cambia:** se convierte en la prueba con cinco vecinos y el protocolo fotográfico de cada hito | Propuesta del tramo piloto |
| F3 mundo vivo (horizontal) | **Cambia:** se reparte por tramos (B4–B6, C2). El anillo del horizonte con Oltà, Bernia y el Toix queda para B2/C (vistas desde la cima). El modelo de alturas de vegetación (491 MB) solo si las máscaras del piloto no bastan. | Corte vertical; ahorro de datos |
| F4 fichas, cuaderno, idiomas (horizontal) | **Cambia:** una ficha completa en el piloto (B9) y el resto por hitos (C3, C) | Corte vertical |
| F5 rendimiento y publicación | **Se mantiene** como Fase D, con métricas nuevas (p99, tirones, tres niveles, terreno visible ≤ 10 s) | Propuesta de rendimiento ajustada |
| Presupuesto de llamadas de dibujo ≤ 120 (spec 001, AC7) | **Cambia** a 100 de objetivo y 200 de tope, contando las sombras | Propuesta de rendimiento; sin estándar externo |
| Ritmo de marcha | **Se mantiene** en 1,4 m/s | Decisión del usuario |
| Vegetación y mar antes que el contenido | **Se elimina** como orden de fases | Lo sustituye el corte vertical |
| `BatchedMesh` sin alternativa | **Se elimina** como supuesto | No hay `WEBGL_multi_draw` en Firefox |

## Tareas que dependen de personas

| Tarea | Quién | Necesaria para |
|---|---|---|
| Identidad de git y remoto | Usuario | Fase A |
| Dos móviles de referencia (Android de gama media 2023–2024 e iPhone de 4–5 años) | Usuario o equipo | A7, B, D |
| Descargar el zip de Quaternius (itch.io) | Usuario | B7 |
| Fotos de referencia en 2–3 puntos por hito (trípode, hora anotada, RAW) | Vecino del equipo | B, B2 |
| Organizar la prueba con cinco vecinos | Usuario | B, B2 |
| Revisión del valenciano | Servicio lingüístico municipal u otra persona revisora | B9, C |
| Contacto con el parque (`ifac_cma@gva.es`): posición de las paradas 1–5 y del Mirador de Ponent, formulación sobre menores, antelación de reserva, precio y las 11 discrepancias del registro | Responsable del proyecto | B9, B2, C |
| Visita al túnel: ancho y alto en 3–4 puntos, escalones de la boca oeste, vídeo; mejor un escaneo LiDAR | Vecino del equipo | B2 |
| Docentes de Primaria y ESO para la ruta de clase y la guía | Ajuntament o centros | C |
| Alojamiento y dominio | Ajuntament + responsable técnico | D |

## Riesgos generales

| Riesgo | Probabilidad | Impacto | Respuesta |
|---|---|---|---|
| Trabajo sin copia remota | Hoy, cierta | Pérdida total | A1 antes que nada |
| Personas no disponibles (vecinos, docentes, parque) | Media | Hitos sin validar | Seguir con lo técnico y dejar el hito "pendiente de validación", no "hecho" |
| Rendimiento en móvil por debajo del objetivo | Media | Experiencia pobre en gama media | Tres niveles, medir en cada hito y recortar en calidad baja |
| Discrepancias oficiales sin resolver | Cierta hoy | Fichas con dos o más valores | Se muestran todos con su fuente; nunca se elige |
| Licencias (QAL, sonidos CC BY-SA, ODbL de la colisión) | Baja | Bloqueo de la publicación | Revisión de licencias en cada hito y ADR 0007/0008 al día |
