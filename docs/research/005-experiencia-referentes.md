# 005 — Experiencia: referentes, accesibilidad, calendario natural y evidencia de valor

- Fecha: 2026-10-12. Trabajo de investigación; no se ha descargado nada en el repositorio, no se ha editado otro archivo y no se ha hecho commit.
- Idioma: castellano, para el equipo. Los nombres de criterios (WCAG, XAG, GAG) se dejan en inglés.
- Para qué sirve: alimenta `docs/specs/004-experiencia/propuesta.md` (referentes, accesibilidad, calendario natural, evidencia).
- Público: vecinos (nostalgia), escuelas (aprender), turistas (preparar la visita) y personas que no pueden subir (movilidad reducida, mayores). Comprador previsto: el Ajuntament de Calp.
- Nada de lo que sigue es una coordenada, la ubicación de una planta de *Silene hifacensis* ni la de un nido.

## Cómo leer este documento

- **Lectura**: `L` = página o ficha leída con WebFetch · `API` = consulta a una API abierta (iNaturalist, GBIF, Wikimedia Commons) hecha con WebFetch · `B` = solo resumen de una búsqueda web, no leída · `[conoc.]` = conocimiento general del redactor, no verificado en esta sesión.
- **Confianza**: **A** alta (fuente primaria leída o recuento grande) · **M** media · **B** baja (muestra pequeña, fuente secundaria o inferencia).
- Cajas geográficas usadas en los recuentos (se repiten en el anexo A para que cualquiera pueda rehacerlas):
  - **Caja del parque**: lat 38,630–38,646, lon 0,060–0,085 (≈ 1,8 × 2,2 km). Incluye el Penyal, el tómbolo norte y parte del casco urbano.
  - **Caja de Calp**: lat 38,60–38,67, lon 0,02–0,13 (≈ 8 × 10 km). Incluye mar abierto, las Salinas y el pueblo.
  - **Caja de Alicante norte**: lat 38,35–38,85, lon −0,60–0,25.
  - **Caja del Levante-Baleares**: lat 37,6–40,0, lon −1,5–4,5 (Valencia, Alicante, Murcia norte e Illes Balears). Se usa cuando la muestra local es demasiado pequeña; la fenología de plantas costeras es parecida, la del interior no.

## Limitaciones de esta sesión

- La web de la GVA (`parquesnaturales.gva.es`) dio `ECONNREFUSED`: no se pudo releer la guía oficial ni el Banc de Dades de Biodiversitat (BDBCV). No hay ninguna cifra de la GVA releída hoy; las del repositorio (`content/facts.json`) son de 2026-10-10.
- WebFetch no extrae el texto de los PDF de MITECO (texto comprimido). La fenología del vencejo pálido y el reparto de colonias de la gaviota de Audouin vienen del resumen de una búsqueda sobre esas fichas (`B`).
- WebSearch devuelve resúmenes, no la página. Todo lo marcado `B` hay que releerlo en la fuente antes de usarlo en una ficha.
- **Los recuentos de iNaturalist y GBIF son esfuerzo de observación, no censos.** Los leyó el resumidor de WebFetch, que pudo equivocarse al transcribir: se comprobó que la suma de meses coincide con el total (salvo cuatro casos menores, anotados en §3.3, §3.4 y §7). Las plantillas del anexo A permiten repetirlos.
- Se hizo una prueba de conectividad con `curl` (solo código HTTP, cuerpo descartado) antes de decidir ceñirse a WebFetch. Todos los datos de este documento salen de WebFetch o WebSearch.
- No se evaluaron visitas 3D de museos (Matterport y similares) ni el cursor del perfil de elevación de Wikiloc: no cambian las lecciones.

---

## Resumen

### Diez lecciones de diseño

1. **Un solo "sistema de recorrido" sirve a los cuatro públicos.** La lista ordenada de las 9 paradas oficiales (`trail-stops`) es a la vez guía en texto (accesibilidad), visita guiada (escuela, turista), lista de destinos del viaje rápido (movilidad reducida) y marcas del perfil de altitud. Se construye una vez, desde `facts.json`. Referentes: visitas guiadas de Discovery Tour, perfil con paradas de Komoot.
2. **HUD de ruta mínimo, de cuatro piezas** (§1.2.1): minimapa con rumbo y opción norte/rumbo arriba; perfil de altitud con punto de posición y paradas; cifras restantes con su método visible; aviso al salir del corredor. No fiar la navegación a un mapa solo diegético (Firewatch): sirve a su ficción, no a un público mayor ni a un comprador público.
3. **Viaje rápido = pin → fundido corto → llegada orientada → anuncio → deshacer** (§1.2.2). El paso a pie sigue siendo 1,4 m/s, que coincide con la recomendación de Meta (3 mph). El viaje rápido es una acción explícita, nunca un "acelerar".
4. **Comodidad por defecto, sin casco.** Sin balanceo de cabeza, cámara estable en las escaleras, FOV ajustable, "modo tranquilo" y viñeta opcional. La evidencia de viñeta y teleport es de visores VR; la transferencia a pantalla plana es plausible, no probada.
5. **Un lugar habla mejor con voz humana, disparada por llegar**: fragmentos de narración al alcanzar cada sitio (Dear Esther) con voz local (guardaparque, vecino; Hidden Worlds). Siempre con transcripción: el texto debe ser igual de bueno que el audio.
6. **Paquete escolar, no solo el mundo**: sesión de 45–60 min, ficha del docente y preguntas ancladas a las paradas (patrón del piloto de Discovery Tour). La evidencia dice que más inmersión no enseña más por sí sola (Makransky 2019).
7. **Modo foto barato y acotado**: cámara libre limitada al entorno del sendero, sin HUD, hora del sol, marco con lugar/cota/fecha y créditos, descarga local o Web Share. Es el canal de boca a boca del Ajuntament, sin servidor.
8. **Calendario "El Penyal en [mes]" solo con fenología documentada y etiquetada** (documentado / observado / estimado). Nunca puntos de silene ni de nidos. Varias premisas del encargo no se sostienen con fuentes (ver "Lo que cambia", abajo).
9. **La honestidad es un rasgo del producto**: mostrar de dónde sale cada dato y su fiabilidad ("¿Qué tan fiel es?": LiDAR 2016, MDT 1 m, límites). Everest VR presume de cientos de miles de fotos sin medir su exactitud; nosotros podemos hacer lo contrario.
10. **La accesibilidad es requisito comercial y de producto.** El Ajuntament está sujeto al RD 1112/2018: hoy se audita contra EN 301 549 V3.2.1 (WCAG 2.1 AA); la V4.1.1 (WCAG 2.2 AA) se publicó el 2026-09-02 y se espera vinculante hacia el 2026-12-16. Hay que entregar declaración de accesibilidad y canal de comunicación. Y no se prometen beneficios de salud: la evidencia es débil (§4).

### Lo que cambia respecto a lo que se daba por hecho

- **La gaviota de Audouin no cría en el Penyal.** Las colonias de cría en España están en el delta del Ebro, Columbretes, Baleares, Murcia (isla Grosa, Salinas de San Pedro), Alborán y Chafarinas (ficha MITECO, `B`). En la caja de Calp hay 155 registros (GBIF) con pico en agosto–octubre, probablemente en las Salinas, fuera del parque. Entra como visitante, no como colonia.
- **No hay ningún registro abierto de cigarras dentro del parque** (iNaturalist: 0 en la caja del parque y 0 en la de Calp; GBIF: 1 en la de Calp). La temporada regional es junio–septiembre con pico en julio. El sonido de cigarras puede ir como ambiente estival, pero la afirmación "se oyen en el Penyal" es de confianza baja hasta preguntar al parque o al usuario.
- **Halcón de Eleonora**: solo 4 registros (agosto–septiembre) en la caja de Calp. Se mantiene `unverified` (`eleonora-falcon`); no es especie de cría del Penyal con ninguna fuente.
- **Flora rupícola amenazada**: no hay datos fiables de floración de *Teucrium hifacense*, *Centaurea rouyi*, *Pseudoscabiosa saxatilis* ni *Hippocrepis valentina* (anotaciones de floración de iNaturalist: 2 y 0 para las dos últimas; las otras dos solo tienen 3 y 17 observaciones sin anotar, repartidas por casi todo el año). Solo la silene tiene meses con fuente oficial. iNaturalist oculta las coordenadas de taxones amenazados, así que un recuento bajo no prueba ausencia. *Capparis spinosa* y *Euphorbia dendroides* tienen 0 observaciones en la caja del parque: no entran en el calendario.
- **Las fotos con licencia abierta son escasas**: 119 de 6 697 observaciones de calidad investigación en la caja del parque (1,8 %) tienen foto CC0 o CC BY. En Wikimedia Commons, 29 de los 40 primeros resultados de "Penyal d'Ifac / Peñón de Ifach" son CC BY-SA, excluidos por `CLAUDE.md`. El plan realista son fotos propias del usuario o permisos explícitos (§3.6).

---

## 1. Referentes

### 1.1 Tabla de referentes

| # | Referente | Qué es (y qué se verificó) | Copiar | Evitar | Conf. |
|---|---|---|---|---|---|
| 1 | **Apps de senderismo**: Komoot, AllTrails, Gaia GPS, Wikiloc | **Komoot** (`L`): durante la navegación se desliza para ver el perfil de altitud, con un punto en tu posición; otro deslizamiento muestra lo que falta y el tiempo estimado; voz que avisa de giros y de salida de ruta. **AllTrails** (`B`, ayuda oficial): aviso de salida de ruta a unos 50 m, visible en la pantalla de navegación, en la de bloqueo y en el reloj, silenciable con un toque. **Gaia GPS** (`B`, guía de un club, secundaria): botón de posición con dos modos (mapa centrado en ti / mapa que gira con el rumbo arriba) y barra de tres estadísticas a elegir. **Wikiloc** (`B`): ficha con distancia, desnivel ±, cota máxima y mínima | El conjunto mínimo: posición y rumbo, perfil con "tú estás aquí", lo que falta, aviso de salida de ruta. Estadísticas elegibles. Conmutador norte arriba / rumbo arriba | Depender del gesto (deslizar) como único acceso. Cifras de desnivel inconsistentes: usuarios de Camino de Santiago señalan que en Wikiloc la ganancia varía mucho entre tracks de la misma ruta (`B`); nosotros mostramos la cota del MDT y su método | M |
| 2 | **Google Arts & Culture, "Hidden Worlds of the National Parks"** (2016-08-24, centenario del NPS) | `L`: vídeos 360° de cinco parques (Kenai Fjords, Kīlauea, Bryce Canyon, Carlsbad Caverns, Dry Tortugas) guiados por un guardaparque local; web y app; archivo de piezas de los museos de los parques; versión para docentes en la app Expeditions | Guía humano local, archivo de objetos integrado en el recorrido, versión docente | Pasividad: se gira 360°, no se camina (`B`, GoogleWatchBlog). La página es de 2016 y no confirma disponibilidad actual. Atarse a una plataforma ajena: nuestro alojamiento estático sin cuentas dura más | A |
| 3 | **NPS Zion, "Virtual Hikes"** | `B`: vídeos en primera persona a velocidad acelerada de varias sendas del cañón, incluida Angels Landing, sin audio; la senda real exige permiso | El caso de uso: mostrar un sendero restringido o delicado a quien no puede o no tiene permiso. Es el gemelo conceptual de nuestro proyecto | Vídeo mudo, sin texto: obliga a una alternativa textual o de audio (WCAG 1.2.1, A). No tiene guía en texto | M |
| 4 | **Assassin's Creed Discovery Tour** (Origins, Ancient Greece, Viking Age) | `L` (Ubisoft): modo educativo sobre el mundo del juego. Piloto en un instituto de 60 min con el historiador del juego; ficha opcional, guía curricular; profesores citan la geografía que no da una foto de libro. Ubisoft lo presenta como herramienta adicional, no como sustituto del libro. **No se encontró una evaluación formal de aprendizaje** (`B`) | Sesión de 45–60 min, ficha del docente, preguntas ancladas al mapa, visitas guiadas junto a paseo libre | Prometer resultados de aprendizaje sin medirlos | A (producto), B (impacto) |
| 5 | **Walking simulators con lugar**: *Firewatch*, *Dear Esther* | *Firewatch* (`B`): Two Forks, Shoshone National Forest (Wyoming), 1989; sin minimapa; mapa de papel y brújula dentro de la ficción; los críticos admiten que navegar es más difícil que con HUD. *Dear Esther* (`B`): isla hebridea deshabitada (no se confirma Mull); un fragmento de narración nuevo al llegar a cada zona; casi sin jugabilidad | De *Dear Esther*: narración disparada por la llegada. De *Firewatch*: la estética de papel y brújula para el minimapa (aspecto, no mecánica) | Navegación solo diegética para un público mayor o un cliente público | M |
| 6 | **Everest VR** (Sólfar + RVX, 2016) | `B`: montaña generada por fotogrametría de "más de 300 000" imágenes (otro medio dice "decenas de miles"), con retoque manual; las fotos de la expedición de 1953 aparecen en el punto desde donde se tomaron. Ninguna fuente mide la exactitud posicional | La foto histórica en su sitio exacto (re-fotografía): encaja con "Antes y ahora" | Presumir de fidelidad sin medirla. Nosotros mostramos fuente y límite de cada capa | B |
| 7 | **Modos foto** (*Gran Turismo*, *Red Dead Redemption 2*, *The Last of Us Part II*, NVIDIA Ansel) | `L` (Wikipedia, Wojciechowski y Shelton 2022 en *Acta Ludologica*, resumen): los modos foto copian los controles de una cámara real; los "fotógrafos virtuales" comparten motivos con los reales (imágenes llamativas, recuerdos, pericia) y se les llama "turistas virtuales"; sirven de marketing gratuito (`B`, NVIDIA y prensa). Ansel (2016) dejó de recibir soporte en febrero de 2022 | Cámara libre, controles de cámara real, ocultar interfaz, compartir | Depender de middleware externo; cámara sin límites | M |
| 8 | **Guías de locomoción de Meta** + Habgood et al. 2018 (IEEE VR) | `L` (Meta): un teleport que cambia la dirección de la mirada desorienta más; el parpadeo (*blink*) y los sonidos espaciales ayudan a reorientarse; viñetas, giros por pasos, aceleraciones breves y raras; velocidad de paseo ≈ 1,4 m/s; modo sentado. `B` (Habgood): con 36 personas en un visor, deslizarse a gran velocidad entre nodos fijos dio menos mareo que caminar continuo a velocidad normal | Fundido corto, orientación explícita, sonido continuo, opciones de comodidad. La velocidad real de 1,4 m/s ya concuerda | Extrapolar sin probar: todo es VR con visor, no pantalla plana | M |

### 1.2 Patrones concretos (propuesta del redactor, apoyada en lo anterior)

#### 1.2.1 HUD de ruta

- **Minimapa** (curvas del ICV): marcador con cono de visión; conmutador rumbo arriba / norte arriba (Gaia); las 9 paradas numeradas; botón "centrar".
- **Perfil de altitud horizontal** con punto "estás aquí" (Komoot) y las paradas como marcas. Tocarlo o arrastrarlo es el origen del viaje rápido (§1.2.2).
- **Cifras**: cota actual (del MDT, no barométrica), distancia recorrida y restante, tiempo restante *a paso de paseo*. Cada cifra enlaza con su método. Distancia y tiempo oficiales están en conflicto en `facts.json` (`trail-length`: ~2 km ida y vuelta GVA, 0,83 km MACMA, 1,68 km medidos en planta; `trail-time`): el HUD no debe presentar una cifra propia como oficial.
- **Salida de corredor**: el sendero es único y "no salir del sendero" es norma (`access-prohibitions`). El aviso al alejarse hace de las alertas de AllTrails, con tono de cortesía y sin sonido por defecto.
- Cada pieza tiene equivalente en texto vivo (§2, A6 y A30). El HUD tiene tres tamaños: compacto, normal y solo texto.

#### 1.2.2 Viaje rápido que no desorienta

1. Origen: pin en el minimapa, marca en el perfil o fila de la lista de paradas (la misma lista de la guía en texto). Confirmar con un toque: "Ir al Mirador de Ponent".
2. Transición: fundido a negro de 150–300 ms (corte seco con "modo tranquilo"). El ambiente sonoro no se corta: el sonido espacial ayuda a reorientarse (Meta).
3. Llegada: en el punto de vista de la parada, con la mirada hacia lo que se describe (`arrivalYaw` definido por el contenido de cada parada). Meta advierte que cambiar la mirada empeora la desorientación: por eso (a) tras llegar no hay movimiento durante ~1 s, (b) se anuncia en la región viva "Has llegado al Mirador de Ponent, mirando al noroeste hacia la Pobla d'Ifac", (c) se muestra una rosa de los vientos breve. Alternativa en ajustes: "mantener mi orientación respecto al sendero".
4. Deshacer: botón "Volver" a la posición anterior.
5. Regla del proyecto: el paso a pie no se acelera (1,4 m/s, decisión del usuario). El viaje rápido es otra acción.
6. Pendiente de probar con mayores: si el fundido desorienta más que un deslizamiento rápido entre nodos (Habgood). Hay un guion de pruebas en `docs/specs/002/pruebas-vecinos.md`.

#### 1.2.3 Modo foto

- **Qué gusta** (§1.1, fila 7): controles de cámara real, compartir, sentirse "turista virtual".
- **Qué lo hace barato** [conoc.]: sin profundidad de campo ni efectos nuevos; el mundo se congela; captura en el mismo frame que el último `render` (evita `preserveDrawingBuffer`); opcionalmente un único render a mayor resolución al disparar; descarga local o Web Share, sin subida.
- **Qué incluir**: proporción (16:9, 4:5, 1:1), nivelar horizonte, FOV, hora del sol (SunCalc, ya previsto), ocultar interfaz, marco con lugar, cota y fecha simulada.
- **Límites**: cámara acotada a un entorno del sendero y por encima del terreno (nunca dentro de la roca; coherente con "no salir del sendero"); créditos de datos (ICV, OSM) en el pie de la imagen exportada, a validar con ADR 0007 y `CREDITS.md`; texto alternativo sugerido para compartir ("Vista desde el Mirador de Ponent hacia la Pobla d'Ifac").

---

## 2. Accesibilidad

### 2.1 Marco normativo (lo que le importa al Ajuntament)

| Norma | Qué dice | Fuente | Lectura |
|---|---|---|---|
| **RD 1112/2018** (BOE-A-2018-12699) | Sujetas: administraciones generales, autonómicas y **entidades locales** (art. 2.1.c). Contenido perceptible, operable, comprensible y robusto (art. 5.1). **Declaración de accesibilidad** detallada, actualizada al menos una vez al año, con enlace "Accesibilidad" en cada página (art. 15). **Mecanismo de comunicación** (art. 10): canal electrónico más otro complementario (art. 11), respuesta en 20 días hábiles (art. 12), reclamación (art. 13). Excepción por carga desproporcionada, motivada y revisada (art. 7). Exclusiones: mapas en línea si la navegación esencial es accesible por otros medios (art. 3.4.d), contenido de terceros no financiado ni controlado por la entidad (art. 3.4.e), reproducciones de colecciones de patrimonio cuando la accesibilidad total sea incompatible con su conservación (art. 3.4.f) | BOE, texto consolidado "informativo, sin valor jurídico" | `L` |
| **Norma técnica** | El art. 6.1 presume conformidad con las normas armonizadas publicadas en el DOUE. Hoy es **EN 301 549 V3.2.1** (2021-03), citada por la Decisión de Ejecución (UE) 2021/1339 (en vigor desde 2021-08-12), con WCAG 2.1 A y AA. El texto del RD solo menciona la V1.1.2 (2015) como presunción subsidiaria (art. 6.3) | BOE; EUR-Lex | `L` / `B` |
| **EN 301 549 V4.1.1** | Publicada en línea por ETSI el **2026-09-02**; cambia la base a WCAG 2.2 AA. Será vinculante (presunción de conformidad) cuando la Comisión la cite en el DOUE: previsto el **2026-12-16** (otra fuente hablaba de octubre). Hasta entonces sigue la V3.2.1. No se verificó una versión UNE | NDA (Irlanda) | `L` |
| **LCSP art. 126** | Las prescripciones técnicas de un contrato deben tener en cuenta la accesibilidad universal y el diseño para todos. **Texto no verificado**; sí el antecedente (TRLCSP art. 117) | Resumen de búsqueda | `B` |
| **Contexto Calp** | El Ajuntament preparó un Plan de Accesibilidad Turística (fase de diagnóstico en 2021, con análisis de recursos en línea). No se encontró el resultado ni su declaración de accesibilidad web | calpe.es | `L` / `B` |

**Consecuencia:** el proyecto ya fija WCAG 2.2 AA (`CLAUDE.md`, spec AC8). Es el objetivo correcto: cumple 2.1 AA (que es lo exigible hoy) y se adelanta a la V4.1.1. Las exclusiones de los arts. 3.4.d y 3.4.f **no se deben usar como excusa**: pedir criterio jurídico al Ajuntament antes de apoyarse en ellas.

### 2.2 Qué aplica a una experiencia 3D en un `<canvas>`

- Un `<canvas>` WebGL es contenido web: se le aplican WCAG 2.1/2.2 A y AA (cláusula 9 de EN 301 549). El canvas no expone semántica por sí mismo: **toda información y toda acción esencial debe existir también en el DOM** (texto, botones, listas) y ser operable por teclado.
- Referencias de buenas prácticas para juegos, no obligatorias: Game Accessibility Guidelines (GAG), Xbox Accessibility Guidelines v3.2 (2023-06-08) y la nota W3C XR Accessibility User Requirements (XAUR, 2021-08-25, "explícitamente no es una colección de requisitos de base"). Los XAG relevantes son 101 Text display, 102 Contrast, 103 Additional channels for visual and audio cues, 104 Subtitles and captions, 105 Audio accessibility, 106 Screen narration, 107 Input, 109 Objective clarity, 112 UI navigation, 115 Error messages, 116 Time limits, 117 Visual distractions and motion settings, 118 Photosensitivity y 121 Accessible documentation.
- Lo que no aplica: criterios de comunicación en tiempo real, voz o multijugador (no hay), y los requisitos de visor VR.

### 2.3 Checklist para nuestra app

Prioridad: **P0** exigible (WCAG A/AA) o riesgo legal/seguridad · **P1** recomendable fuerte (GAG básico e intermedio, XAG) · **P2** deseable. "Verif." = cómo se comprueba.

#### Texto y estructura

| ID | Requisito | Norma | Pri. | Verif. |
|---|---|---|---|---|
| A1 | **Guía de la ruta en texto, siempre disponible** (no solo sin WebGL2): lista ordenada de las 9 paradas con distancia, cota y descripción de `facts.json`, con fuentes y estado. Imprimible | WCAG 1.1.1, 1.3.1; spec AC8 | P0 | NVDA/VoiceOver recorren la guía completa |
| A2 | El `<canvas>` lleva `role="img"` y `aria-label` que resume la escena y enlaza a la guía; ningún control ni dato esencial vive solo dentro del canvas | WCAG 1.1.1, 4.1.2 | P0 | axe + revisión manual |
| A3 | Fichas de puntos de interés y cuaderno en DOM real (encabezados, listas), con gestión de foco: abrir mueve el foco, `Esc` cierra y devuelve el foco, el foco nunca queda oculto | WCAG 2.4.3, 2.4.7, 2.4.11 | P0 | Teclado solo |
| A4 | `lang` correcto en la página y en cada trozo en otro idioma (es, va, en); selector de idioma siempre visible | WCAG 3.1.1, 3.1.2 | P0 | axe |
| A5 | Lenguaje claro; versión de lectura fácil de la guía | GAG básico "Use simple clear language" | P2 | Revisión editorial |
| A6 | **Regiones vivas** (`aria-live="polite"`) para: llegada a una parada, hitos de progreso, salida del corredor, llegada de un viaje rápido, cambio de modo. Con límite de frecuencia y desactivables | WCAG 4.1.3; XAUR REQ 8a | P0 | Lector de pantalla |
| A7 | Botón "¿Dónde estoy?" que anuncia posición, cota, rumbo y siguiente parada | GAG intermedio "indicate current objectives" | P1 | Prueba con usuarios |

#### Entrada y mando

| ID | Requisito | Norma | Pri. | Verif. |
|---|---|---|---|---|
| A8 | Todo operable con teclado, sin trampas; atajos documentados. Las teclas sueltas (WASD, P) solo actúan con el canvas enfocado o se pueden remapear | WCAG 2.1.1, 2.1.2, 2.1.4 [conoc. sobre la excepción] | P0 | Playwright + manual |
| A9 | Alternativas a flechas y WASD; mando previsto; remapeo de controles | GAG básico "controls remapped" | P1 | Manual |
| A10 | Objetivos táctiles de 24 × 24 px CSS como mínimo; 44 × 44 en los controles primarios, con separación | WCAG 2.5.8 (2.2 AA); GAG básico "large and well spaced" | P0 / P1 | Inspección |
| A11 | Nada obliga a arrastrar: el joystick virtual y el giro de cámara tienen alternativa de un solo toque (botones, "caminar" conmutable, auto-subida) | WCAG 2.5.7 (2.2 AA), 2.5.1 | P0 | Táctil real |
| A12 | El movimiento del dispositivo (giroscopio) nunca es la única vía y está desactivado por defecto | WCAG 2.5.4 | P0 | Móvil real |
| A13 | "Caminar" como conmutador, sin mantener pulsado | GAG intermedio "avoid hold buttons" | P1 | Manual |
| A14 | Funciona en vertical y horizontal | WCAG 1.3.4 | P0 | Emulación |
| A15 | Sensibilidad de giro, invertir eje Y, velocidad de giro | GAG básico "sensitivity" | P1 | Manual |

#### Movimiento y mareo

| ID | Requisito | Norma | Pri. | Verif. |
|---|---|---|---|---|
| A16 | **Auto-subida** (ya existe) con botón en pantalla, pausa, reanudar y parada opcional en cada punto. Operable con teclado | XAUR REQ 2a; GAG "assist modes" | P0 (núcleo) | E2E existente |
| A17 | Velocidad real 1,4 m/s por defecto. Opciones solo **más lentas** (p. ej. 0,5× y 0,75×); nunca más rápido que el paso real. XAUR REQ 15a pide cambiar la velocidad de viaje: se atiende con el viaje rápido, no acelerando | Decisión del usuario; Meta (≈ 1,4 m/s) | P1 | Medición |
| A18 | Sin balanceo de cabeza, sin sacudidas, sin desenfoque de movimiento por defecto; cámara con elevación estabilizada (filtro) en escaleras y escalones | XAG 117; Meta (*stabilize camera elevation*) | P1 | Revisión de vídeo |
| A19 | **Deslizador de FOV** con valor de partida prudente | XAG 117; GAG | P1 | Manual |
| A20 | Viñeta opcional durante el movimiento; giro por pasos opcional en teclado y mando. Evidencia de VR con visor (Fernandes y Feiner 2016, `B`) | Meta | P2 | Prueba con mayores |
| A21 | **Modo tranquilo**: se activa solo con `prefers-reduced-motion` y también a mano. Quita balanceo, parallax y transiciones (fundidos pasan a corte), y reduce partículas y oleaje. Es AAA en WCAG, pero barato y es un riesgo de salud (vestibular) | WCAG 2.3.3; técnica C39; XAG 117 | P0 | Emulación del medio |
| A22 | **Pausar el mundo** (agua, nubes, aves). El movimiento ambiental permanente podría caer en 2.2.2; la excepción "esencial" es discutible | WCAG 2.2.2 | P1 | Manual |
| A23 | Sin destellos de más de 3 por segundo; limitar brillos especulares del mar y el bloom; ninguna transición estroboscópica en el túnel | WCAG 2.3.1; XAG 118; XAUR REQ 16b | P0 | Revisión de capturas |
| A24 | Viaje rápido según §1.2.2 (fundido corto, anuncio, deshacer) | Meta | P1 | Prueba con mayores |
| A25 | Elección de primera o tercera persona (ya en AC4) | XAG 117 | P1 | Hecho |

#### Visión

| ID | Requisito | Norma | Pri. | Verif. |
|---|---|---|---|---|
| A26 | Contraste de texto ≥ 4,5:1 y de componentes ≥ 3:1. El HUD sobre cielo claro lleva panel sólido o semiopaco, nunca texto suelto | WCAG 1.4.3, 1.4.11; XAG 102 | P0 | axe + contraste |
| A27 | Texto base ≥ 16 px, ampliable al 200 %; reflujo hasta 320 px CSS; espaciado de texto; control de escala del HUD | WCAG 1.4.4, 1.4.10, 1.4.12; GAG "resize interfaces" | P0 | Zoom 400 % |
| A28 | Nada se distingue solo por color: categorías de paradas, estados de ruta y capas del mapa llevan icono, forma y etiqueta. Paleta segura para daltonismo (p. ej. Okabe–Ito) en minimapa y perfil | WCAG 1.4.1; GAG básico | P0 | Simulador de daltonismo |
| A29 | Tema de alto contraste y oscuro; respetar `forced-colors` | XAG 102 | P1 | Emulación |
| A30 | El minimapa tiene equivalente textual vivo ("Km 0,42 · 118 m · rumbo noreste") y se puede ocultar | RD art. 3.4.d (no confiar en la exclusión) | P1 | Lector |
| A31 | Nada depende del hover | WCAG 1.4.13 | P0 | Táctil |

#### Audio

| ID | Requisito | Norma | Pri. | Verif. |
|---|---|---|---|---|
| A32 | Audio apagado hasta el primer gesto del usuario; volumen general y por capa (ambiente, voz, efectos) | WCAG 1.4.2; GAG básico | P0 | Manual |
| A33 | Toda narración con transcripción y, si va sincronizada con vídeo, con subtítulos. Descripción de audio o alternativa para vídeo con contenido visual | WCAG 1.2.1, 1.2.2, 1.2.3, 1.2.5 | P0 | Revisión |
| A34 | Información nunca solo por sonido; opción de subtítulos de ambiente ("[gaviotas cerca]") | GAG básico / intermedio; XAG 103, 104 | P0 / P2 | Manual |

#### Tiempo, memoria y proceso

| ID | Requisito | Norma | Pri. | Verif. |
|---|---|---|---|---|
| A35 | Sin límites de tiempo ni pérdida de sesión | WCAG 2.2.1; XAG 116 | P0 | Manual |
| A36 | Ajustes y cuaderno se recuerdan en el dispositivo. Las preferencias en `localStorage` no son cookies, pero se pide al Ajuntament que su delegado de protección de datos lo confirme | GAG básico "settings saved" | P1 | Manual |
| A37 | Recordatorio de controles y del objetivo actual al alcance | GAG intermedio | P1 | Manual |
| A38 | **Declaración de accesibilidad** (con enlace "Accesibilidad" en cada página) y **canal de comunicación** con correo y un segundo canal, en el idioma de la página. Lo publica el Ajuntament; nosotros entregamos el texto, el estado de cada criterio y las limitaciones conocidas | RD 1112/2018 arts. 10–15 | P0 | Entrega |
| A39 | Documentación (README del mantenedor, guía del docente) en formato accesible | XAG 121; GAG | P1 | Revisión |
| A40 | **Plan de verificación** (§2.5) | GAG intermedio "include people with impairments in playtesting" | P1 | Informe |

### 2.4 Decisiones que necesita el responsable técnico

1. **Velocidad**: ¿se permite ir más lento que 1,4 m/s? Recomendado sí (A17); la decisión previa solo prohíbe acelerar.
2. **Narración con voz**: si hay voz, A33 es obligatoria; si no la hay, el texto basta y el coste de accesibilidad baja mucho. Se recomienda empezar sin locución, con texto, y añadir voz después.
3. **Viñeta y giro por pasos**: evidencia solo de visores VR. Se propone ofrecerlos como opción apagada y probarlos con mayores antes de recomendarlos.
4. **Atajos de una tecla**: ¿se permiten con el canvas enfocado (excepción de 2.1.4) o se prefiere un modificador? La excepción es válida; con modificador se evitan choques con lectores de pantalla.

### 2.5 Verificación propuesta

- Automática: axe en Playwright en cada vista; emulación de `prefers-reduced-motion`; capturas a 375 / 768 / 1440 px y zoom 400 %.
- Manual: teclado solo; NVDA con Firefox y Chrome; VoiceOver en iOS Safari; TalkBack en Android; simulador de daltonismo.
- Con personas: ampliar el guion de `docs/specs/002/pruebas-vecinos.md` con al menos una persona mayor de 70, una con movilidad reducida y una usuaria de lector de pantalla. Registrar el cuestionario corto de mareo (SSQ) y el tiempo hasta completar "Llévame a la cima".

---

## 3. Calendario natural del Penyal

### 3.1 Método

- **Floración y frutos**: recuento mensual de observaciones de calidad investigación de iNaturalist **con anotación de fenología** ("Flowering" o "Fruits or Seeds"), caja del Levante-Baleares (`API`). Se considera floración un mes con ≥ 20 % del mes de mayor recuento, y pico ≥ 60 %. La anotación la pone quien observa: N pequeño = poca confianza.
- **Presencia en el Penyal**: observaciones de calidad investigación en la caja del parque (`API`).
- **Aves, insectos y mar**: registros mensuales de GBIF (iNaturalist, eBird y otros conjuntos) en la caja de Calp (`API`). **Mide esfuerzo de observación** (más gente en invierno-primavera y en turismo), no abundancia. Para la **cría** se prefieren fichas de literatura (Vertebrados Ibéricos, MNCN-CSIC, `L`).
- Descriptores de lo que "se ve" o "se oye": `[conoc.]` salvo indicación.
- Fuentes **no** leídas: GVA, BDBCV, Flora iberica, Anthos, Atlas de SEO/BirdLife. Quedan como petición (§3.7).

### 3.2 Reglas de contenido

- ***Silene hifacensis***: solo meses y ciclo (`silene-biology`, verificado: florece de marzo a junio y fructifica de mayo a julio; MITECO y Decreto 40/2008). Ficha sin mapa, flecha ni "aquí crece" (`silene-history`). Cero instancias 3D. Una comprobación cruzada de iNaturalist (anotación de floración, sin filtro de lugar) da N = 3 (abril 2, mayo 1): coherente, pero demasiado pequeña para usarse.
- **Nidos**: nunca se muestran. Del halcón peregrino se muestra la norma oficial (escalada prohibida en caras N y NO de abril a junio, `access-climbing-ban`), no un punto. De las gaviotas, lo que dice la GVA: agresivas en primavera cerca de la bifurcación (`gull-breeding`).
- **Etiqueta de fiabilidad en cada tarjeta**: "documentado" (fuente oficial o literatura), "observado" (recuento abierto) o "estimado". Lo estimado nunca se presenta como hecho. Cada dato nuevo sería un hecho de `facts.json` (id propuesto `phenology-<especie>`), con estado `unverified` hasta que lo confirme el parque.

### 3.3 Flora

Datos de floración: iNaturalist, anotación "Flowering", caja del Levante-Baleares (excepto silene). Presencia: caja del parque, observaciones de calidad investigación.

| Especie | Floración | Frutos u otra fase | Qué se ve [conoc.] | N (flor) | Obs. en el parque | Conf. |
|---|---|---|---|---|---|---|
| *Silene hifacensis* (silene de Ifach) | marzo–junio | fructifica mayo–julio | Solo en ficha, sin ubicación | oficial | no se usa | A |
| *Pistacia lentiscus* (lentisco) | marzo–abril (rango probable marzo–mayo; Flora Vascular da abril–mayo en Andalucía occidental, `L`) | frutos de agosto a febrero, pico septiembre–noviembre (N = 103; Flora Vascular: septiembre–octubre) | Matorral perenne; flores diminutas rojizas; bayas rojas que pasan a negras | 30 | 111 | M |
| *Chamaerops humilis* (palmito) | abril–mayo | frutos agosto–septiembre | Mata de abanicos; inflorescencias entre las hojas | 11 | 30 | B |
| *Salvia rosmarinus* (romero) | **dos tandas**: enero–abril y septiembre–diciembre; casi nada junio–agosto | — | Flor azul lila clara sobre el matorral | 127 | 11 | A |
| *Lavandula dentata* (cantueso) | febrero–mayo y octubre–diciembre | — | Mata gris con espigas lilas | 47 | 80 | M |
| *Pinus halepensis* (pino carrasco) | sin dato (la anotación de iNaturalist no tiene registros en la muestra) | conos todo el año [conoc.] | Árbol de copa abierta, base del paisaje | 0 | 19 | — |
| *Asphodelus fistulosus* (gamoncillo) | enero–mayo, pico febrero–abril | — | Varas de flores blancas con raya parda | 53 | 27 | A |
| *Arisarum vulgare* (candelillos) | octubre–abril | — | Espatas pardas y blancas a ras de suelo | 43 | 52 | M |
| *Drimia maritima* (cebolla albarrana) | agosto–octubre, **pico septiembre** | — | Varas blancas sin hojas; hojas grandes en invierno | 39 | 71 | M |
| *Lapiedra martinezii* | agosto–octubre, **pico septiembre** | — | Bulbo otoñal de flor blanca pequeña | 76 | 25 | A |
| *Crithmum maritimum* (hinojo marino) | julio–septiembre | — | Umbelas amarillo verdosas en roca costera | 26 | 94 | M |
| *Erica multiflora* (brezo) | septiembre–diciembre, pico octubre–diciembre | — | Matas bajas rosadas | 57 | 8 | M |
| *Ceratonia siliqua* (algarrobo) | octubre–noviembre | — | Árbol; flores discretas | 15 | 10 | B |
| *Osyris lanceolata* (bayón) | marzo–julio | — | Arbusto discreto | 8 | 41 | B |
| *Pallenis maritima* (margarita de mar) | marzo–junio, pico abril | — | Margaritas amarillas | 81 | 93 | A |
| *Fagonia cretica* (abrojo de Creta) | enero–mayo, pico abril | — | Planta baja de flores rosadas | 76 | 32 | A |
| *Petrosedum sediforme* (uña de gato) | junio–julio | — | Crasulácea de flor amarilla en piedra | 24 | 22 | M |
| *Oxalis pes-caprae* (**exótica invasora**) | enero–abril y diciembre | — | Alfombras amarillas en suelos removidos de la base | 116 | 125 | A |
| *Cistus albidus* (jara blanca) | febrero–mayo, pico marzo–mayo | — | Flor rosa | 115 | **2** | A (flor), B (presencia) |
| Rupícolas: *Teucrium hifacense*, *Centaurea rouyi*, *Pseudoscabiosa saxatilis*, *Hippocrepis valentina*, *Asperula paui* | **sin dato fiable**: anotaciones de floración 2 (*Pseudoscabiosa*) y 0 (*Hippocrepis*); *Teucrium* 3 observaciones y *Centaurea* 17 sin anotar; *Asperula* no consultada. FloraVeg da mayo–julio para el género *Pseudoscabiosa* (`B`, no la especie) | — | Solo fichas, sin ubicación | ≤ 2 | *Pseudoscabiosa* 0, *Hippocrepis* 1; las demás no consultadas (y las amenazadas se ocultan en iNaturalist) | B |
| *Capparis spinosa* (alcaparra), *Euphorbia dendroides* | **no entran**: 0 observaciones en el parque | — | — | — | 0 | — |

Notas:

- *Cistus albidus*: la floración es sólida, pero presenta solo 2 observaciones en la caja del parque. No debería ser protagonista visual.
- *Lapiedra martinezii*: el resumidor dio total 76 y los meses suman 77; la diferencia no cambia el patrón (pico septiembre).
- *Oxalis pes-caprae* es una especie introducida muy visible en invierno-primavera cerca de la base. Mostrarla "tal como es" encaja con la regla de fidelidad, pero la ficha debe decir que es exótica.
- Silene, rupícolas y *Juniperus phoenicea* (3 observaciones en el parque; GVA la cita en `flora-rupicola`): no hay cobertura 3D (regla de colocación de la vegetación, `docs/specs/002/vegetacion-especies.md`).

### 3.4 Fauna

#### Aves

| Especie | Estado en el Penyal | Cría (meses) | Registros GBIF en la caja de Calp | Qué se ve u oye | Conf. |
|---|---|---|---|---|---|
| **Gaviota patiamarilla** (*Larus michahellis*) | Cría en el parque; agresiva en primavera cerca de la bifurcación (`gull-breeding`, GVA) | Puesta en **marzo–abril** en el Mediterráneo (Vertebrados Ibéricos, `L`); los pollos vuelan ≈ 45 días tras eclosionar, es decir hacia mayo–junio (inferencia del resumidor) | N = 1 791 (suma de meses 1 789): todos los meses, picos enero–febrero, abril y octubre. Obs. iNaturalist en el parque: 522 | Reclamos largos, vuelo junto al cantil, adultos defendiendo. Audio aprobado: XC624044 (CC BY 4.0) | A (cría), M (fechas) |
| **Halcón peregrino** (*Falco peregrinus*) | Cría en el parque; veda de escalada N y NO abril–junio (`falcon-breeding`, `access-climbing-ban`) | Vuelos nupciales **enero**; puesta de la 3.ª semana de febrero a la última de marzo; incubación 28–33 días; primeros vuelos ≈ 45 días tras eclosionar, es decir mayo–junio (Vertebrados Ibéricos, `L`; inferencia) | N = 43 (suma 42), sin patrón: **no usar para fenología** | Vuelo en picado, silueta. Sin audio con licencia verificada | A (cría), M (fechas) |
| **Cormorán moñudo** (subespecie mediterránea *desmarestii*) | La GVA lo cita (`fauna-other`); una guía de Calp lo dice "refugiado" en el peñón (`B`). **Sin dato de cría ni de parejas en Ifac** (`bird-pair-counts`, `unverified`) | La subespecie: recuento de nidos **diciembre–junio** (censo de aves marinas de Murcia 2017, `B`) y noviembre–junio (Parc national des Calanques, `B`). La forma atlántica pone en febrero (Vertebrados Ibéricos, `L`). Ningún dato de Ifac | N = 283, pero solo 258 con mes registrado: todo el año | Ave oscura posada en cornisas sobre el mar | M (presencia), B (cría en Ifac) |
| **Vencejo pálido** (*Apus pallidus*) | La GVA lo cita | Llegada de **finales de febrero**, a veces hasta principios de octubre (ficha MITECO, `B`). Cría en acantilados y edificios | N = 104: **marzo–septiembre**, pico junio–agosto | Bandadas de vuelo rápido; gritos agudos. Sin audio CC0 o CC BY (búsqueda del responsable técnico) | M |
| **Cernícalo** (*Falco tinnunculus*) | La GVA lo cita | — | N = 78: todo el año | Cernido junto a la pared | M |
| **Collalba negra** (*Oenanthe leucura*) | La GVA la cita. **No es** *Phoenicurus ochruros* | Residente estricto; cría de **finales de marzo a mediados de agosto** (Vertebrados Ibéricos, `L`, datos de Guadix y Almería) | N = 55: todo el año | Pájaro negro de cola con borde blanco en pedreras. Sin audio válido | M |
| **Curruca rabilarga** (*Curruca undata*) | La GVA la cita | — | N = 11 (muestra pequeña) | Pájaro discreto en matorral. Audio aprobado: XC930530 (CC BY 4.0) | B |
| **Colirrojo tizón** (*Phoenicurus ochruros*) | No está en la lista de la GVA | — | N = 430: **octubre–marzo** (invernante) | Pajarito oscuro con cola rojiza, en invierno | M |
| **Roquero solitario** (*Monticola solitarius*) | No está en la lista de la GVA | Puesta a finales de abril y primeros de mayo en el Penedès; segunda tanda junio–julio (Vertebrados Ibéricos, `L`) | N = 119: todo el año | Macho azul en riscos | M |
| **Gaviota de Audouin** (*Ichthyaetus audouinii*) | **No cría en el Penyal ni consta en Calp**. Probablemente en las Salinas | Colonias en Ebro, Columbretes, Baleares, Murcia, Alborán y Chafarinas (MITECO, `B`) | N = 155: pico **agosto–octubre** | Visitante estacional, fuera del parque | M |
| **Halcón de Eleonora** (*Falco eleonorae*) | Lo menciona el Ayuntamiento; la GVA no (`eleonora-falcon`) | — | N = 4: agosto 3, septiembre 1 | Sin base para mostrarlo como residente | B |

#### Insectos

| Especie | Meses | Fuente | Qué se oye | Conf. |
|---|---|---|---|---|
| Cigarras (*Cicada orni*, *Lyristes plebejus*) | **junio–septiembre, pico julio**. *C. orni* N = 153: junio 15, julio 75, agosto 44, septiembre 14, octubre 4. *L. plebejus* N = 86: julio 64, agosto 14 (GBIF, caja del Levante-Baleares) | `API` | Canto estridente continuo en pinar y matorral. Audio aprobado: "Cicadas in Greece" (dominio público, autodeclarado) | M (región), **B (Penyal)**: sin registro abierto dentro del parque |

#### Mar

| Especie | Meses (GBIF, caja de Calp) | Qué se ve | Conf. |
|---|---|---|---|
| Alcatraz atlántico (*Morus bassanus*) | N = 29: **diciembre–febrero** | Pescando mar adentro | B |
| Pardela balear (*Puffinus mauretanicus*) | N = 16: enero–marzo (más julio 3) | Bandos lejanos sobre el agua | B |
| Pardela cenicienta (*Calonectris diomedea*) | N = 5: abril–julio | Paso ocasional | B |
| Delfín mular (*Tursiops truncatus*) | N = 30: todos los meses, pico abril | Visita ocasional | B |

- **Zona protegida**: ZEC y ZEPA "Espacio marino de Ifac" ESZZ16006, 1 377,27 ha (Real Decreto 531/2025, `park-natura2000-sea`). Según una ficha EUNIS anterior al decreto (`B`): 2 hábitats (uno de ellos bancos de arena someros 1110, ≈ 99 ha) y 4 especies de aves. **No consta** en las fuentes leídas una pradera de *Posidonia* en este espacio concreto, aunque hay 20 observaciones de *Posidonia oceanica* en la caja del parque. No afirmarla.
- Los bichos marinos concretos del arrecife citados por una guía comercial ("túneles, arcos y galerías") son `B` y de baja prioridad.

### 3.5 Calendario mes a mes ("qué mostrar")

Solo entran elementos con confianza M o A. "Doc." = documentado en literatura o fuente oficial; "Obs." = recuento abierto.

| Mes | Flora que florece | Fauna y cría | Norma o aviso oficial |
|---|---|---|---|
| Enero | Romero y gamoncillo (obs.); *Oxalis* exótica | Vuelos nupciales del peregrino (doc.); alcatraz en el mar (obs.) | — |
| Febrero | Romero, cantueso, gamoncillo, *Oxalis* | Puesta del peregrino empieza (doc.) | — |
| Marzo | **Silene** (solo ficha, doc.), lentisco, jara, cantueso, margarita de mar | Puesta de la gaviota (doc.); llegan los vencejos (doc., obs.); peregrino incuba | — |
| Abril | Lentisco, margarita de mar (pico), abrojo, palmito | Gaviota incubando y primeros pollos (estimado); peregrino con pollos (estimado) | **Empieza la veda de escalada N y NO** |
| Mayo | Palmito, jara, silene (fruto) | Pollos de gaviota (estimado); gaviota agresiva cerca de la bifurcación (doc., GVA); primeros vuelos del peregrino (estimado) | Veda de escalada |
| Junio | Uña de gato; fin de la silene | Gaviotas volanderas (estimado); primeras cigarras (obs. regional) | Veda hasta el 30 |
| Julio | Hinojo marino, uña de gato | **Cigarras** (pico, regional); vencejos | — |
| Agosto | Hinojo marino; empiezan cebolla albarrana y *Lapiedra*; frutos del lentisco | Vencejos; Audouin en las Salinas (obs.) | — |
| Septiembre | **Cebolla albarrana y *Lapiedra* (pico)**, brezo empieza | Se marchan los vencejos (fin de septiembre-principio de octubre, `B`) | — |
| Octubre | Brezo, algarrobo, romero de nuevo, cantueso, candelillos; frutos del lentisco (pico) | Llega el colirrojo tizón (obs.) | — |
| Noviembre | Brezo, romero, candelillos, algarrobo | Colirrojo tizón | — |
| Diciembre | Brezo, romero, candelillos, *Oxalis* | Alcatraz en el mar; cormorán moñudo empieza a criar (dic–jun, sin dato de Ifac) | — |

Uso en la app (propuesta): un selector "El Penyal en…" y una etiqueta "Ahora en el Penyal" según la fecha del dispositivo. En 3D solo variaciones baratas de plantas ya presentes en la paleta (romero, cantueso, lentisco, palmito, pino): color de flor por billboard o textura de instancia, y bayas rojas/negras del lentisco de agosto a diciembre. El resto va en fichas.

### 3.6 Imágenes y sonido: qué licencias hay

| Fuente | Resultado | Implicación |
|---|---|---|
| iNaturalist, fotos CC0 o CC BY (calidad investigación, caja de Alicante norte, `API`) | Lentisco 10 · palmito 13 · cebolla albarrana 13 · cantueso 14 · gaviota patiamarilla 16 · cormorán moñudo 6 · halcón peregrino **0** · vencejo pálido **0** · alcaparra 0 · *Cicada orni* 5 (caja del Levante-Baleares) · *Silene hifacensis* 2 (global; no usar) | Hay algo para lentisco, palmito, cebolla, cantueso y gaviota; nada para peregrino ni vencejo. La licencia es **por foto**: se relee al descargar y se anota la URL de la observación y quien la hizo (CC BY exige atribución) |
| iNaturalist, todas las observaciones del parque | 119 de 6 697 con foto CC0 o CC BY (1,8 %) | Casi todo está bajo licencias no comerciales o reservadas. Hace falta contactar a observadores o fotografiar nosotros |
| Wikimedia Commons, primeros 40 resultados de "Penyal d'Ifac / Peñón de Ifach" (`API`) | 5 CC0, 6 CC BY, 29 CC BY-SA | Las BY-SA no entran (`CLAUDE.md`). Las CC0 (p. ej. "Cerca del Peñón de Ifach en Calpe") y CC BY sirven para paisaje |
| Fotos propias del usuario (de Calp) | — | Es la vía más limpia y la de mayor valor local; con fecha y permiso |
| Sonido | Ya resuelto en `docs/specs/002/sonido-licencias.md`: gaviota (XC624044, CC BY 4.0), curruca rabilarga (XC930530, CC BY 4.0), mar (Commons, CC BY 3.0), cigarras (dominio público autodeclarado), pasos en grava (CC BY 4.0). Sin fuente válida: peregrino, vencejo pálido, collalba negra | — |

### 3.7 Qué falta y a quién preguntar

- **Al parque (GVA)**: calendario de floración de las rupícolas amenazadas (BDBCV, Flora iberica); censos de aves marinas y del halcón peregrino en el Penyal; si hay cormorán moñudo nidificante; si se oyen cigarras en el sendero.
- **A SEO/BirdLife Alicante o al Atlas de Aves Reproductoras**: confirmar fechas de cría de gaviota patiamarilla y vencejo pálido en la costa alicantina.
- **Al usuario (conocimiento local)**: en qué meses se ven alfombras de *Oxalis*, varas de cebolla albarrana y cigarras en el sendero.
- **A los observadores de iNaturalist**: permiso explícito para fotos NC o reservadas, si hacen falta (el permiso por escrito evita el problema de licencia).

---

## 4. Evidencia de valor para los públicos

Resumen honesto: **la evidencia específica para una caminata virtual en pantalla de un sendero real es muy débil o inexistente.** Lo que hay es indirecto: naturaleza simulada en general, VR con visor en mayores, excursiones virtuales escolares y turismo virtual con discapacidad. Casi todo son muestras pequeñas, riesgo de sesgo medio o alto, y visores, que nosotros no usamos.

| # | Hallazgo | Estudio (fuente) | Tipo y tamaño | Evidencia | Qué implica |
|---|---|---|---|---|---|
| 1 | Naturaleza simulada se asocia a más afecto positivo y menos estrés, tensión, fatiga y ánimo bajo. Inmersión *media* dio mayor efecto en afecto positivo que baja o alta | Li et al. 2023, *Front Psychol*, [10.3389/fpsyg.2022.1058177](https://doi.org/10.3389/fpsyg.2022.1058177) (PubMed) | Revisión y metaanálisis, 26 publicaciones; todas con riesgo de sesgo moderado a alto | Débil–moderada | No hace falta visor; una pantalla es "inmersión media". No prometer efectos clínicos |
| 2 | Naturaleza en VR frente a imágenes planas de naturaleza: sin diferencias significativas en ansiedad (5 estudios), ánimo (3) y estrés (4) | Hubbard et al. 2025, *Appl Psychol Health Well Being*, [10.1111/aphw.70060](https://doi.org/10.1111/aphw.70060) (PubMed) | Revisión y metaanálisis, 24 estudios, 1 419 universitarios; 2 de calidad "buena" | Débil | Respalda que una pantalla basta. Población joven, no mayor |
| 3 | Las intervenciones basadas en la naturaleza (senderismo, jardines, VR, sonidos de bosque) tienen impacto positivo en la salud de mayores | Catissi et al. 2024, *Int J Environ Res Public Health*, [10.3390/ijerph21010112](https://doi.org/10.3390/ijerph21010112) (PubMed) | Mapa de evidencia, 12 revisiones o ensayos | Débil–moderada, heterogénea | Apoya la intuición, no un efecto de nuestro formato |
| 4 | En mayores institucionalizados con visor, importa elegir el contenido, sobre todo si evoca recuerdos; hay efectos adversos posibles | Martinez et al. 2025, *Geriatr Psychol Neuropsychiatr Vieil*, [10.1684/pnv.2025.1239](https://doi.org/10.1684/pnv.2025.1239) (PubMed) | Revisión narrativa, 10 estudios | Débil | "Antes y ahora" y recuerdos de Calp son contenido bien elegido para vecinos mayores |
| 5 | Mayores en residencia toleraron bien el visor: 92 % completó 3 sesiones; 61 % sin síntomas; la ansiedad bajó | Rmadi et al. 2023, *Front Public Health*, [10.3389/fpubh.2023.1163484](https://doi.org/10.3389/fpubh.2023.1163484) (PubMed) | 36 participantes, edad media 89 | Débil (preliminar) | Un visor puede tolerarse, pero la nuestra es pantalla |
| 6 | Mareo y edad: resultados contrarios. Más mareo en jóvenes que en mayores (N = 111) frente a vulnerabilidad de mayores en un simulador de carretilla | Pöhlmann y Keshavarz 2026, *Exp Brain Res*, [10.1007/s00221-026-07367-x](https://doi.org/10.1007/s00221-026-07367-x); Islam y Lim 2025, *IISE Trans Occup Ergon Hum Factors*, [10.1080/24725838.2025.2556699](https://doi.org/10.1080/24725838.2025.2556699) (PubMed) | Estudios únicos | Débil, contradictoria | No suponer nada por edad: ofrecer opciones y medir |
| 7 | Los efectos adversos son más frecuentes con visor que con sistemas de escritorio | Simón-Vicente et al. 2024, *Neurología*, [10.1016/j.nrleng.2022.04.007](https://doi.org/10.1016/j.nrleng.2022.04.007) (PubMed) | Revisión, 10 estudios, 416 pacientes, edad media 24,5 | Débil | Mantener pantalla plana |
| 8 | Hacer ejercicio al aire libre se disfruta más que su versión virtual | Lahart et al. 2019, *Int J Environ Res Public Health*, [10.3390/ijerph16081352](https://doi.org/10.3390/ijerph16081352) (PubMed) | Revisión, 28 ensayos; calidad baja | Débil | Posicionar la experiencia como complemento de la visita, no sustituto |
| 9 | Personas con movilidad limitada querían usar la VR para evadirse, pero **la consideraron inaccesible en la práctica** | Hardwick 2024, tesis doctoral, Swansea ([Cronfa](https://cronfa.swan.ac.uk/Record/cronfa66921)) | Cualitativo (IPA), 12 participantes | Débil pero relevante | Apoya evitar el visor y cuidar el control, la ergonomía y la guía en texto |
| 10 | Marco conceptual de aceptación de VR turística por personas con discapacidad | Iftikhar et al. 2023, *Leisure Studies*, [10.1080/02614367.2022.2153903](https://doi.org/10.1080/02614367.2022.2153903) | Conceptual, sin datos | Muy débil | Solo referencia teórica |
| 11 | Visitas virtuales como evaluación de accesibilidad previa a un viaje (personas con movilidad limitada) | Chi, Sha y Zhang 2023, ACM, [10.1145/3587281.3587292](https://doi.org/10.1145/3587281.3587292) | Solo se verificó el título | No valorable | Idea: la app como "ver antes de ir" |
| 12 | Más presencia pero **menos aprendizaje** y más carga cognitiva en VR inmersiva frente a escritorio (presencia d = 1,30; aprendizaje d = 0,80; carga EEG d = 0,59) | Makransky, Terkildsen y Mayer 2019, *Learning and Instruction* 60:225–236 (resumen en `B`; DOI no verificado) | Experimento, 52 universitarios; financiación parcial de Labster | Moderada, un estudio | Para escuelas: pantalla, tareas guiadas, poco ruido |
| 13 | Excursiones virtuales: la mayoría de estudios tienen muestras pequeñas o evalúan mal el aprendizaje; ayudan sobre todo a quien no puede viajar | Revisión STEM (Krause et al., póster 2019, `B`); Dost 2023, revisión de 37 estudios (`B`) | Revisiones | Débil | No comprometer resultados de aprendizaje; medir en un piloto |
| 14 | Discovery Tour: **no se halló evaluación formal**; hay anécdotas docentes y un piloto de 60 min | Ubisoft y prensa (`B`, `L`) | Anecdótico | Muy débil | Copiar el formato, no la promesa |

### Lo que no sabemos

- Si una caminata en pantalla de un sendero real mejora el bienestar, la preparación de una visita o el aprendizaje, y en cuánto.
- Si **personas con movilidad reducida** lo perciben útil o sustitutivo. No hay un estudio con ese perfil sobre experiencias de sendero en pantalla.
- Si el viaje rápido desorienta menos que un deslizamiento rápido en pantalla plana.
- Si los mayores prefieren voz narrada o texto.

### Piloto barato propuesto (no iniciado)

Tres grupos (un centro de mayores de Calp, un aula, una o dos personas con movilidad reducida), 20 minutos cada uno, en su propio dispositivo. Medir: tareas completadas sin ayuda ("Llévame a la cima", abrir una ficha), SSQ corto, una pregunta de utilidad percibida y una de "¿reconoces el lugar?". Es una ampliación de `docs/specs/002/pruebas-vecinos.md`.

---

## 5. Decisiones abiertas y tareas sugeridas (no iniciadas)

Decisiones que no se pueden tomar con las fuentes:

1. ¿Narración con voz en la primera versión, o texto? (§2.4, punto 2). Con voz hace falta además guion verificado y licencia de la voz.
2. ¿Se incluye *Oxalis* exótica en la fidelidad de invierno? Recomendado sí, con ficha que la marque como introducida.
3. ¿El calendario entra en la fase C (modos) o en D (guía en texto y PWA)? Es barato si la paleta ya existe; las tarjetas estacionales dependen de hechos nuevos.
4. ¿Se acepta pedir a observadores de iNaturalist permiso para fotos de peregrino, vencejo y palmito, o se fotografía?

Tareas sugeridas, sin empezarlas:

- Añadir a `content/facts.json` los hechos de fenología con estado `unverified` y fuente (iNaturalist API, Vertebrados Ibéricos, MITECO).
- Dar de alta en `content/sources.json` las fuentes nuevas de §6.
- Corregir en el contenido la etiqueta "collalba negra": es *Oenanthe leucura* (ya señalado en `sonido-licencias.md`).
- Ampliar `docs/specs/002/pruebas-vecinos.md` con los tres perfiles de §4.
- Una prueba de conformidad con axe y un recorrido con lector de pantalla cuando exista la ficha visible.

---

## 6. Fuentes

Propuesta de ID para `content/sources.json`. Lectura: `L` leída · `API` consulta a API abierta · `B` solo resumen de búsqueda. Acceso: 2026-10-12.

### 6.1 Accesibilidad

| ID | URL | Lectura | Nota |
|---|---|---|---|
| `gag-full-list` | https://gameaccessibilityguidelines.com/full-list/ | `L` | Listas Basic e Intermediate |
| `xag-guidelines` | https://learn.microsoft.com/en-us/gaming/accessibility/guidelines | `L` | Versión 3.2, 2023-06-08 |
| `xag-117` | https://devdocs.xbox.com/gaming/accessibility/xbox-accessibility-guidelines/117 | `L` | Visual distractions and motion settings |
| `xag-version-history` | https://learn.microsoft.com/en-us/xbox/accessibility/xag-version-history | `L` | Lista de XAG 101–121 |
| `w3c-xaur` | https://www.w3.org/TR/xaur/ | `L` | Nota, 2021-08-25 |
| `boe-rd-1112-2018` | https://www.boe.es/buscar/act.php?id=BOE-A-2018-12699 | `L` | Texto consolidado informativo |
| `eurlex-2021-1339` | https://eur-lex.europa.eu/eli/dec_impl/2021/1339/oj | `B` | EN 301 549 V3.2.1 |
| `nda-en301549` | https://nda.ie/news/en301549-published | `L` | V4.1.1, fechas |
| `w3c-wcag22-new` | https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/ | `L` | Criterios nuevos de 2.2 |
| `w3c-wcag-2-3-3` | https://www.w3.org/WAI/WCAG21/Understanding/animation-from-interactions.html | `L` | 2.3.3 y técnica C39 |
| `w3c-wcag-2-2-2` | https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html | `L` | 2.2.2 |
| `calp-plan-accesibilidad` | https://www.calpe.es/va/node/3208 | `L` | Plan de Accesibilidad Turística |

### 6.2 Referentes y comodidad

| ID | URL | Lectura |
|---|---|---|
| `komoot-4-ways` | https://www.komoot.com/adventure-hub/4MasE6DPzRyY4tHUgDqF6w/4-ways-to-use-komoot-during-your-adventure | `L` |
| `alltrails-wrong-turn` | https://support.alltrails.com/hc/en-us/articles/37213407013908-Wrong-turn-alerts | `B` |
| `gaia-guide-cmc` | https://carolinamountainclub.org/view/assets/uploadedAssets/GaiaGuide.pdf | `B` |
| `google-hidden-worlds` | https://blog.google/company-news/outreach-and-initiatives/arts-culture/explore-hidden-worlds-national-parks/ | `L` |
| `nps-zion-virtual-hikes` | https://www.nps.gov/zion/learn/photosmultimedia/virtual-hikes.htm | `B` |
| `ubisoft-discovery-tour-school` | https://www.ubisoft.com/en-sg/game/assassins-creed/news/2Qdtl7NjlUPC5XO2JkJdLo/what-happens-when-students-and-teachers-go-handson-with-discovery-tour-ancient-greece | `L` |
| `firewatch-ui` | https://gamedeveloper.com/design/how-firewatch-s-ui-enhances-player-immersion | `B` |
| `dear-esther-wiki` | https://en.wikipedia.org/wiki/Dear_Esther | `B` |
| `everest-vr-roadtovr` | https://roadtovr.com/?p=165207 | `B` |
| `virtual-photography-wiki` | https://en.wikipedia.org/wiki/Virtual_photography | `L` |
| `acta-ludologica-photomodes` | https://actaludologica.com/the-creative-remediation-and-promotional-use-of-photographic-modes-in-digital-games/ | `L` (resumen) |
| `nvidia-photo-mode` | https://www.nvidia.com/en-sg/geforce/news/photo-mode-revolutionizing-game-screenshots/ | `B` |
| `meta-locomotion-comfort` | https://developers.meta.com/horizon/design/locomotion-comfort-usability/ | `L` |
| `habgood-2018` | https://shura.shu.ac.uk/18594 (IEEE VR 2018, 10.1109/VR.2018.8446130) | `B` |
| `fernandes-feiner-2016` | https://www.sciencedaily.com/releases/2016/06/160614121922.htm | `B` (prensa; el artículo no se leyó) |

### 6.3 Calendario natural

| ID | URL | Lectura |
|---|---|---|
| `inat-api` | https://api.inaturalist.org/v1/observations/histogram y `/species_counts` (plantilla en el anexo A) | `API` |
| `gbif-api` | https://api.gbif.org/v1/occurrence/search (plantilla en el anexo A) | `API` |
| `commons-api` | https://commons.wikimedia.org/w/api.php (búsqueda en espacio de nombres de archivos) | `API` |
| `flora-vascular-lentisco` | https://www.floravascular.com/index.php?spp=Pistacia+lentiscus | `L` |
| `vi-larus-michahellis` | https://www.vertebradosibericos.org/aves/larmic.html | `L` |
| `vi-falco-peregrinus` | https://www.vertebradosibericos.org/aves/reproduccion/falperre.html | `L` |
| `vi-phalacrocorax-aristotelis` | https://www.vertebradosibericos.org/aves/phaari.html | `L` |
| `vi-oenanthe-leucura` | https://www.vertebradosibericos.org/aves/reproduccion/oenleure.html | `L` |
| `vi-monticola-solitarius` | https://www.vertebradosibericos.org/aves/reproduccion/monsolre.html | `L` |
| `miteco-vencejo-palido` | https://www.miteco.gob.es/content/dam/miteco/es/biodiversidad/publicaciones/especies/vencejo__palido_tcm30-99935.pdf | `B` |
| `miteco-gaviota-audouin` | https://www.miteco.gob.es/content/dam/miteco/es/biodiversidad/publicaciones/especies/gaviota_de_audouin_tcm30-100059.pdf | `B` |
| `carm-aves-marinas-2017` | https://conocimientoabierto.carm.es/jspui/bitstream/20.500.11914/3822/1/Las%20aves%20marinas%20en%20la%20Regi%c3%b3n%20de%20Murcia.%20Censo%202017.pdf | `B` |
| `calanques-cormoran` | https://calanques-parcnational.fr/fr/cormoran-huppe-de-mediterranee | `B` |
| `miteco-silene-atlas` | https://www.miteco.gob.es:443/content/dam/miteco/es/biodiversidad/temas/inventarios-nacionales/silene_hifacensis_tcm30-99628.pdf | `B` ("caméfito de floración primaveral y fructificación estival") |
| `floraveg-pseudoscabiosa` | https://floraveg.eu/en/factsheet/default/102274 | `B` (nivel de género) |
| `eunis-eszz16006` | https://eunis.eea.europa.eu/sites/ESZZ16006 | `B` |

### 6.4 Evidencia

| ID | URL o DOI | Lectura |
|---|---|---|
| Artículos de PubMed de §4 (filas 1–8) | DOI en la tabla; metadatos obtenidos de PubMed | `L` (resumen) |
| `hardwick-2024` | https://cronfa.swan.ac.uk/Record/cronfa66921 | `L` |
| `iftikhar-2023` | https://doras.dcu.ie/33013/ | `L` |
| `chi-2023` | https://par.nsf.gov/biblio/10532879 | `L` (solo título) |
| `makransky-2019` | https://imotions.com/blog/adding-immersive-virtual-reality-to-a-science-lab-simulation-causes-more-presence-but-less-learning | `B` |
| `vft-stem-review` | https://serc.carleton.edu/earth_rendezvous/2019/program/posters/wednesday/220505.html | `B` |
| `vft-dost-2023` | https://papers.iafor.org/?p=68693 | `B` |

---

## 7. Conflictos y no verificado

| Dato | Situación | Qué hacer |
|---|---|---|
| Colonias de gaviota de Audouin "en el Penyal" | Sin fuente; el MITECO sitúa las colonias en otros sitios | No mostrarla como colonia |
| Cigarras en el Penyal | Sin registro abierto dentro del parque | Preguntar al parque o al usuario; hasta entonces, ambiente estival con confianza baja |
| Halcón de Eleonora | 4 registros agosto–septiembre; el Ayuntamiento lo menciona, la GVA no | Mantener `unverified` |
| Cormorán moñudo criando en Ifac | Sin dato de cría ni de parejas | No dar fechas de cría para Ifac; presencia sí |
| Fecha de llegada y partida del vencejo pálido | Resumen de una ficha MITECO que no se pudo leer | Releer el PDF |
| Fenología de las rupícolas amenazadas | N ≤ 3 y 0 observaciones en el parque | Pedirla al parque |
| Datos de GBIF del cormorán | Total 283, meses suman 258 | 25 registros sin mes; no cambia el patrón |
| Suma de meses del peregrino y la gaviota patiamarilla | 43 frente a 42; 1 791 frente a 1 789 | Sin efecto práctico |
| Recuentos y sumas leídos por el resumidor de WebFetch | Pueden contener errores de transcripción | Repetir con las plantillas del anexo A antes de citar cifras en una ficha |
| EN 301 549 V4.1.1 vinculante el 2026-12-16 | Fecha prevista; otra fuente hablaba de octubre | Comprobar en el DOUE |
| LCSP art. 126 | Texto no leído | Leerlo en el BOE si el Ajuntament contrata |
| Versión UNE de EN 301 549 V4.1.1 | No hallada | Preguntar a UNE/AENOR |
| Impacto educativo de Discovery Tour | Sin evaluación formal localizada | No prometerlo |
| Tiempo y distancia oficiales de la Ruta Roja | Conflicto ya recogido en `trail-length` y `trail-time` | El HUD cita su método y enseña el conflicto |
| Evidencia de viñeta y teleport | Solo VR con visor | Opción apagada y prueba con mayores |
| Disponibilidad actual de Hidden Worlds y Expeditions | La página es de 2016 | No contar con ello |

---

## Anexo A. Consultas reproducibles

Todas se hicieron con WebFetch el 2026-10-12.

**iNaturalist, fenología mensual (floración: `term_value_id=13`; frutos: `14`)**

```
https://api.inaturalist.org/v1/observations/histogram?taxon_name=<Nombre científico>&date_field=observed&interval=month_of_year&quality_grade=research&term_id=12&term_value_id=13&nelat=40.0&nelng=4.5&swlat=37.6&swlng=-1.5
```

**iNaturalist, presencia en la caja del parque**

```
https://api.inaturalist.org/v1/observations?taxon_name=<Nombre científico>&quality_grade=research&swlat=38.630&swlng=0.060&nelat=38.646&nelng=0.085&per_page=0
```

**iNaturalist, fotos con licencia abierta** (se añadió `photo_license=cc0,cc-by` a la consulta anterior y la caja de Alicante norte: `nelat=38.85&nelng=0.25&swlat=38.35&swlng=-0.60`)

**iNaturalist, abundancia de plantas en la caja del parque**

```
https://api.inaturalist.org/v1/observations/species_counts?swlat=38.630&swlng=0.060&nelat=38.646&nelng=0.085&quality_grade=research&iconic_taxa=Plantae&per_page=120&locale=es
```

(270 especies; el resumidor leyó las 74 primeras.)

**GBIF, registros por mes en la caja de Calp**

```
https://api.gbif.org/v1/occurrence/search?geometry=POLYGON((0.02 38.60,0.13 38.60,0.13 38.67,0.02 38.67,0.02 38.60))&scientificName=<Nombre>&occurrenceStatus=PRESENT&limit=0&facet=month&facetLimit=12
```

(con `%20` por los espacios del polígono). Para las cigarras se usó el polígono de la caja del Levante-Baleares.

**Wikimedia Commons, licencias**

```
https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch=Penyal d'Ifac OR Peñón de Ifach&gsrnamespace=6&gsrlimit=40&prop=imageinfo&iiprop=extmetadata&iiextmetadatafilter=LicenseShortName|Artist&format=json
```

(los 40 primeros resultados; hay más).

Nota sobre nombres: iNaturalist resuelve `taxon_name` con sinonimia (*Rosmarinus officinalis* y *Salvia rosmarinus* dan el mismo taxón). GBIF trata *Phalacrocorax aristotelis* y *Gulosus aristotelis*, y *Sylvia undata* y *Curruca undata*, como sinónimos.
