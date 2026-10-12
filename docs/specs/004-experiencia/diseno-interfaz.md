# 004 — Diseño de la interfaz del jugador (X0.1)

- Estado: **propuesta del diseño, 12/10/2026**, para revisión del responsable técnico. Tarea X0.1 de `plan.md`.
- Dirección aprobada por el usuario (no se reabre): interfaz **mínima y flotante**, pensada para niños, sin atajos ni gestos escondidos, icono **y** palabra en cada control, objetivos de 44 px, paso real de 1,4 m/s.
- Entradas: `propuesta.md` (§3, §4.1, §4.5, §4.6, §8), `docs/research/005-experiencia-referentes.md` (§1.2 y la lista P0 de §2.3), los bocetos `boceto-escritorio.jpg` y `boceto-movil.jpg`, y la interfaz actual (`app/index.html`, `app/src/ui/strings.ts`, `app/src/ui/hud.ts`, `app/src/input/touch.ts`).
- Prototipo estático (fuera del repo): ver §9. Todas las capturas de fondo son del juego real (vista previa de producción, 12/10/2026).
- **Valores de ejemplo** en el prototipo y en este documento: la hora (12:40), la temperatura (22°), la hora del historial (12:38) y la fecha del sello (12/10/2026). Todo lo demás es real: altitudes de los anclajes de `trail.json`, distancias medidas sobre la ruta, coordenadas del "GPS simulado" (EPSG:25830 → WGS84 con pyproj), ortofoto ICV 2024, textos y fuentes de `content/`.

## 1. Dirección

**Tres palabras:** sereno, mineral, honesto.

- El paisaje manda. La interfaz es texto blanco con un **reborde oscuro fino** y un halo suave, sin cajas. Solo los paneles que se piden (Más, ficha, cuaderno, mapa) tienen superficie, y es opaca.
- Una sola familia tipográfica, la del sistema (`system-ui`): cero bytes de fuentes, buena cobertura de `l·l`, `à`, `ç`, cifras tabulares. Jerarquía por tamaño y peso (400/500), nunca por gris ni por opacidad.
- Color: neutros cálidos de "roca en sombra" (`ink`) y "papel de cuaderno" (`paper`); un único acento, el **ámbar** de la ruta, que también es el color del foco y de la acción principal. Estados con colores Okabe–Ito (verde azulado, naranja) y siempre con icono y palabra.
- Referentes de patrón: la cifra y la ruta de Komoot (perfil con "tú estás aquí"), los rótulos de subtítulo de juego (blanco con reborde, legible sobre cualquier fondo) y el mapa de papel de *Firewatch* solo como tono del cuaderno, no como mecánica.
- **Lo que no se hace:** degradados decorativos, cajas translúcidas con desenfoque (`backdrop-filter`), "card soup", gris sobre gris, emojis como iconos (el botón actual de cámara, `touch.ts:48`, usa 📷 y desaparece), ilustraciones genéricas, todo centrado.

## 2. Tokens

Tres capas: **primitivo → semántico → componente**. Los componentes solo usan semánticos o de componente. El fichero de referencia completo es el `tokens.css` del prototipo (§9); aquí va lo que la implementación debe copiar tal cual. En la app irán como variables CSS en un `ui/tokens.css` cargado por `index.html` (no hay Tailwind en el proyecto).

### 2.1 Primitivos (OKLCH; hex para revisión)

| Token | OKLCH | Hex | Uso previsto |
|---|---|---|---|
| `--ink-950` | `0.17 0.012 60` | `#130e0a` | Halo, reborde, fondo de alto contraste |
| `--ink-900` | `0.21 0.012 60` | `#1d1713` | Fondo de hoja oscura, texto sobre papel |
| `--ink-800` | `0.28 0.012 60` | `#2d2823` | Superficie elevada oscura (teselas) |
| `--ink-700` | `0.37 0.012 60` | `#453e39` | Separadores oscuros (decorativos) |
| `--ink-600` | `0.46 0.011 60` | `#5d5752` | Texto secundario sobre papel |
| `--ink-500` | `0.55 0.010 65` | `#76706c` | Bordes de control (oscuro y papel) |
| `--ink-300` | `0.76 0.008 75` | `#b4b0ac` | Texto secundario sobre oscuro |
| `--ink-200` | `0.86 0.008 80` | `#d4d0cb` | Separadores sobre papel |
| `--ink-100` | `0.93 0.008 85` | `#eae7e2` | Texto sobre hoja oscura |
| `--paper-50` | `0.975 0.010 85` | `#faf6ef` | Fondo de hoja clara |
| `--paper-100` | `0.945 0.014 82` | `#f2ece3` | Superficie elevada clara |
| `--white` | `1 0 0` | `#ffffff` | Texto e iconos flotantes |
| `--amber-200` | `0.90 0.11 88` | `#fcda86` | "Hora elegida", etiqueta seleccionada en el mapa |
| `--amber-300` | `0.85 0.145 82` | `#fdc44f` | Ruta, foco, acción principal oscura, botón activo |
| `--amber-700` | `0.50 0.11 60` | `#905211` | Enlaces sobre papel |
| `--green-300` / `--green-700` | `0.82 0.12 165` / `0.47 0.10 165` | `#70ddb1` / `#006c4d` | Estado `verified` (oscuro / papel) |
| `--orange-300` / `--orange-700` | `0.80 0.13 60` / `0.50 0.13 50` | `#fba962` / `#9b4805` | Estado `conflict` (oscuro / papel) |

### 2.2 Semánticos

**Capa flotante (HUD), siempre clara sobre la escena:**

```css
--hud-fg: var(--white);
--hud-fg-muted: var(--white);          /* jerarquía por tamaño, nunca por opacidad */
--hud-halo-rgb: 19 14 10;              /* ink-950 */
--hud-rim: rgb(var(--hud-halo-rgb) / 0.85);
--hud-text-halo:                       /* tratamiento medido en §5.5 (variante H6) */
  1px 0 0 var(--hud-rim), -1px 0 0 var(--hud-rim), 0 1px 0 var(--hud-rim), 0 -1px 0 var(--hud-rim),
  1px 1px 0 var(--hud-rim), -1px 1px 0 var(--hud-rim), 1px -1px 0 var(--hud-rim), -1px -1px 0 var(--hud-rim),
  0 0 1px rgb(var(--hud-halo-rgb) / 0.9), 0 0 2px rgb(var(--hud-halo-rgb) / 0.9),
  0 0 3px rgb(var(--hud-halo-rgb) / 0.7), 0 1px 8px rgb(var(--hud-halo-rgb) / 0.4),
  0 0 16px rgb(var(--hud-halo-rgb) / 0.25);
--hud-icon-casing-width: 5.5px;        /* trazo oscuro bajo el trazo blanco de 2 px: 1,75 px por lado */
--hud-icon-halo: drop-shadow(0 0 4px rgb(var(--hud-halo-rgb) / 0.45));
--hud-veil-opacity: 0;                 /* velo: 0,55 con Contraste alto */
--hud-disc-bg: rgb(var(--hud-halo-rgb) / 0.45);
--hud-disc-bg-hover: rgb(var(--hud-halo-rgb) / 0.6);
--hud-disc-bg-pressed: rgb(var(--hud-halo-rgb) / 0.72);   /* también fondo de las píldoras */
--hud-disc-ring: rgb(255 255 255 / 0.28);
--hud-disc-active-bg: var(--amber-300);
--hud-disc-active-fg: var(--ink-950);
--focus-ring: 0 0 0 2px var(--amber-300), 0 0 0 4px var(--ink-950);   /* doble anillo */
--route: var(--amber-300);
--route-casing: rgb(var(--hud-halo-rgb) / 0.8);
--you-fill: var(--white);   --you-stroke: var(--ink-950);
--stop-fill: var(--white);  --stop-stroke: var(--ink-950);  --stop-selected: var(--amber-300);
```

**Hojas** (oscuras por defecto; "papel" con `prefers-color-scheme: light` o en Ajustes):

| Token | Oscuro | Papel | Alto contraste |
|---|---|---|---|
| `--sheet-bg` | `ink-900` | `paper-50` | `ink-950` |
| `--sheet-raised` | `ink-800` | `paper-100` | `ink-900` |
| `--sheet-fg` | `ink-100` | `ink-900` | `white` |
| `--sheet-fg-muted` | `ink-300` | `ink-600` | `ink-100` |
| `--sheet-border` (controles) | `ink-500` | `ink-500` | `white` |
| `--sheet-divider` (decorativo) | `ink-700` | `ink-200` | `ink-700` |
| `--sheet-link` | `amber-300` | `amber-700` | `amber-300` |
| `--sheet-primary-bg` / `-fg` | `amber-300` / `ink-950` | `ink-900` / `white` | `amber-300` / `ink-950` |
| `--status-verified` | `green-300` | `green-700` | `green-300` |
| `--status-conflict` | `orange-300` | `orange-700` | `orange-300` |
| `--status-unverified` | `ink-300` | `ink-600` | `ink-100` |
| `--sheet-focus` (contorno 3 px, separación 2 px) | `amber-300` | `ink-900` | `amber-300` |
| `--sheet-scrim` | `ink-950 / 0.35` | igual | igual |

### 2.3 Tipografía

- Familia: `system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans", Ubuntu, sans-serif`. Pesos: 400 y 500. Cifras: `font-variant-numeric: tabular-nums` en hora, altitud, distancias y coordenadas.
- `--ui-scale`: 1 · 1,25 · 1,5 (Ajustes › Tamaño del texto). Multiplica todos los tamaños de texto. Los discos y objetivos no cambian. Se aplica en `html` (no en `body`: las variables derivadas se resuelven donde se declaran).

| Token | Escritorio | Táctil | Uso | Interlineado |
|---|---|---|---|---|
| `--text-hud-2xs` | 12 px | 12 px | "Créditos", la N del minimapa | 1,2 |
| `--text-hud-xs` | 13 px / 500 | 13 px / 500 | Etiquetas de los botones | 1,25 |
| `--text-hud-sm` | 14 px / 400 | 14 px / 400 | "Ahora en Calp", "Toca para saber más ›", unidad de altitud | 1,3 |
| `--text-hud-md` | 16 px / 500 | 15 px / 500 | Hora, cifra de altitud, pistas de primera vez | 1,25 |
| `--text-hud-lg` | 18 px / 500 | 17 px / 500 | Nombre del sitio al llegar, estado de la subida | 1,25 |
| `--text-sheet-xs` | 13 px | 13 px | Insignias de estado, notas | 1,4 |
| `--text-sheet-sm` | 14 px | 14 px | Metadatos, fuentes, teselas | 1,4 |
| `--text-sheet-md` | 16 px | 16 px | Cuerpo de las hojas (mínimo para leer, A27) | 1,45 |
| `--text-sheet-lg` | 19 px / 500 | 19 px / 500 | Subtítulos (parada seleccionada) | 1,2 |
| `--text-sheet-xl` | 24 px / 500 | 22 px / 500 | Título de hoja | 1,2 |

Títulos con `text-wrap: balance`; párrafos con `text-wrap: pretty`; medida máxima de 60–70 caracteres en la ficha de escritorio (ancho 440 px).

### 2.4 Iconos

- Un solo juego: rejilla de 24 × 24, trazo 2 (`--hud-icon-stroke`), extremos y uniones redondeados, `currentColor`. Formas de tipo Lucide; si se usan los de Lucide (ISC), se añade su licencia a `CREDITS.md`.
- Tamaño: 22 px en el HUD (`--hud-icon`), 20–24 px en hojas, 16 px en insignias.
- En la capa flotante cada icono se dibuja dos veces: un **trazo de funda** de 5,5 px en `--hud-rim` y encima el trazo blanco de 2 px (como la ruta del minimapa). Dentro de un disco o píldora no lleva funda: el disco ya es su fondo.
- Correspondencia: Ir a la cima = montaña con bandera · Cuaderno = libro · Más = tres puntos · llegada = chincheta · Mapa = mapa plegado · ¿Dónde estoy? = diana · Hora y tiempo = reloj · Foto = cámara · Ajustes = deslizadores · Ayuda = interrogación · Solo paisaje = ojo tachado · Ver desde = persona · Pausa / Seguir / Parar = dos barras / triángulo / cuadrado · Ir ahora = chincheta con estela · Caminar hasta aquí = persona andando · Volver = flecha atrás · Comprobado / Las fuentes no coinciden / Sin confirmar = círculo con marca / bifurcación / círculo discontinuo con interrogación.

### 2.5 Espacio, radio, elevación

- Rejilla de 4 px: `--space-1…12` = 4, 8, 12, 16, 20, 24, 32, 48.
- Radio: `--radius-sm` 6 · `--radius-md` 12 (teselas, tarjetas, zona de toque de los textos flotantes) · `--radius-lg` 20 (hojas) · `--radius-full` (discos, píldoras).
- Elevación: la capa flotante no tiene sombra de caja, solo el halo. Las hojas, una sola sombra: `0 10px 40px rgb(ink-950 / 0.45)`.
- Bordes de pantalla: `--hud-edge-x` / `--hud-edge-y` = 24/20 px en escritorio y tableta, 16/12 px en teléfono. Siempre `max(borde, env(safe-area-inset-*))`. La meta `viewport-fit=cover` ya está en `index.html`.

### 2.6 Movimiento

| Token | Valor | Uso |
|---|---|---|
| `--dur-press` | 120 ms | Hundir el disco al pulsar |
| `--dur-fade` | 200 ms | Hover, cambio de fondo |
| `--dur-enter` / `--dur-exit` | 280 / 200 ms | Hojas: entrar (desliza 24 px + opacidad) / salir |
| `--dur-notice-in` / `--dur-notice-out` | 400 / 600 ms | Aviso de llegada |
| `--dur-teleport` | 220 ms por mitad | Fundido a negro y desde negro de "Ir ahora" (dentro de 150–300 ms) |
| `--ease-out` | `cubic-bezier(0.2, 0.7, 0.2, 1)` | Entradas |
| `--ease-in` | `cubic-bezier(0.4, 0, 1, 1)` | Salidas |
| `--ease-standard` | `cubic-bezier(0.3, 0, 0.2, 1)` | Cambios de estado |

- Solo se animan `opacity` y `transform`.
- **`prefers-reduced-motion: reduce`** o Ajustes › Movimiento › Tranquilo: sin desplazamientos; las hojas y avisos aparecen con opacidad en 120 ms como máximo; el fundido de "Ir ahora" pasa a corte; el minimapa nunca gira (se fuerza "Norte arriba" y el ajuste lo explica); sin escala al pulsar.

### 2.7 Variantes

- **Contraste alto** (Ajustes): `--hud-veil-opacity: 0.55` (un velo oscuro difuminado, sin borde, detrás de cada grupo flotante: `radial-gradient(closest-side, ink-950 55 %, transparente)`), discos al 82 %, anillo del disco blanco, hojas en `ink-950` con texto blanco y bordes blancos. Ver `p375-contraste-alto.png`.
- **`forced-colors: active`**: los halos desaparecen por diseño del navegador; cada grupo flotante pasa a una caja `Canvas` con texto `CanvasText` y borde `ButtonBorder`, los iconos a `currentColor`, la ruta a `Highlight` y el foco a `Highlight`. Es el único caso en que el HUD tiene cajas.
- **Papel** (`prefers-color-scheme: light` o Ajustes): solo cambian las hojas; la capa flotante es la misma. Ver `*-ficha-clara.png`.

## 3. Componentes y estados

Estados comunes de todo control: **reposo · hover** (solo con `@media (hover: hover)`, nunca necesario) **· foco visible** (`:focus-visible`, doble anillo) **· pulsado · activo/abierto · oculto**. **No hay estado deshabilitado:** lo que no está disponible no se muestra (la tesela "Foto" no aparece hasta la fase X5; el tiempo no aparece sin `weather.json`). Tablero de estados: `d1440-componentes.png`.

Todo texto flotante lleva `--hud-text-halo`; todo icono flotante, la funda y `--hud-icon-halo`. Las zonas de toque son la caja de cada control (`pointer-events: auto` solo en ella); los contenedores llevan `pointer-events: none`, para que el toque llegue al lienzo (joystick y mirar).

### 3.1 Hora y tiempo (arriba a la derecha)

- Anatomía: `[icono del cielo] 22° · 12:40` en `--text-hud-md`, y debajo "Ahora en Calp" en `--text-hud-sm`. Botón de 44 px de alto como mínimo.
- Hora de `Europe/Madrid`, `HH:MM` de 24 h, se actualiza al cambiar el minuto. Icono y temperatura **solo** si hay `weather.json` válido; sin él: `12:40` y nada más.
- En teléfono se oculta "Ahora en Calp". **"Hora elegida"** se ve siempre, en todos los tamaños, en `--amber-200`.
- Al pulsar abre "Hora y tiempo". Hasta X2 esa hoja dice la hora y la frase de §7 sobre la luz de ejemplo (ver pregunta abierta 1).
- Nombre accesible: "Hora y tiempo: 12:40, ahora en Calp, 22 grados".

### 3.2 Minimapa (abajo a la izquierda con puntero fino; arriba a la izquierda en táctil)

| | Escritorio | Tableta | Teléfono |
|---|---|---|---|
| Diámetro (`--minimap-size`) | 168 px | 136 px | 104 px |
| Ventana | 280 × 280 m centrada en ti (radio 140 m) | igual | igual |

- **Máscara**: `mask-image: radial-gradient(circle closest-side, #000 82%, transparent 100%)`. La ortofoto se atenúa (`saturate(0.85) brightness(0.9)`). Sin borde, sin aro.
- **Ruta**: trazo `--route` de 2,5 px CSS sobre funda `--route-casing` de 5 px, con `vector-effect: non-scaling-stroke` para que no adelgace en el minimapa de 104 px. Es un solo color; no se distingue por color ningún tramo.
- **Tú**: flecha blanca de 14 px (12 px en táctil) con contorno `ink-950` de 1,5 px, en el centro, girada con tu rumbo.
- **Paradas** dentro del círculo: punto blanco de 6 px con contorno `ink-950`.
- **Próxima parada fuera del círculo**: punto blanco y un triángulo hacia fuera, pegados al 82 % del radio en su dirección (`*-autosubida.png`, el túnel).
- **N**: letra de 12 px/500 en lo alto del círculo, con halo.
- **Norte arriba** por defecto. "Gira conmigo" (Ajustes) gira el mapa, deja la flecha hacia arriba y la N recorre el borde. Nunca con movimiento reducido.
- Se actualiza unas 10 veces por segundo (posición y rumbo), con transformaciones CSS sobre una sola imagen: cero llamadas de dibujo nuevas.
- Es un botón: abre el mapa grande. Nombre accesible: "Mapa. Abre el mapa grande". Estados: hover = la flecha y la N a opacidad completa y la imagen sin atenuar; foco = doble anillo circular a 4 px del borde fundido; oculto = solo paisaje.

### 3.3 Altitud (bajo el minimapa)

- Escritorio y tableta: "**75 m** sobre el mar" (cifra `--text-hud-md`/500, unidad `--text-hud-sm`/400). Teléfono: "**75 m**".
- Valor: altura del suelo bajo el jugador en el campo de colisión, redondeada al metro. No es un control.
- Texto accesible: "Altitud: 75 metros sobre el mar". En la cima se ve lo que da el modelo (325 m); la ficha explica los 332 m oficiales (`summit-altitude`).

### 3.4 Aviso de llegada (centro, abajo)

- Anatomía: chincheta de 18 px, nombre del sitio (`--text-hud-lg`) y "Toca para saber más ›" (táctil) o "Pulsa para saber más ›" (puntero o teclado). Es **un botón** de 44 px de alto como mínimo, ancho según su texto, máximo 30 rem. Abre la ficha.
- Tiempos: entra en 400 ms (opacidad y 8 px hacia arriba), se queda **6 s** más 50 ms por carácter del nombre (máximo 9 s), sale en 600 ms. El tiempo se detiene mientras tiene el foco o el puntero encima y mientras hay una hoja abierta (entonces no aparece y espera).
- Cola: uno a la vez, por orden de llegada, como máximo dos en espera y 1 s entre ellos. Si el mismo sitio vuelve a llegar en menos de 60 s, no se repite.
- Historial: cada llegada queda en Más › "Lugares por los que has pasado" (los 20 últimos de la sesión, con la hora). Así el aviso puede irse solo sin que se pierda nada (WCAG 2.2.1).
- Región viva: "Has llegado a {lugar}." (una vez por llegada, por la región única de §5.3).
- Nombre: el título de la ficha en `content/pois/*.json` en el idioma activo; si falta, el castellano con `lang="es"`.

### 3.5 Los tres botones (abajo a la derecha)

- Anatomía: disco de 46 px (escritorio) o 48 px (táctil), fondo `--hud-disc-bg`, anillo interior de 1 px `--hud-disc-ring`, icono de 22 px; debajo la palabra en `--text-hud-xs`/500 con halo. **Todo el conjunto es el botón**, unos 62 × 70 px.
- Orden: **Ir a la cima · Cuaderno · Más**. Separación de 12 px (escritorio) o 6 px (táctil) entre cajas.
- Estados: hover → fondo al 60 %; pulsado → al 72 % y escala 0,94 en 120 ms; foco → doble anillo alrededor del disco; abierto (Más con su hoja) → disco ámbar e icono `ink-950`, `aria-expanded="true"`; oculto → solo paisaje.
- Durante la subida automática "Ir a la cima" desaparece y quedan Cuaderno y Más.
- Las etiquetas no se cortan nunca: si no caben, pasan a dos líneas (máximo 6,5 em de ancho).

### 3.6 Créditos

- Enlace de texto de 12 px, subrayado, con zona de toque de 24 px de alto como mínimo (WCAG 2.5.8). Abre el diálogo de créditos que ya existe (`#credits`).
- Escritorio, tableta y teléfono apaisado: bajo los botones, alineado a la derecha. **Teléfono vertical: bajo la hora**, arriba a la derecha (abajo choca con la fila de botones al 150 % y con la zona del indicador de inicio de iOS).
- Sustituye a la línea de atribución larga de `#attribution`, que pasa al diálogo y al pie del modo foto.

### 3.7 Hoja "Más"

- Contenedor (§4.2): globo anclado sobre el botón en escritorio (380 px), hoja inferior en teléfono vertical y tableta (máximo 600 px), hoja lateral derecha en teléfono apaisado (380 px).
- Contenido, en este orden:
  1. Cabecera: "Más" (h2) y "Cerrar" (icono y palabra, 44 px).
  2. Teselas de 3 columnas, 76 px de alto como mínimo, icono de 24 px y palabra: **Mapa · ¿Dónde estoy? · Hora y tiempo · Foto · Ajustes · Ayuda**. Una tesela sin función aún no se muestra y la rejilla se recoloca.
  3. Filas: **Solo paisaje** (interruptor) y **Ver desde: Mis ojos | Detrás** (selector de dos opciones; sustituye al botón 📷 de `touch.ts` y a la tecla C, que se mantiene).
  4. "Lugares por los que has pasado": el historial de §3.4; cada fila abre su ficha.
  5. Enlaces: Créditos · Accesibilidad (declaración, A38) · La ruta en texto (A1).
- **¿Dónde estoy?**: cierra la hoja y dice, en la región viva y como texto flotante arriba en el centro durante 8 s, "Estás cerca de {lugar}, a {alt} m sobre el mar. Miras al {rumbo}. La próxima parada, {parada}, está a {distancia} por el sendero." {lugar} es el anclaje con nombre más cercano a menos de 30 m; si no hay, "en la Ruta Roja". Con la voz activada en Ajustes, también se lee con la síntesis del navegador.
- **Ajustes** se abre dentro de la misma hoja, con "‹ Más" para volver (`p375-ajustes.png`). Todo se guarda en el dispositivo:
  - Idioma: Español | Valencià | English (cada nombre en su idioma y con su `lang`);
  - Tamaño del texto: A | A+ | A++;
  - Contraste: Normal | Alto;
  - Movimiento: Normal | Tranquilo (se marca solo con `prefers-reduced-motion`);
  - Velocidad al caminar: Real | Más despacio (0,75×). Nunca más rápido;
  - Mapa pequeño: Norte arriba | Gira conmigo;
  - Sonido: sí/no (llega con L2);
  - Calidad de imagen: Auto | Baja | Media | Alta.
- **Ayuda** muestra las pistas de primera vez (§3.12) en grande y, en un apartado "Con teclado", la tabla de §5.4.
- Selectores: `role="radiogroup"` con flechas; interruptores: `role="switch"`. 44 px de alto, opción activa en `--sheet-primary-bg`.

### 3.8 Ficha de un punto de interés

- Contenedor: lateral derecho de 440 px en escritorio (420 px en teléfono apaisado); hoja inferior del 86 % de alto en teléfono y del 78 % en tableta.
- Cabecera: título (h2, `--text-sheet-xl`), y debajo "Ruta Roja · {alt} m sobre el mar". "Cerrar" a la derecha **recibe el foco al abrir**.
- Cuerpo, desde `content/pois/{id}.json`:
  1. Cada elemento de `summary` es un párrafo seguido de su línea de datos: **insignia de estado** y "Fuentes ({n}) ›".
  2. Insignia: icono + palabra, contorno de 1,5 px en el color de estado y texto del mismo color. Si el elemento cita varios hechos, manda el peor: `conflict` > `unverified` > `verified`.
  3. "Fuentes" es un botón con `aria-expanded`. Abre una lista: título de la fuente, editor, "consultada el {accessed}" y "Abrir la web ↗" (pestaña nueva, "(web externa)" para el lector). En un hecho `conflict` se listan **todos los valores**, cada uno con sus fuentes y su nota (p. ej. 332 m GVA · 325,8 m ICV CV05 · 328,07 m LiDAR).
  4. `expand` son apartados plegables (h3 dentro de un botón, 52 px, flecha a la derecha), cerrados al abrir.
  5. El bloque `notice` va al final, con borde, nunca escondido.
  6. Idioma: si falta la traducción (`translations.va.status = "missing"`), arriba aparece "Aquesta fitxa encara no està en valencià. Te la mostrem en castellà." y el cuerpo lleva `lang="es"`.
- `Esc`, "Cerrar" o tocar el velo cierran la ficha; el foco vuelve al aviso si sigue visible y, si no, a "Más".

### 3.9 Cuaderno de campo

- Mismo contenedor que la ficha. Cabecera "Cuaderno de campo" y "{n} de {m} sellos". {m} es el número de puntos de interés del registro con sello, no las 9 paradas oficiales.
- Rejilla de sellos (columnas de 104 px como mínimo): disco de 76 px.
  - **Conseguido**: disco ámbar con el icono del sitio en `ink-950`, doble aro, nombre y fecha (`dd/mm/aaaa`, de `notebook.ts`).
  - **Pendiente**: disco con aro de `--sheet-border` y fondo rayado, icono de sello, nombre y "Aún no".
- Cada sello conseguido abre su ficha. Lista semántica (`ul`), cada sello es un botón con nombre "Centro de Visitantes, conseguido el 12 de octubre de 2026".
- El prototipo rellena los huecos con los anclajes del mapa a modo de ilustración; en la app solo habrá huecos para las fichas que existan.

### 3.10 Mapa grande y viaje rápido

- Contenedor: diálogo centrado de 1240 × 820 px en escritorio, con velo; pantalla completa en táctil.
- **Mapa**: ortofoto ICV 2024 (la misma imagen de X1.1), encuadrada en la caja de la ruta con 76 px de margen para los rótulos. Ruta de 4 px sobre funda de 8 px. Paradas: punto blanco de 7 px con contorno de 3 px; la **seleccionada**, ámbar de 10 px y rótulo en `--amber-200`. Rótulos con halo, a un lado fijo por parada (§9, `LABEL_SIDE`). Además: "Tú" con la flecha, N, barra de escala de 100 m y la atribución "Ortofoto 2024 © ICV (CC BY 4.0) · Ruta © OpenStreetMap (ODbL)" dentro del mapa.
- **Paradas** (anclajes de `trail.json` sobre la ruta): Centro de Visitantes, Mirador (OSM 1795591637), Mirador (3635481356), Túnel, Mirador (3635481353, salida del túnel), Bifurcación, Mirador de Carabiners, Cima. Las que no tienen nombre confirmado se llaman "Mirador" (X1.3). `viewpoint-288472097` queda a 7 m de la ruta y no se muestra hasta confirmarlo.
- **Tarjeta de la parada seleccionada**:
  - título (`--text-sheet-lg`);
  - "325 m sobre el mar · a 1,7 km por el sendero, unos 20 min a paso real", con distancia sobre la ruta y tiempo a 1,4 m/s sin paradas, rotulados como cálculo del modelo y nunca como cifra oficial (`trail-length` y `trail-time` están en `conflict`);
  - **"Ir ahora"** (principal, recibe el foco) y **"Caminar hasta aquí"**, de 48 px. En teléfono van una encima de otra a todo el ancho.
- **GPS simulado**: etiqueta con borde "GPS simulado" y "38,63741° N · 0,07382° E": las coordenadas reales del punto del modelo donde estás, con 5 decimales.
- **Perfil de altitud**: SVG de 96 px de alto, área en `--sheet-raised`, línea de 1,5 px, una marca por parada (la seleccionada en ámbar), "tú" como punto ámbar de 6 px, ejes "0 km", "1,8 km", "70 m" y "325 m". Recorrido de la ruta principal: acceso → escalera → túnel → bifurcación → cima, 1.753 m en planta.
- **Lista de paradas** (`ol`, en escritorio a la vista; en táctil bajo el perfil): nombre y altitud. Es la vía accesible para elegir parada y la misma lista de la guía en texto.
- **"Ir ahora"**:
  1. cierra el mapa;
  2. funde a `ink-950` en 220 ms;
  3. llama a `teleport(anclaje, rumbo)` y pide las teselas del destino;
  4. si a los 220 ms no están, deja el negro con "Cargando…" en el centro y nunca enseña terreno vacío;
  5. funde desde negro en 220 ms, mirando la vista de la parada (`arrivalYaw`);
  6. durante 1 s no hay movimiento;
  7. anuncia "Has llegado a {lugar}. Miras al {rumbo}.";
  8. muestra la píldora **"Volver"** abajo en el centro hasta que camines 10 m o abras algo. "Volver" hace el mismo fundido a la posición anterior.
  Con movimiento reducido, corte seco.
- **"Caminar hasta aquí"**: cierra el mapa e inicia la subida automática hacia esa parada (§3.11), con el texto "Caminando hasta {lugar}".

### 3.11 Subida automática (Pausa / Parar)

- Se inicia con "Ir a la cima", con "Caminar hasta aquí" o con la tecla P.
- Abajo en el centro (sobre la fila de botones en teléfono vertical):
  - estado: "**Subiendo a la cima**" (`--text-hud-lg`) y "a paso real · faltan 1,2 km" (`--text-hud-sm`), con la distancia restante sobre la ruta, actualizada cada 10 m;
  - dos píldoras de 48 px con icono y palabra: **Pausa** (pasa a **Seguir**) y **Parar**.
- El foco va a "Pausa" al empezar, porque el botón que se pulsó desaparece. Al parar o llegar, el foco vuelve a "Ir a la cima".
- Tocar el joystick o pulsar una tecla de movimiento **pausa** la subida (no la cancela) y muestra "Seguir". Un niño que toca sin querer no pierde la subida.
- Avisos: "Subiendo a la cima", "En pausa", "Subida parada", y al llegar el aviso de llegada de la cima.
- El minimapa y la altitud siguen visibles; las pistas de primera vez no.

### 3.12 Pistas de primera vez

- **Táctil**:
  - "Arrastra para caminar": aro de 96 px con una mano en la zona del pulgar izquierdo;
  - "Arrastra para mirar": aro de 72 px con un ojo, a la derecha.
  En teléfono apaisado solo cabe la primera; la segunda aparece después del primer paseo y dura 4 s o hasta que mires.
- **Escritorio**: dibujo de las cuatro teclas de flecha (96 × 66 px) con "Usa las flechas para caminar" y un ratón con "Arrastra con el ratón para mirar". Con el paseo tocando el camino (B10), la primera pasa a "Usa las flechas o toca el camino". Nunca una lista de teclas.
- No reciben toques (`pointer-events: none`). Se van con el primer movimiento de 2 m o la primera mirada, sin límite de tiempo. Se guarda en el dispositivo que ya se vieron; Ayuda las vuelve a mostrar.
- Sustituyen a `hintKeyboard` y `hintTouch`.

### 3.13 Aviso de sendero y solo paisaje

- **Aviso de sendero** (`corridorNotice`, ya existe): texto flotante arriba en el centro, `--text-hud-sm`, con los tiempos de `notices.ts`. Pierde su caja negra actual.
- **Solo paisaje**: lo oculta todo salvo una píldora **"Mostrar"** (icono de ojo), abajo a la derecha (`p375-solo-paisaje.png`). `Esc` también vuelve. Las llegadas no se muestran y van al historial y a la región viva. Aviso: "Solo paisaje. Para volver, pulsa Mostrar."

## 4. Disposición

Medidas en px CSS. "sa*" = `env(safe-area-inset-*)`; el prototipo usa 47/34 (vertical) y 47/21 (apaisado), como un iPhone con isla.

### 4.1 Pantalla de juego

| Elemento | 375 × 812 vertical (táctil) | 812 × 375 apaisado (táctil) | 768 × 1024 (táctil) | 1440 × 900 (puntero) |
|---|---|---|---|---|
| Minimapa + altitud | Arriba izq. (16, sat + 12), 104 | Arriba izq. (max(16, sal), 12), 104 | Arriba izq. (24, sat + 20), 136 | **Abajo izq.** (24, abajo 20), 168 |
| Hora y tiempo | Arriba der., sin subtexto | Arriba der., sin subtexto | Arriba der., con "Ahora en Calp" | Arriba der., con "Ahora en Calp" |
| Créditos | **Bajo la hora** | Bajo los botones | Bajo los botones | Bajo los botones |
| Aviso de llegada | Centrado, abajo sab + 300 | Centrado, abajo 112 | Centrado, abajo sab + 170 | Centrado, abajo 124 |
| Tres botones | Fila abajo der., abajo sab + 14 | Fila abajo der., abajo sab + 22 | Fila abajo der., abajo sab + 28 | Fila abajo der., abajo 40 |
| Pistas | Caminar abajo izq. y mirar abajo der., a sab + 120 | Solo caminar, abajo izq. | Caminar abajo izq., mirar a la der. sobre los botones | Centradas, abajo 230 |
| Subida automática | Centrada sobre la fila, sab + 104 | Centrada abajo, sab + 14 | Centrada, sab + 120 | Centrada abajo, 40 |

Capturas: `{p375,l812,t768,d1440}-default.png` y `-autosubida.png`.

### 4.2 Hojas

| Hoja | 375 vertical | 812 apaisado | 768 tableta | 1440 escritorio |
|---|---|---|---|---|
| Más | Inferior, altura según contenido | Lateral derecha, 380 | Inferior, 600 centrada | Globo sobre "Más", 380, abajo 130 |
| Ficha / Cuaderno | Inferior, 86 % | Lateral, 420 | Inferior, 600, 78 % | Lateral, 440 |
| Mapa | Pantalla completa: mapa de 400 px de alto, tarjeta, GPS, perfil y lista (con desplazamiento) | Pantalla completa: mapa a la izquierda (alto completo), tarjeta, GPS y perfil a la derecha | Pantalla completa: mapa de 560 px y debajo el resto | Diálogo de 1240 × 820: mapa de 720 × 720 a la izquierda, columna de 440 a la derecha |

Toda hoja es un `<dialog>` modal (`showModal()`): atrapa el foco, `Esc` cierra, el fondo queda inerte y el velo es `--sheet-scrim`. Mientras hay una hoja abierta no se camina. Las inferiores llevan un asa dibujada solo como pista visual: cerrar no depende de arrastrar (WCAG 2.5.7), siempre hay "Cerrar".

### 4.3 Choques con el joystick y la zona de mirar (táctil)

1. El joystick es flotante en la mitad izquierda del lienzo (`touch.ts`). Un toque que empieza sobre un control del DOM nunca crea joystick. Por eso ningún control puede quedar en la **zona del pulgar**: un cuadrado de 200 × 200 px abajo a la izquierda, por encima de `sab` (`--thumb-zone`). Solo las pistas, que no reciben toques, pueden estar ahí.
2. El aviso de llegada es un botón en la mitad izquierda del centro. Su zona de toque es solo su caja (como mucho unos 260 × 70 px) y nunca entra en la zona del pulgar. En vertical va por encima de ella (sab + 300).
3. La fila de botones ocupa la esquina inferior derecha, donde también se apoya el pulgar derecho para mirar. Mirar empieza en cualquier otro punto de la mitad derecha. Separación mínima de 6 px entre cajas de botón.
4. El minimapa arriba a la izquierda queda fuera del alcance natural del pulgar.
5. El botón de cámara de 56 px de `touch.ts` desaparece (pasa a Más › Ver desde). Esa esquina es ahora de "Más".
6. Ningún control dentro de la zona del indicador de inicio de iOS (`sab`) ni de la isla (`sat`).

### 4.4 Qué se pliega

- **Teléfono** (lado corto < 600 px): sin "Ahora en Calp" (salvo "Hora elegida"), altitud sin "sobre el mar", minimapa de 104 px, Créditos bajo la hora en vertical.
- **Alto < 420 px** (apaisado): hojas laterales; el mapa se pone al lado de su columna; la pista de mirar va después de la de caminar.
- **Texto al 125–150 %**: etiquetas en dos líneas antes que cortarse; el aviso se ensancha hasta `100vw − 32 px`; las pistas se parten en dos líneas (`max-width: min(11em, 42vw)`). Ver `p375-texto-150.png`.
- **Ventana de escritorio estrecha** (< 700 px de ancho con puntero fino): disposición de teléfono, pero con el minimapa abajo a la izquierda y sin zona del pulgar.
- **320 px de ancho** (reflujo, WCAG 1.4.10): la fila de tres botones mide unos 240 px y cabe; las hojas son de ancho completo.
- Qué disposición se usa lo decide el tipo de entrada (`pointer: coarse` o el primer toque visto) y no solo el ancho. Atributo `data-input` en `html`, como en el prototipo.

## 5. Accesibilidad

### 5.1 Estructura y roles

```html
<h1 class="visually-hidden">Penyal d'Ifac 3D</h1>
<main>
  <canvas id="scene" tabindex="0" role="img" aria-label="Vista 3D del Penyal d'Ifac" aria-describedby="scene-help"></canvas>
  <p id="scene-help" class="visually-hidden">Usa las flechas para caminar. Abre «Más» para el mapa, la ayuda y la ruta en texto.</p>
  <button class="notice">…</button>                 <!-- solo cuando hay aviso -->
  <section class="autowalk" aria-label="Subida automática">…</section>  <!-- solo durante la subida -->
  <nav aria-label="Acciones">Ir a la cima · Cuaderno · Más</nav>
  <aside aria-label="Orientación">minimapa (botón) · altitud · hora (botón)</aside>
</main>
<footer>Créditos</footer>
<div id="status" role="status" aria-live="polite" class="visually-hidden"></div>
<dialog>…</dialog>  <!-- Más, Ficha, Cuaderno, Mapa, Créditos -->
```

- Un `h1` oculto; cada hoja con su `h2` y `aria-labelledby`.
- Insignias de estado con texto (nunca solo color).
- El perfil de altitud es un SVG `role="img"` con resumen ("de 70 m en el Centro a 325 m en la cima, en 1,8 km; estás a 75 m"). El mapa grande, `role="img"` con resumen, y las paradas como botones en el orden de la lista.

### 5.2 Orden del foco

1. El lienzo, que recibe el foco al cargar: las flechas caminan sin más.
2. El aviso de llegada, si lo hay.
3. Pausa y Parar, si hay subida.
4. Ir a la cima, Cuaderno, Más.
5. Mapa (minimapa), Hora y tiempo.
6. Créditos.

El orden del DOM es este; la posición en pantalla la da el CSS. En las hojas: Cerrar, contenido, controles. Al cerrar, el foco vuelve a quien abrió; si ya no existe (aviso desaparecido, "Ir a la cima" durante la subida), va a "Más" o a "Pausa". El foco nunca queda tapado por una hoja (2.4.11): las hojas son modales.

### 5.3 Región viva única (`#status`, cortés)

- Mensajes: llegada a un sitio, llegada del viaje rápido (con el rumbo), subida (empieza, pausa, sigue, para, llega), "¿Dónde estoy?", aviso de sendero, solo paisaje, cambio de idioma.
- Como mucho un mensaje cada 2 s; los repetidos en 20 s se descartan (`CorridorNotice` ya lo hace con el de sendero).
- El aviso visual y el mensaje hablado tienen textos distintos, para no leer dos veces lo mismo: el botón se llama "Centro de Visitantes: abrir la ficha".
- Desactivable en Ajustes si molesta con lector de pantalla (A6).

### 5.4 Teclado (alternativa, nunca necesaria)

| Tecla | Acción | Estado |
|---|---|---|
| W / ↑, S / ↓ | Adelante / atrás | Existe |
| A / Q, D / E | De lado | Existe |
| ← / → | Girar | Existe |
| Mayús | Correr | Existe; **no se anuncia** en pistas ni en ayuda para niños (el paso es 1,4 m/s) |
| C | Cambiar la vista | Existe; también en Más › Ver desde |
| F | Abrir la ficha del último aviso | Existe (`interact`) |
| P | Subida automática: empieza / pausa / sigue | Existe |
| M | Abrir el mapa grande | Nuevo |
| Esc | Cerrar la hoja; salir de solo paisaje | Nuevo |
| Tab / Mayús+Tab, Intro / Espacio, flechas en selectores y en la lista de paradas | Navegación estándar | Nuevo |

Las teclas de una sola letra (C, F, P, M, y WASD/QE) solo deben actuar con el foco en el lienzo o en el `body` (excepción de WCAG 2.1.4). Hoy `keyboard.ts:44` escucha en `window`, y solo se calla cuando hay un diálogo abierto o el foco está en un campo editable. Con el foco en un botón del HUD, la P también arrancaría la subida. Hay que añadir esa condición en X0.2.

### 5.5 Contraste del texto flotante sobre los peores fondos reales

**Método** (scripts en `x01/measure*.{mjs,py}`):

1. Diez capturas nuevas del juego (`turnstile`, `viewpoint-3635481356` y `summit`, a 375, 812, 768 y 1440 px).
2. En cada una, la ventana de 260 × 56 px CSS **más clara** del cielo (45 % superior) y del suelo (55 % inferior). Las peores: neblina del horizonte y camino claro, con L ≈ 0,65 (`#bcd6ea` como p99).
3. Sobre esos recortes se pintan las muestras del HUD a DPR 1 y 2 en tres pasadas: máscara de color, fondo solo y resultado.
4. Se mide la luminancia del relleno del glifo frente a:
   - **M1**: la banda de 1 px pegada al glifo, el halo tomado como fondo (Understanding 1.4.3: un halo ancho es fondo);
   - **M2**: el reborde frente a la escena a 2–4 px, el reborde tomado como parte de la letra (un borde estrecho es letra).
5. Siempre se toma el 5 % más claro y el peor de los diez recortes.

Blanco sin tratamiento sobre el peor fondo: **1,51:1**.

| Muestra | Sin nada | Sombra del boceto (H1) M1 | **Token final (H6)** M1 / M2 | Contraste alto (H6 + velo) M1 |
|---|---|---|---|---|
| Nombre al llegar, 17/500 | 1,51 | 1,79 | **7,78 / 7,85** | 9,26 |
| Subtexto, 14/400 | 1,51 | 1,75 | **5,29 / 7,73** | 6,67 |
| Etiqueta de botón, 13/500 | 1,51 | 1,75 | **5,01 / 6,19** | 6,04 |
| Créditos, 12/400 | 1,51 | 1,77 | **10,66 / 6,73** | 10,75 |
| Hora, 15/500 | 1,51 | 1,76 | **8,66 / 8,28** | 9,20 |
| Icono 22 px, trazo 2 (umbral 3:1) | 1,51 | 1,71 | **10,66 / 5,58** | 10,84 |

**Decisión.** La sombra suave del boceto (H1) y un halo difuminado más denso (H2, 2,6–4,3:1) **no llegan**. Una sombra con desenfoque se diluye en trazos de 1,5 px. También fallaron un trazo con `paint-order` de 2,5 px (H4) y un reborde de 1 px sin halo (H5): 1,9–3,8:1 en algún caso. Pasa **H6**: ocho desplazamientos de 1 px sin desenfoque en `ink-950` al 85 % (un reborde fino y denso), más un halo de 1–3 px y un brillo ancho para despegar el texto. Los iconos llevan una funda de 5,5 px. Solo usa `text-shadow`, así que funciona igual en todos los navegadores. Visualmente sigue siendo "texto con sombra suave", con un filo oscuro apenas visible sobre fondos claros (`d1440-componentes.png`).

**Piezas planas** (cálculo con el píxel p99 del peor recorte, `#bcd6ea`):

| Par | Contraste | Umbral |
|---|---|---|
| Icono blanco en disco `ink-950/0.45` | 4,28 | 3 (icono) |
| Texto blanco en píldora `ink-950/0.72` | 9,53 | 4,5 |
| "Hora elegida" `amber-200` sobre su reborde | 10,32 | 4,5 |
| Foco: anillo `ink-950` exterior / escena clara | 12,74 | 3 |
| Foco: anillo `amber-300` / escena oscura (`#14161a`) | 11,37 | 3 |
| Ruta `amber-300` / funda | 8,40 | 3 |
| Funda de la ruta / ortofoto más clara (p99, atenuada) | 6,23 | 3 |
| Ruta sin funda / ortofoto clara | 1,35 | **falla: por eso la funda es obligatoria** |
| Parada blanca / ortofoto más oscura | 17,09 | 3 |

**Hojas** (pares semánticos, con `colors.py`):

| Par | Oscura | Papel |
|---|---|---|
| Cuerpo / fondo | 14,38 | 16,46 |
| Secundario / fondo | 8,23 | 6,61 |
| Secundario / elevada | 6,77 | 6,06 |
| Enlace / fondo | 11,13 | 5,73 |
| Enlace / elevada | 9,16 | 5,26 |
| `verified` / fondo | 10,70 | 5,99 |
| `conflict` / fondo | 9,25 | 5,87 |
| `unverified` / fondo | 8,23 | 6,61 |
| Texto del botón principal | 12,04 | 17,73 |
| Borde de control / fondo (3:1) | 3,63 | 4,53 (con `ink-400` daba 2,90; se cambió a `ink-500`) |
| Alto contraste: blanco / `ink-950` | 19,18 | — |

### 5.6 Tamaños de toque

- Controles principales de 44 px como mínimo: discos de 46–48 px con su etiqueta (unos 62 × 70), píldoras y botones de hoja de 48, "Cerrar" de 44, teselas de 76, filas de 48, segmentos de 38 × 44 en un grupo de 44 de alto.
- Enlaces de texto (Créditos, Abrir la web) de 24 px de alto como mínimo (2.5.8) y separados.
- Nada exige arrastrar (2.5.7): el joystick tiene "Ir a la cima", "Caminar hasta aquí" y el teclado; las hojas se cierran con un botón.

## 6. Textos (es · va · en)

Claves para `app/src/ui/strings.ts`. Frases cortas y en segunda persona, para niños. **(revisar)** = valenciano o inglés en el que no estoy seguro; debe revisarlo un hablante, junto con la revisión ya prevista de `strings.ts`. Los nombres de lugar no son traducciones: salen de `content/` en el idioma que haya (en valenciano, "Centre d'Informació i de Visitants" según `centre-name`; en inglés no hay nombre oficial y se usa el castellano con `lang`).

| Clave | es | va | en |
|---|---|---|---|
| `clockNow` | Ahora en Calp | Ara a Calp | Now in Calp |
| `clockChosen` | Hora elegida | Hora triada **(revisar: o "escollida")** | Chosen time |
| `clockLabel` | Hora y tiempo: {hora}, {ahora/elegida}, {t} grados | Hora i temps: {hora}, {ara/triada}, {t} graus | Time and weather: {time}, {now/chosen}, {t} degrees |
| `skyExample` | La luz del cielo todavía es de ejemplo: no sigue la hora real. | La llum del cel encara és d'exemple: no segueix l'hora real. | The light in the sky is still an example: it does not follow the real time yet. |
| `weatherUpdated` | Actualizado a las {hh:mm} | Actualitzat a les {hh:mm} | Updated at {hh:mm} |
| `altitude` | {n} m sobre el mar | {n} m sobre el mar **(revisar: "sobre la mar")** | {n} m above sea level |
| `altitudeLabel` | Altitud: {n} metros sobre el mar | Altitud: {n} metres sobre el nivell del mar | Altitude: {n} metres above sea level |
| `minimapLabel` | Mapa. Abre el mapa grande | Mapa. Obri el mapa gran | Map. Opens the big map |
| `btnSummit` | Ir a la cima | Puja al cim | Go to the top |
| `btnNotebook` | Cuaderno | Quadern | Notebook |
| `btnMore` | Más | Més | More |
| `creditsButton` | Créditos | Crèdits | Credits |
| `arrivalTap` | Toca para saber más › | Toca per a saber-ne més › | Tap to learn more › |
| `arrivalPress` | Pulsa para saber más › | Prem per a saber-ne més › | Click to learn more › |
| `arrivalButton` | {lugar}: abrir la ficha | {lloc}: obri la fitxa | {place}: open the card |
| `arrivalLive` | Has llegado a {lugar}. | Has arribat a {lloc}. | You have reached {place}. |
| `hintWalkTouch` | Arrastra para caminar | Arrossega per a caminar | Drag to walk |
| `hintLookTouch` | Arrastra para mirar | Arrossega per a mirar | Drag to look around |
| `hintWalkKeys` | Usa las flechas para caminar | Usa les fletxes per a caminar | Use the arrow keys to walk |
| `hintWalkKeysTap` (B10) | Usa las flechas o toca el camino | Usa les fletxes o toca el camí | Use the arrow keys or tap the path |
| `hintLookMouse` | Arrastra con el ratón para mirar | Arrossega amb el ratolí per a mirar | Drag with the mouse to look around |
| `autoSummit` | Subiendo a la cima | Pujant al cim | Walking to the top |
| `autoTo` | Caminando hasta {lugar} | Caminant fins a {lloc} | Walking to {place} |
| `autoPace` | a paso real · faltan {d} | a pas real · falten {d} **(revisar)** | at real walking pace · {d} to go |
| `autoPause` / `autoResume` / `autoStop` | Pausa / Seguir / Parar | Pausa / Continua / Para **(revisar: "Atura")** | Pause / Go on / Stop |
| `autoPausedLive` / `autoStoppedLive` | En pausa. / Subida parada. | En pausa. / Pujada aturada. | Paused. / Walk stopped. |
| `close` | Cerrar | Tanca | Close |
| `moreTitle` | Más | Més | More |
| `tileMap` | Mapa | Mapa | Map |
| `tileWhere` | ¿Dónde estoy? | On estic? **(revisar: "On soc?")** | Where am I? |
| `tileTime` | Hora y tiempo | Hora i temps | Time and weather |
| `tilePhoto` | Foto | Foto | Photo |
| `tileSettings` | Ajustes | Ajustos **(revisar: o "Configuració")** | Settings |
| `tileHelp` | Ayuda | Ajuda | Help |
| `landscapeOnly` | Solo paisaje | Només paisatge | Just the view |
| `landscapeShow` | Mostrar | Mostra | Show |
| `landscapeLive` | Solo paisaje. Para volver, pulsa Mostrar. | Només paisatge. Per a tornar, prem Mostra. | Just the view. To go back, press Show. |
| `viewFrom` / `viewEyes` / `viewBehind` | Ver desde / Mis ojos / Detrás | Veure des de / Els meus ulls / Darrere | View from / My eyes / Behind |
| `history` | Lugares por los que has pasado | Llocs per on has passat | Places you have been |
| `accessibility` | Accesibilidad | Accessibilitat | Accessibility |
| `textRoute` | La ruta en texto | La ruta en text | The route as text |
| `whereAmI` | Estás cerca de {lugar}, a {alt} m sobre el mar. Miras {rumbo}. La próxima parada, {parada}, está a {d} por el sendero. | Estàs prop de {lloc}, a {alt} m sobre el mar. Mires {rumb}. La pròxima parada, {parada}, és a {d} pel sender. **(revisar: "està a")** | You are near {place}, {alt} m above sea level. You are facing {dir}. The next stop, {stop}, is {d} along the trail. |
| `onTheTrail` | en la Ruta Roja | a la Ruta Roja | on the Ruta Roja |
| `dir.*` (frases enteras, por la elisión) | al norte · al noreste · al este · al sureste · al sur · al suroeste · al oeste · al noroeste | cap al nord · cap al nord-est · cap a l'est · cap al sud-est · cap al sud · cap al sud-oest · cap a l'oest · cap al nord-oest | north · north-east · east · south-east · south · south-west · west · north-west |
| `settings` | Ajustes | Ajustos | Settings |
| `setLanguage` | Idioma | Idioma | Language |
| `setTextSize` | Tamaño del texto | Mida del text **(revisar: "Grandària")** | Text size |
| `setContrast` | Contraste: Normal / Alto | Contrast: Normal / Alt | Contrast: Normal / High |
| `setMotion` | Movimiento: Normal / Tranquilo | Moviment: Normal / Tranquil | Motion: Normal / Calm |
| `setMotionNote` | Tranquilo: sin fundidos ni giros del mapa | Tranquil: sense fosos ni girs del mapa **(revisar)** | Calm: no fades and no map turning |
| `setSpeed` | Velocidad al caminar: Real / Más despacio | Velocitat en caminar: Real / Més a poc a poc **(revisar)** | Walking speed: Real / Slower |
| `setSpeedNote` | Real: 1,4 m/s, como una persona paseando | Real: 1,4 m/s, com una persona passejant | Real: 1.4 m/s, like a person out for a walk |
| `setMinimap` | Mapa pequeño: Norte arriba / Gira conmigo | Mapa xicotet: El nord amunt / Gira amb mi | Small map: North up / Turns with me |
| `setSound` | Sonido | So | Sound |
| `setQuality` | Calidad de imagen: Auto / Baja / Media / Alta | Qualitat de la imatge: Automàtica / Baixa / Mitjana / Alta | Image quality: Auto / Low / Medium / High |
| `statusVerified` | Comprobado | Comprovat | Checked |
| `statusConflict` | Las fuentes no coinciden | Les fonts no coincideixen | Sources disagree |
| `statusUnverified` | Sin confirmar | Sense confirmar | Not confirmed |
| `sources` | Fuentes ({n}) | Fonts ({n}) | Sources ({n}) |
| `sourceChecked` | consultada el {fecha} | consultada el {data} | checked on {date} |
| `sourceOpen` | Abrir la web | Obri el web | Open the website |
| `externalSite` | (web externa) | (web externa) **(revisar: "lloc web extern")** | (external website) |
| `cardMissingVa` | Esta ficha aún no está en valenciano. Te la mostramos en castellano. | Aquesta fitxa encara no està en valencià. Te la mostrem en castellà. | — |
| `cardMissingEn` | — | — | This card is not in English yet. It is shown in Spanish. |
| `cardSub` | Ruta Roja · {alt} m sobre el mar | Ruta Roja · {alt} m sobre el mar | Ruta Roja · {alt} m above sea level |
| `notebookTitle` | Cuaderno de campo | Quadern de camp | Field notebook |
| `notebookCount` | {n} de {m} sellos | {n} de {m} segells | {n} of {m} stamps |
| `notebookNotYet` | Aún no | Encara no | Not yet |
| `notebookEmpty` | Cuando llegues a un sitio, aquí aparecerá su sello. | Quan arribes a un lloc, ací apareixerà el seu segell. | When you reach a place, its stamp will appear here. |
| `mapTitle` | Mapa de la Ruta Roja | Mapa de la Ruta Roja | Map of the Ruta Roja |
| `mapYou` | Tú | Tu | You |
| `mapGps` | GPS simulado | GPS simulat | Simulated GPS |
| `mapGo` | Ir ahora | Vés-hi ara **(revisar)** | Go now |
| `mapWalk` | Caminar hasta aquí | Camina fins ací | Walk here |
| `mapBack` | Volver | Torna | Go back |
| `mapStopLine` | {alt} m sobre el mar · a {d} por el sendero, unos {min} min a paso real | {alt} m sobre el mar · a {d} pel sender, uns {min} min a pas real | {alt} m above sea level · {d} along the trail, about {min} min at real pace |
| `mapProfile` | Perfil de altitud | Perfil d'altitud | Elevation profile |
| `mapAttribution` | Ortofoto 2024 © ICV (CC BY 4.0) · Ruta © OpenStreetMap (ODbL) | Ortofoto 2024 © ICV (CC BY 4.0) · Ruta © OpenStreetMap (ODbL) | Orthophoto 2024 © ICV (CC BY 4.0) · Route © OpenStreetMap (ODbL) |
| `stopViewpoint` (sin nombre) | Mirador | Mirador | Viewpoint |
| `stopTunnel` / `stopFork` / `stopSummit` | Túnel / Bifurcación / Cima | Túnel / Bifurcació / Cim | Tunnel / Fork / Summit |
| `teleportLoading` | Cargando… | Carregant… | Loading… |
| `teleportLive` | Has llegado a {lugar}. Miras {rumbo}. | Has arribat a {lloc}. Mires {rumb}. | You are at {place}. You are facing {dir}. |
| `sceneHelp` | Usa las flechas para caminar. Abre «Más» para el mapa, la ayuda y la ruta en texto. | Usa les fletxes per a caminar. Obri «Més» per al mapa, l'ajuda i la ruta en text. | Use the arrow keys to walk. Open "More" for the map, help and the route as text. |
| `viewToggle` (sustituye a `CAMERA_BUTTON_LABEL`) | Cambiar la vista | Canvia la vista | Change the view |

Sustituidas: `hintKeyboard` y `hintTouch` (listas de teclas), y la constante `CAMERA_BUTTON_LABEL` de `touch.ts`, que está fija en castellano. `attributionLine` se mantiene para el diálogo de créditos y el pie del modo foto.

## 7. Lo que la implementación NO debe hacer

1. Cajas o paneles fijos en la pantalla de juego (salvo `forced-colors`). Nada de tarjetas translúcidas detrás de la hora o los botones.
2. `backdrop-filter` sobre el lienzo WebGL: obliga a recomponer cada fotograma en un móvil medio. Las hojas son opacas.
3. Bajar el contraste con `opacity` o grises en el texto flotante (el boceto usaba 0,75–0,92). Jerarquía por tamaño y peso.
4. Quitar o "suavizar" el reborde H6 sin volver a medir (§5.5). La sombra del boceto da 1,8:1.
5. Controles solo con icono, solo con palabra, o con emoji (el 📷 actual).
6. Cualquier función que solo exista en una tecla, en un gesto (deslizar, pellizcar, mantener) o en el hover. Tampoco el asa de las hojas como único modo de cerrar.
7. Listas de teclas en las pistas o en pantalla. El teclado se documenta solo en Ayuda › Con teclado.
8. Controles deshabilitados en gris: lo que no está, no se muestra. Y nada de "próximamente".
9. Cifras sin método o presentadas como oficiales: distancia y tiempo son "por el sendero, a paso real" (cálculo del modelo); la altitud es la del modelo. Tampoco la temperatura sin `weather.json`, ni otra hora que no se rotule "Hora elegida".
10. Acelerar el paso: ni botón "más rápido", ni subida automática por encima de 1,4 m/s, ni correr anunciado en la ayuda para niños.
11. Avisos que tapan el camino, que se acumulan o que no dejan rastro: uno a la vez, que se van solos y quedan en el historial.
12. Perder el foco (botón que desaparece con el foco dentro) o moverlo a otra cosa sin que el usuario lo pida, salvo al abrir una hoja.
13. Controles en la zona del pulgar, en `sab` o en `sat`. Tampoco contenedores con `pointer-events` que roben toques al joystick.
14. Girar el minimapa o fundir la pantalla con movimiento reducido.
15. Textos fijos en el código (como `CAMERA_BUTTON_LABEL`): todos salen de `strings.ts`, y los de lugar, de `content/`.
16. Rotular paradas con nombres no confirmados (la del OSM 1795591637 se llama "Mirador", no "Mirador de Ponent"). Enseñar una ubicación de *Silene*.
17. Rehacer el minimapa o el mapa con WebGL: son DOM y SVG, sin coste de presupuesto 3D.

## 8. Notas para X0.2–X1.4

- `index.html` gana `ui/tokens.css` y un `ui/hud.css`. Los estilos de `#hints`, `#notice` y `#attribution` se sustituyen y no conviven con los nuevos.
- `touch.ts`: se quita el botón de cámara y se respeta la regla 1 de §4.3: si `event.target` no es el lienzo, no hay joystick. Hoy ya escucha en el lienzo, así que basta con que los controles estén por encima.
- La lectura del estado del jugador para el HUD, unas 10 veces por segundo (`propuesta.md` §5), alimenta minimapa, altitud y "faltan {d}".
- E2E: comprobar que el aviso de llegada no entra en la zona del pulgar a 375 × 812 y 812 × 375; tomar capturas a 375, 768 y 1440 px; pasar axe; emular movimiento reducido.

## 9. Prototipo

Directorio: `/private/tmp/claude-501/-Users-lr0y-Workspace/67537e43-1f41-4e05-80c0-9d7a7b7515b0/scratchpad/x01/`.

- `proto/tokens.css`, `proto/hud.css`, `proto/icons.mjs` y `proto/build.mjs` (genera `out/*.html` y `out/*.png` con Playwright).
- `capture.mjs` (capturas nuevas desde `http://127.0.0.1:3000/?start=…`, sin `#dock` ni los controles táctiles), `geo.py` (recortes de la ortofoto, distancias, coordenadas y perfil desde `trail.json`), y `findpatch2.py`, `crop_patches.py`, `measure.mjs`, `measure.py` y `colors.py` (contraste).
- Imágenes en `out/`:
  - las cinco pantallas a los cuatro tamaños: `{p375,l812,t768,d1440}-{default,mas,ficha,mapa,autosubida}.png`;
  - extras: `d1440-primera-vez`, `p375-ajustes`, `{p375,l812,d1440}-cuaderno`, `p375-solo-paisaje`, `{p375,d1440}-ficha-clara`, `p375-contraste-alto`, `p375-texto-150` y `d1440-componentes` (tablero de estados).

## 10. Preguntas abiertas que cambian la implementación

1. **La hora real con un cielo fijo.** Hasta X2 el cielo es el preset `day` con el sol quieto (`sky.ts:26`). A las 22:00, "22:00 · Ahora en Calp" sobre un mediodía es una verdad a medias (principio 3.1). Propuesta: hasta X2, el subtexto dice "Luz de ejemplo" en lugar de "Ahora en Calp", y la hoja "Hora y tiempo" lo explica con `skyExample`. Lo decide el responsable técnico.
2. **Color de la ruta.** El sendero se llama Ruta Roja, pero el boceto aprobado usa ámbar. El ámbar con funda pasa 3:1 sobre cualquier punto de la ortofoto y no se confunde con el verde de la vegetación en las daltonías más comunes; un rojo sobre pinar oscuro tiene poco contraste de luminancia. Se mantiene el ámbar salvo que el usuario quiera el rojo de la señalización.
3. **Dónde va "Créditos" en el teléfono vertical.** Lo he subido bajo la hora: abajo choca con la fila de botones al 150 % y con la zona del indicador de inicio. El boceto aprobado era apaisado y no resolvía este caso.
4. **Aviso en el teléfono vertical a sab + 300 px**, por encima de la zona del pulgar. Queda en la mitad inferior, pero más alto que en el boceto apaisado. La alternativa, ponerlo junto a los botones, rompe el "centro, abajo" aprobado.
5. **Correr (Mayús, 2,6 m/s) sigue en el código.** No se anuncia, pero existe. ¿Se mantiene como atajo oculto para adultos o se quita para cumplir del todo "el paso es real"?
6. **Valenciano**: los términos marcados **(revisar)** en §6, sobre todo "Ajustos", "Hora triada", "On estic?", "Para / Atura" y "Vés-hi ara". Habría que pedir al parque o al Ajuntament el uso que tienen en su señalización.
