# 002 — Verificación de la propuesta

- Fecha: 11/10/2026. Trabajo de investigación sin cambios de código.
- Idioma: castellano, para el equipo, como piden los nombres de los entregables.
- Método: para cada propuesta se comprueban dos cosas.
  1. El estado real del repositorio, con archivo:línea, medición o captura.
  2. Las fuentes primarias, con URL y fecha.
- Veredicto posible: **confirmada**, **ajustada** (con el valor nuevo y el motivo) o **rechazada**. Cuando dos fuentes oficiales se contradicen se muestran todas y no se elige.
- Evidencia propia:
  - `docs/audits/002-auditoria.md` y `docs/audits/002-capturas/`: 7 capturas en puntos fijos y mediciones en JSON;
  - análisis del sendero sobre `app/public/assets/generated/trail.json`.
- Fecha de consulta de todas las fuentes: 11/10/2026.
- Limitación importante: los portales de la GVA (`parquesnaturales.gva.es`, `mediambient.gva.es`, `ceice.gva.es`) no respondían desde esta máquina. Su contenido se ha leído en capturas del Internet Archive; la fecha de cada captura se indica. DOGV, BOE, `calpe.es` y `tramita.gva.es` sí se leyeron en directo.

## Tabla de veredictos

| # | Propuesta | Veredicto | Motivo principal |
|---|---|---|---|
| 1 | Tramo piloto de 350 m + segundo hito túnel → cima | **Ajustada** | La idea y el segundo hito se sostienen, pero el tramo necesita límites medidos, un punto de interés con posición confirmada y requisitos previos que hoy faltan (commits, atribución, teclado). |
| 2 | Rendimiento | **Ajustada** | Los objetivos son razonables, pero no son estándares. Hay que medir también p99 y tirones; el criterio de descarga se cumple pero el terreno tarda en verse; los niveles de calidad hoy no se eligen midiendo. |
| 3 | Render | **Ajustada** | WebGL2 se confirma y WebGPU no puede exigirse. AgX frente a ACES se decide con fotos. Las sombras precalculadas dependen de la posición del sol. La neblina estándar no dispersa la luz del sol. |
| 4 | Realismo | **Ajustada** | La luz y el material tienen apoyo en estudios. El sonido sube al tercer puesto por su impacto y su bajo coste, y la validación con fotos necesita un protocolo más estricto. |
| 5 | Escenas | **Ajustada** | Con los datos del sendero, las escenas 1 y 3 son demasiado cortas y la 2 demasiado larga. Se proponen límites nuevos, y faltan puntos de observación en un hueco de 385 m. |
| 6 | Interacción | **Ajustada** | En 4G rápido se camina viendo el terreno a los 7,4 s; en 4G lento no. El control táctil es hoy de dos pulgares. Paseo automático y salto entre anclas ya existen sin interfaz. |
| 7 | Educativa y recreativa | **Ajustada** | El Decreto 106/2022 está modificado por el 96/2026 y el de ESO es el 107/2022 modificado por el 66/2024. La ruta de clase no cabe en 20–25 min recorriendo todo; la información práctica tiene contradicciones oficiales. |

Ninguna propuesta se rechaza.

---

## 1. Tramo piloto

**Propuesta:** terminar a calidad de entrega los primeros 350 m desde el torniquete, antes de extender nada. Incluye material del terreno definitivo, vegetación, mar, cielo, caminante animado, sonido ambiente y un punto de interés completo con ficha y cuaderno en tres idiomas, probado con cinco vecinos. Segundo hito: del túnel a la cima.

**Estado real (repositorio y mediciones).** Datos de `trail.json`, regenerado a las 12:38 con las alturas curadas del túnel; pendiente suavizada en ventanas de 10 m.
- El torniquete está en el kilómetro 0,071 de la ruta. 350 m después se llega al **kilómetro ≈ 0,421**: se sube de 75,7 a 119,7 m (**+44 m**).
- A la velocidad de la app (1,4 m/s, que se mantiene por decisión del usuario) son **≈ 4,2 min**. Andando de verdad, según la función de Tobler, son ≈ 7,0 min.
- En el tramo hay solo dos anclas: el torniquete y el mirador OSM 1795591637 (km 0,192). El siguiente mirador está en el km 0,577.
- Las paradas oficiales 1 a 5 (Mirador de Ponent, restos del poblado ibérico, pinos tumbados, área de descanso, Mirador del Botànic Cavanilles) **no tienen posición publicada**. Su correspondencia con nodos OSM está **sin verificar**.
- La Pobla d'Ifac queda fuera del pasillo, a 86 m del sendero, y según la GVA su muralla se ve desde el Mirador de Ponent.

Estado de cada componente:

| Componente | Estado |
|---|---|
| Material del terreno | Hecho en borrador (T2.2, `app/src/world/terrain/material.ts`); coste medido en GPU real: +0,5 a +1,2 ms. |
| Cielo, sol y mar | Solo versiones básicas (`app/src/world/{sky,sea}.ts`, sol fijo). |
| Vegetación | No empezada. Podría hacerse sin descargar nada más, con la banda infrarroja de la ortofoto ya descargada y las zonas arboladas de la cartografía 1:5000. |
| Caminante animado | Bloqueado: falta el zip de Quaternius (ADR 0008), que tiene que descargar el usuario. |
| Sonido | No empezado. Candidato: gaviota de Commons, CC BY-SA 4.0, con licencia por archivo a revisar. |
| Ficha, cuaderno e idiomas | No empezados. El registro de datos existe (`content/facts.json`). |

Faltan además requisitos previos que hoy bloquean cualquier prueba con vecinos (ver la auditoría):
- B2: sin commits;
- M1: sin atribución en pantalla;
- M3: sin giro por teclado;
- m11: sin aviso de carga visible.

**Fuentes.**
- Paradas oficiales: página "Ruta Roja descripció" (va) de la GVA, captura del Internet Archive del 08/08/2022, https://parquesnaturales.gva.es/va/web/pn-penyal-d-ifac/ruta-roja-descripcion. Lista las 9 paradas en orden, sin distancias entre ellas.
- Menores pasado el túnel. **Hay contradicción; se muestran todas las versiones y no se elige:**

| Fuente | Formulación |
|---|---|
| GVA, "Recomendaciones para la visita", es (IA 16/04/2026) y va (IA 14/03/2026) | **No se permite** continuar a menores de 18 años |
| GVA, portada del parque, es (IA 23/08/2026) y va (IA 30/09/2026) | **Se desaconseja** |
| Guía de reservas de la GVA (PDF "Guia Web Castellano Diciembre 22", creado 17/03/2023) | **No se recomienda** |
| GVA, Ruta Roja, va (IA 08/08/2022) | No aconsejable con menores; **de 16 a 18 años, siempre con un adulto** |
| Ajuntament de Calp, `calpe.es` (en directo) | Sin norma propia; enlaza una copia de la guía de la GVA |

- Accesibilidad: página de la GVA sobre accesibilidad (IA 28/08/2026). La ruta está adaptada para la mayoría de colectivos solo hasta el túnel; seguir a la cima se describe como "totalmente desaconsejado".
- Prueba con cinco usuarios: la referencia habitual es Nielsen y Landauer (1993), *A mathematical model of the finding of usability problems*, INTERCHI '93, doi:10.1145/169059.169166. **Sin verificar en esta sesión:** no se ha consultado el texto.

**Veredicto: ajustada.**
- **Tramo piloto:** desde la explanada del Centre d'Informació hasta el kilómetro 0,421 de la ruta (350 m después del torniquete, +44 m). Son ≈ 4,5 min a 1,4 m/s.
- **Punto de interés del piloto:** la Pobla d'Ifac vista desde el Mirador de Ponent, *si el parque confirma que ese mirador está en el tramo*. Si no lo confirma, el Centre d'Informació.
- **Antes del piloto:** cerrar B1–B2, M1, M3 y m11 de la auditoría.
- **Vegetación del piloto:** con las máscaras ya disponibles (banda infrarroja y zonas arboladas), sin pedir la descarga del modelo de alturas de vegetación (491 MB).
- **Segundo hito (túnel → cima): confirmado.** Sea cual sea la versión oficial (prohibido, desaconsejado, no recomendado, o de 16 a 18 años con un adulto), los menores no hacen ese tramo de forma ordinaria, y para personas con movilidad reducida está desaconsejado. Por eso es el tramo con más valor virtual. La ficha mostrará las cuatro formulaciones con su fuente hasta que el parque las unifique.

## 2. Rendimiento

**Propuesta:**
- 30 fps estables, con un tiempo de fotograma ≤ 33 ms en el percentil 95;
- 100 llamadas de dibujo como objetivo y 200 como tope;
- DPR ≤ 1,5 con ajuste dinámico;
- descarga inicial ≤ 15 MB;
- tres niveles de calidad elegidos midiendo al arrancar;
- instancias o lotes y texturas KTX2.

**Estado real.**
- **Llamadas de dibujo:** 5–18 en los 7 puntos fijos, todavía sin vegetación (`docs/audits/002-capturas/metrics.json`).
- **Triángulos:** 98.000–296.000.
- **Tiempo de fotograma en GPU real** (Apple M1 Pro, Metal, 2560×1440, medido por el agente de T2.2): p95 de 2,9–3,6 ms en calidad baja y de 3,6–4,3 ms en alta.
- **Sin medición en móvil real (T1.11).** Bajo SwiftShader el p95 se satura en 100 ms porque el bucle recorta el delta (hallazgo m2 de la auditoría).
- **DPR:** limitado a 1,5 con puntero grueso (`app/src/core/renderer.ts:19-20`, `:63`). **No hay ajuste dinámico.**
- **Descarga hasta poder caminar** (producción, sin caché): 1,86 MB en calidad baja y 4,32 MB en alta, frente a 15 MB.
- **Descarga con el terreno asentado:** 9,16 MB en calidad baja y **17,08 MB** en alta (`prod-net.json`).
- **Niveles de calidad:** hay **dos**, elegidos por heurística (`app/src/world/terrain/quality.ts:27-32`). Safari no expone `deviceMemory`, así que todos los iPhone acaban en calidad baja (m5).
- **Texturas:** KTX2 en uso.
- **Instancias:** todavía no se usan, porque no hay vegetación.

**Fuentes.**
- No hay ningún estándar de llamadas de dibujo para navegador móvil. El dato más cercano es la guía de Meta para Quest: 80–200 llamadas es "ocupado" y 200–300 "medio", con la advertencia de que los resultados varían (https://developers.meta.com/horizon/documentation/unreal/unreal-debug-android, 14/04/2026).
- MDN, *WebGL best practices*, solo da consejos cualitativos: https://developer.mozilla.org/en-US/docs/Web/API/WebGL_API/WebGL_best_practices (07/10/2026).
- Fluidez:
  - Android cuenta como "lento" un fotograma de más de 16 ms (https://developer.android.com/topic/performance/vitals/render, 21/09/2026).
  - Apple considera buena una tasa de tirones ≤ 10 ms/s y de aviso ≤ 25 ms/s (documentación de Apple, consultada por el agente).
  - Core Web Vitals usa el percentil 75 de las cargas de página (https://web.dev/articles/vitals).
  - El p95 ≤ 33 ms equivale aproximadamente a 25 ms/s de tirones, justo el límite de aviso de Apple.
- 60 fps se distingue de 30 fps: Claypool 2006, doi:10.1117/12.648609; Tokey 2026, doi:10.1145/3837059. Los picos ocasionales de latencia favorecen el mareo: Stauffert 2020, doi:10.3389/frvir.2020.582204, una revisión sobre cascos de realidad virtual.
- `BatchedMesh` necesita `WEBGL_multi_draw`, que Firefox no tiene (código de three r186, `BatchedMesh.js`).
- KTX2Loader elige ASTC o ETC2 en iOS y Android (`examples/jsm/loaders/KTX2Loader.js:784-837` en r186). Ambos formatos están en ≈ 99,9 % de los dispositivos WebGL2 según web3dsurvey.com (sin fecha).

**Veredicto: ajustada.**
- **Fluidez:** se mantiene "30 fps estables" y se añaden más criterios:
  - p95 ≤ 33,3 ms **y** p99 ≤ 50 ms;
  - número de fotogramas por encima de 50 ms por minuto;
  - se mide con el delta real de `requestAnimationFrame`, sin recortar, en los móviles de referencia y a lo largo de cada escena.
- **Llamadas de dibujo:** se mantienen 100 de objetivo y 200 de tope como presupuesto interno, no como estándar, **contando los pases de sombra**.
- **DPR:** se mantiene 1,5 y se añade una resolución dinámica por pasos con histéresis.
- **Descarga:** el criterio de 15 MB antes del primer paso ya se cumple. Se añade que el terreno sea visible en ≤ 10 s con red "4G rápido" (hoy 7,4 s) y que, con el terreno asentado, no se pasen los 15 MB en los niveles móviles.
- **Niveles de calidad:** **tres**, con una heurística como punto de partida, 2–3 s de medición real de la GPU al arrancar y bajada automática de nivel si cae la fluidez durante la sesión.
- **Lotes:** `BatchedMesh` con una alternativa para Firefox.

## 3. Render

**Propuesta:**
- mantener `WebGLRenderer` con WebGL2;
- verificar WebGPU para una migración posterior, sin hacerla ahora;
- salida sRGB con AgX;
- un sol con sombras en cascada en calidad alta y sombras precalculadas en baja;
- neblina por distancia;
- ningún posprocesado salvo el antialiasing.

**Estado real.**
- **Renderer:** `WebGLRenderer` con salida sRGB y **tone mapping ACES**, no AgX (`app/src/core/renderer.ts:56-58`). El comentario del código dice que AgX desaturaría la roca; esa afirmación no se ha probado.
- **Material:** usa `onBeforeCompile` (`material.ts:316`), un mecanismo que solo existe en `WebGLRenderer`.
- **Luz y sombras:** el sol es fijo y no hay sombras.
- **Neblina:** lineal, de tipo `Fog`.
- **Antialiasing:** activado con puntero fino y desactivado en móvil.

**Fuentes.**
- WebGPU en Safari:
  - Safari 26 añadió WebGPU (iOS, iPadOS y macOS 26; notas de Safari 26, 15/09/2025: https://developer.apple.com/documentation/safari-release-notes/safari-26-release-notes).
  - Según Apple, el 79 % de los iPhone estaban en iOS 26 y el 14 % en iOS 18, con datos del 07/06/2026 (https://developer.apple.com/support/app-store/).
- WebGPU en Android y Firefox:
  - Chrome para Android lo tiene desde la versión 121, en Android 12 o posterior con GPU Qualcomm o ARM (https://developer.chrome.com/blog/new-in-webgpu-121, 18/01/2024).
  - Chrome no publica el porcentaje de cobertura (**sin verificar**).
  - Firefox para Android no lo tiene (MDN browser-compat-data, `api/GPU.json`).
  - MDN marca la API como de "disponibilidad limitada" (02/09/2026), y la especificación del W3C sigue siendo un borrador de recomendación candidata (15/09/2026).
- `WebGPURenderer` en r186:
  - Tiene modo `forceWebGL` (`src/renderers/webgpu/WebGPURenderer.js:41-57`).
  - Su API cambia en cada versión: la guía de migración de three.js lista cambios incompatibles de r182 a r187.
  - `onBeforeCompile` no existe en `WebGPURenderer`.
- AgX existe desde r160 (`src/constants.js:473` en r186). Funciona con color lineal a la entrada y a la salida, seguido de la conversión sRGB.
- Sombras:
  - `CSM` sigue en r186 y solo funciona con WebGL (`examples/jsm/csm/CSM.js:32`); la versión para WebGPU es `CSMShadowNode`.
  - **`PCFSoftShadowMap` ya no existe**: se sustituye por PCF con un aviso (`src/renderers/webgl/WebGLShadowMap.js:99-101`).
- Neblina: `Fog` y `FogExp2` no modelan la luz del sol dispersada en el aire.
- Cielo: el cielo `Sky` de three es el modelo Preetham (1999). Zotti (2007) encontró desviaciones frente a cielos medidos, y Hošek y Wilkie (2012) mejoran atardeceres y turbidez. Son estudios de precisión, no de percepción.
- Antialiasing en móvil: según el ejemplo de Khronos y Arm para Vulkan, 4× MSAA es barato en GPU de mosaicos si se resuelve en el chip. **Sin verificar** que en WebGL ocurra lo mismo.

**Veredicto: ajustada.**
- **WebGL2: confirmado.** WebGPU **no** debe exigirse: alrededor de 1 de cada 5 iPhone no lo tiene, Firefox para Android tampoco, y en Android depende de la GPU.
- **Preparar la migración sin hacerla:**
  - mantener el GLSL y `onBeforeCompile` en pocos módulos (terreno, cielo, mar, vegetación) detrás de interfaces pequeñas;
  - mantener glTF, KTX2 y meshopt independientes del renderer;
  - fijar three 0.186.x;
  - revisar WebGPU de nuevo antes de publicar.
- **AgX:** pasa a ser candidato por defecto, pero AgX frente a ACES se decide **con el protocolo de comparación con fotos** en el piloto. Hasta entonces se queda ACES, que es lo que hay hoy.
- **Sombras en cascada:** solo en calidad alta, con PCF (no PCF suave), y contando las cascadas en el presupuesto de llamadas de dibujo.
- **Sombras precalculadas:** dependen de la posición del sol, así que se generan una por ajuste (día y atardecer).
- **Neblina:** por distancia y con la luz del sol dispersada (en el shader del cielo y del terreno). La `Fog` estándar no basta para el atardecer.
- **Posprocesado:** ninguno, confirmado. El antialiasing en móvil se decide midiendo en los móviles de referencia.

## 4. Realismo

**Propuesta:** prioridad por impacto y coste, en este orden: luz y atmósfera con el sol real, material del terreno (ortofoto a distancia, roca cerca y triplanar solo en pendientes fuertes), vegetación con especies reales, mar y sonido. Cada mejora se valida comparando la captura con una foto real desde el mismo punto.

**Estado real.** El material ya hace lo que se propone: triplanar entre 45° y 55°, detalle cercano que se desvanece entre 14 y 30 m, y tono de la ortofoto (`app/src/world/terrain/material.ts:27-30`). Luz, sol, vegetación, mar con oleaje y sonido están sin empezar.

**Fuentes.**
- Rademacher et al. (2001), doi:10.2312/egwr/egwr01/235-248: las sombras suaves y la rugosidad de la superficie influyen de forma significativa en que una imagen parezca real; el número de luces, de objetos y de formas, no. Limitaciones: bloques en gris, no exteriores.
- Slater et al. (2009), doi:10.1109/mcg.2009.55: las sombras dinámicas y los reflejos aumentan la presencia (con casco de realidad virtual).
- Kern y Ellermeier (2020), doi:10.3389/frobt.2020.00020: en un paseo virtual por un parque, el sonido tiene efectos grandes sobre presencia y realismo, y el paisaje sonoro pesa más que los pasos.
- Poeschl et al. (2013), doi:10.1109/vr.2013.6549396: efecto de medio a grande del sonido sobre la presencia.
- No se ha encontrado apoyo para el orden vegetación > mar > sonido. Los estudios de paisaje (Daniel y Meitner 2001; Lange 2001; Appleton y Lovett 2003) están **sin verificar**: son de pago y solo se han visto resúmenes secundarios.
- Validación con fotos:
  - Baboud et al. (2011), doi:10.1109/cvpr.2011.5995727: registro de fotos sobre el MDT por la silueta del horizonte.
  - Mantiuk et al. (2012), doi:10.1111/j.1467-8659.2012.03188.x: la comparación forzada por pares es el método con menos varianza.
  - DISTS (doi:10.1109/tpami.2020.3045810) muestra que las métricas píxel a píxel castigan texturas como la hierba, el mar o las nubes aunque estén bien.

**Veredicto: ajustada.**
- **Orden nuevo:**
  1. Luz y atmósfera con el sol real.
  2. Material del terreno (ya en borrador; se afina).
  3. **Sonido ambiente.** Sube porque la evidencia muestra efectos grandes y cuesta poco.
  4. Vegetación con las especies reales del parque.
  5. Mar.
- **Validación con fotos, con un protocolo explícito:**
  1. Foto desde un punto conocido, con trípode, objetivo fijo y RAW; se anotan la hora y la posición del sol.
  2. Registro de la cámara sobre la silueta del MDT, indicando el error en minutos de arco.
  3. Captura del render a la misma hora solar.
  4. Prueba de elección forzada con 20–30 personas: "¿cuál es la foto?" y "¿cuál se parece más al lugar?", con controles.
  5. SSIM, LPIPS o FLIP solo como diagnóstico en recortes estáticos, nunca como umbral para aprobar.
  6. El informe dice "parecido en N puntos en estas condiciones", nunca "fotorrealista".

## 5. Escenas

**Propuesta:** cinco escenas con identidad propia: acceso y centro, subida al túnel, túnel, tramo posterior con Carabiners, y cima. Cada una de 3–5 min, con algo que observar cada 60–90 s. Ajustar los límites a los datos.

**Estado real.** Kilometraje en 3D sobre `trail.json`; tiempos a 1,4 m/s, el ritmo de la app que el usuario decidió mantener, y entre paréntesis los de Tobler:

| Tramo según la propuesta | Distancia | Desnivel | Tiempo en la app (Tobler) |
|---|---|---|---|
| Centro → torniquete | 31 m | +5,6 m | 0,4 min (0,7) |
| Torniquete → boca oeste | 749 m | +94,8 m | 8,9 min (14,8) |
| Túnel | 54 m | +21,3 m | 0,6 min (2,9) |
| Túnel → bifurcación | 365 m | +34,0 m | 4,3 min (7,1) |
| Bifurcación → Carabiners (solo ida) | 261 m | +0,5 m | 3,1 min (3,9) |
| Bifurcación → cima | 548 m | +99,6 m | 6,5 min (14,9) |

- Hay **12 anclas**. El hueco más largo, de **385 m (≈ 4,6 min)**, va del mirador OSM 1795591637 (km 0,192) al 3635481356 (km 0,577).
- Para tener algo que observar cada 60–90 s a 1,4 m/s hace falta un punto cada 84–126 m: **16–20 puntos** en la ruta principal.
- Las paradas oficiales 2 a 5 probablemente caen en ese hueco, pero no tienen posición publicada (**sin verificar**). La página "Descarga tu ruta" no está archivada y el mapa en PDF del Ajuntament no tiene capa de texto.
- Totales oficiales para comparar: GVA, unos 2 km ida y vuelta y 1 h 30 de subida; Ajuntament, unas 2 h 30. Ya figuran como discrepancia en `content/facts.json`.

**Veredicto: ajustada.** Cinco escenas con límites medidos:

| Escena | Límites (km de la ruta) | Tiempo en la app |
|---|---|---|
| E1 Acceso, centro y primer tramo (coincide con el piloto) | Centro → km 0,421 | ≈ 4,5 min |
| E2 Subida al túnel | km 0,421 → boca oeste (km 0,820) | ≈ 4,8 min |
| E3 Túnel y plataforma de salida | km 0,820 → 0,874, con parada en la plataforma | ≈ 0,6 min de marcha más la parada; **excepción** a los 3–5 min, el túnel mide 54 m |
| E4 Tramo posterior y Carabiners | km 0,874 → bifurcación (km 1,239) → Carabiners (+261 m) | ≈ 7,4 min solo ida; **por encima de 5**: se acepta o se divide en dos subescenas |
| E5 Cima | km 1,239 → 1,787 | ≈ 6,5 min; ligeramente por encima |

El ritmo de una observación cada 60–90 s exige situar las paradas oficiales, con un mapa del parque o una visita, y añadir puntos de flora y aves. Hasta entonces el criterio no se puede cumplir.

## 6. Interacción

**Propuesta:**
- caminar antes de 10 s y sin leer instrucciones;
- táctil con un pulgar;
- paseo automático;
- salto rápido entre miradores visitados;
- descubrimiento por cercanía y mirada;
- fichas de ≤ 60 palabras con opción de ampliar;
- cuaderno en el dispositivo, sin cuentas.

**Estado real.**
- **Tiempos de carga** (producción, sin caché, torniquete, `docs/audits/002-capturas/throttle.json`):
  - con red "4G rápido": primer paso a los **2,0 s** y terreno visible a los **7,4 s**;
  - con "4G lento": **9,9 s** y **21,3 s**.
- **Sin aviso de carga visible** (`app/index.html:53`).
- **Mirar exige un clic** (bloqueo del puntero) y **el teclado no gira**: las flechas izquierda y derecha desplazan de lado (`app/src/input/mapping.ts:11-12`).
- **El táctil usa dos pulgares**: joystick a la izquierda y arrastre a la derecha (`app/src/input/touch.ts:26-27`).
- **Paseo automático:** existe (`app/src/player/autowalk.ts`, `?autowalk=`, tecla P), pero sin botón táctil.
- **Salto a un ancla:** existe con `?start=<ancla>` (`app/src/world/trail.ts`, `startAnchor`), pero sin interfaz.
- **Descubrimiento:** la cercanía se registra (`anchorsReached`); la mirada, no.
- **Fichas y cuaderno:** sin empezar.

**Fuentes.**
- WCAG 2.2:
  - 2.5.7: los arrastres necesitan una alternativa con un solo puntero (https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements.html, 10/08/2026);
  - 2.5.8: los objetivos táctiles deben medir ≥ 24 px CSS.
- Parhi et al. (2006), doi:10.1145/1152215.1152260: objetivos de ~9–10 mm para el pulgar. No se ha encontrado ninguna comparación revisada entre joystick y "tocar para caminar" (**sin verificar**).
- Espera tolerable:
  - ≈ 2 s, y la tolerancia aumenta si hay indicación de progreso (Nah 2004, doi:10.1080/01449290410001669914);
  - el perjuicio deja de crecer hacia los 4–8 s (Galletta 2004, doi:10.17705/1jais.00044);
  - un `<canvas>` no cuenta como LCP (https://web.dev/articles/lcp, 04/09/2025).
- Lectura: 238 palabras por minuto en lectura silenciosa (Brysbaert 2019, doi:10.1016/j.jml.2019.104047). 60 palabras son ≈ 15 s. No hay un límite de palabras respaldado por estudios revisados; el de 75 palabras (Serrell) solo se ha visto citado por terceros.

**Veredicto: ajustada.**
- **"Caminar antes de 10 s"** se redefine así:
  - terreno visible y caminando en ≤ 10 s con red "4G rápido";
  - con "4G lento", aviso de carga visible en ≤ 2,5 s y caminar con el terreno de baja resolución en ≤ 10 s.
  - Para conseguirlo hay que cargar antes el anillo lejano y los LOD2 y servir con compresión.
- **"Sin leer instrucciones":** pistas en pantalla de 3 s como máximo, giro con teclado y mirar sin clic previo.
- **Un pulgar:** por defecto "tocar para caminar" y paseo automático, con joystick opcional y objetivos ≥ 24 px (mejor ~9 mm).
- **Salto entre miradores y cercanía: confirmados**; ya tienen base técnica.
- **Mirada:** secundaria, solo como ayuda para el descubrimiento.
- **Fichas de ≤ 60 palabras con opción de ampliar: confirmadas** como regla editorial, no como resultado de investigación.
- **Cuaderno en el dispositivo, sin cuentas: confirmado.**

## 7. Educativa y recreativa

**Propuesta:** tres modos.
- **Ruta de clase:** 20–25 min, con una pregunta guía, 6–8 tareas con respuesta inmediata, síntesis imprimible y guía docente contrastada con el Decreto 106/2022 de Primaria en su redacción vigente y con el decreto valenciano de ESO en vigor.
- **Visita exprés de 5 min:** miradores principales e información práctica de reserva y aforo verificada con el parque.
- **Paseo libre:** paseo automático, modo foto y retos de flora y aves.

**Estado real.**
- La ruta principal entera son ≈ 21 min de marcha a 1,4 m/s (centro → cima, 1.787 m), sin contar tareas.
- Paseo automático y salto a anclas: existen. Modo foto, retos, tareas, síntesis y guía: no.

**Fuentes.**

Decreto 106/2022 (Primaria):
- Decreto 106/2022, de 5 de agosto, DOGV núm. 9402 de 10/08/2022, ref. 2022/7572, https://dogv.gva.es/datos/2022/08/10/pdf/2022_7572.pdf.
- Lo **modifica el Decreto 96/2026**, de 19 de junio: DOGV núm. 10391 de 25/06/2026, CVE DOGV-C-2026-21223, se aplica desde el curso 2026-27, https://dogv.gva.es/datos/2026/06/25/pdf/2026_21223_es.pdf.
  - Cambian, entre otros, los artículos 9 (áreas) y 10, que pasa a ser "Fomento de la lectura".
  - En el Anexo III cambian los criterios de evaluación.
- **No existe texto consolidado** (la API del DOGV lo marca como pendiente), así que la "redacción vigente" es el texto original más el Decreto 96/2026.
- Lo más relevante para esta experiencia está en el área de Conocimiento del Medio Natural, Social y Cultural (Anexo III):
  - competencias específicas CE3 (preguntas sobre el medio natural), CE5 (problemas causados por la acción humana), CE6 (cronología histórica) y CE8 (patrimonio natural, histórico y cultural de la Comunitat Valenciana);
  - saberes del bloque 1 (seres vivos; paisajes y ecosistemas; desarrollo sostenible) y del bloque 3 (educación patrimonial; sociedades medievales).

Decreto 107/2022 (ESO):
- Decreto 107/2022, de 5 de agosto, DOGV núm. 9403 de 11/08/2022, ref. 2022/7573.
- Lo **modifica el Decreto 66/2024**: DOGV núm. 9878 de 26/06/2024, ref. 2024/6134, que sustituye el currículo de Biología y Geología.
- Las sentencias del TSJCV publicadas en el DOGV núm. 9704 anulan los artículos 10.3, 11.3 y 15.7 (este último solo para 1.º a 3.º).
- Relevante:
  - Biología y Geología: método científico y observación de campo; seres vivos y biodiversidad; la Tierra; ecología y sostenibilidad;
  - Geografía e Historia: geografía física de la Comunitat Valenciana; Edad Media y Reino de Valencia; CE5 sostenibilidad; CE9 patrimonio.
- **Sin verificar:** a qué curso corresponde cada contenido, porque las columnas se pierden al extraer el texto, y los saberes de las áreas de lengua.

Pedagogía (estudios revisados):
- Villena-Taranilla et al. (2022), doi:10.1016/j.edurev.2022.100434, metaanálisis de Infantil a 6.º de Primaria:
  - efecto global de 0,64;
  - en entornos no inmersivos, que es nuestro caso, solo 0,32;
  - intervenciones de menos de 2 h: 0,72.
- Lazonder y Harmsen (2016), doi:10.3102/0034654315627366: el guiado en el aprendizaje por indagación da d = 0,50.
- Wisniewski, Zierer y Hattie (2020), doi:10.3389/fpsyg.2019.03087: la retroalimentación da d = 0,48, con mucha variación.
- Petersen et al. (2020), doi:10.1111/bjet.12991: una preparación narrada antes de la excursión virtual mejora la transferencia.
- **No** hay ningún estudio controlado que compare una excursión virtual con una real en Primaria o ESO (**sin verificar** que exista).

Información práctica:
- **Reserva:** trámite `CITA_PREVIA_PARQUES` en tramita.gva.es (en directo; tras un inicio de sesión).
- **Aforo:** 300 personas al día "en principio" (PRUG, art. 26, Decreto 260/1993, DOGV 21/01/1994).
- **Quién reserva:** todas las personas, también los niños.
- **Horario:** sin franjas; de la salida a la puesta del sol (GVA, IA 28/08/2026).
- **Grupos de más de 15 personas:** aviso con 15 días de antelación (IA 28/08/2026).
- **Antelación de la reserva. Hay contradicción; se muestran todas las versiones:**

| Fuente | Antelación |
|---|---|
| GVA, portada y guía | Hasta 10 días, y el mismo día si quedan plazas |
| Copia de la guía alojada en `calpe.es` (01/2023) | Hasta un mes |
| Nota municipal de `calpe.es`, hacia 2020 | Un mínimo de 4 días |

- **Precio:** no aparece en ninguna fuente (**sin verificar**; no debe darse por gratuito).

**Veredicto: ajustada.**
- **Ruta de clase:** 20–25 min **no** permiten recorrer toda la ruta con tareas. Se propone:
  - preparación narrada de 2 min;
  - E1 completa;
  - salto a E3 y E5 con paseo automático;
  - 6–8 tareas con respuesta inmediata;
  - síntesis imprimible.
  - Expectativa realista: el efecto en entornos no inmersivos es pequeño (0,32).
- **Guía docente:** debe citar el **Decreto 106/2022 más el Decreto 96/2026** (sin texto consolidado) y el **Decreto 107/2022 más el 66/2024, con las anulaciones del TSJCV**. Necesita la revisión de un docente; la asignación por cursos está sin verificar.
- **Visita exprés de 5 min: confirmada** con salto entre miradores. La información práctica se muestra con su fuente y fecha, enlaza al trámite oficial, y presenta las antelaciones en conflicto hasta que el parque las aclare. El precio no se menciona.
- **Paseo libre:** confirmado. Lo respalda la página oficial de accesibilidad: la ruta está adaptada solo hasta el túnel y la cima está desaconsejada. Modo foto y retos son trabajo nuevo.

## Lo que queda sin verificar

- Si las páginas de la GVA siguen diciendo hoy lo mismo que sus capturas del Internet Archive, y la posición de las paradas oficiales 1 a 5.
- El precio de la reserva.
- El porcentaje de Android con WebGPU.
- El coste real del antialiasing en móviles con WebGL.
- Estudios de paisaje y perspectiva aérea.
- La comparación joystick frente a "tocar para caminar".
- El texto de Nielsen y Landauer (1993).
- La asignación por cursos en los decretos de ESO, y los saberes de las áreas de lengua.
- Cualquier estudio que compare una excursión virtual con una real en Primaria o ESO.
