# 003 — Entorno construido del Penyal d'Ifac y de la Ruta Roja

- Fecha: 2026-10-11. Trabajo de investigación; no se ha descargado nada en el repositorio ni se ha editado otro archivo.
- Idioma: castellano, para el equipo. Identificadores de fuente de `content/sources.json` y de hechos de `content/facts.json`.
- Fecha de consulta: todas las lecturas en directo son del **2026-10-11**. Las búsquedas que solo dieron fragmentos se marcan como "fragmento de búsqueda" y no como lectura completa.
- **Limitación de esta sesión:** los portales de la GVA (`parquesnaturales.gva.es`, `mediambient.gva.es`), `calpe.es`, `marqalicante.com`, `catastro.hacienda.gob.es`, `ovc.catastro.meh.es`, `web.archive.org` y `commons.wikimedia.org` no respondieron (ECONNREFUSED, DNS o HTTP 404). `curl` desde el sandbox tampoco llega. Por eso lo que sigue depende de copias, fragmentos de búsqueda y fuentes secundarias. Todo lo que no se ha leído se marca **[sin verificar]**.
- Nada de lo que sigue es una coordenada ni la ubicación de una planta de *Silene hifacensis*.

## Resumen (lo que cambia para el modelado)

1. **"El museo"**: hay dos candidatos claros y uno posible. El Centre d'Informació i de Visitants está en el acceso (a pie de sendero). El Museu d'Història de Calp está en el casco urbano, con piezas de la Pobla. No existe museo ni espacio de interpretación en la Pobla. Decide el usuario (ver §1 y §5).
2. **Lo construido en el acceso** es poco documentado. Tenemos el nombre y la dirección del centro, sus horarios y la existencia de aseos, fuentes y área recreativa (estos últimos por un fragmento de 2018). No tenemos planos, altura, materiales ni número de plazas de aparcamiento.
3. **El sendero** tiene túnel de 1918 (portales, roca pulida, dos cuerdas, plataforma de salida), mirador de Ponent con restos de muralla, mirador de Carabiners (ruinas), y vértice geodésico de tercer orden en la cima. Las dimensiones y los materiales de casi todo siguen sin fuente.
4. **Datos de geometría**: el Catastro tiene un servicio WFS y descargas ATOM por municipio (sin verificar el atributo de plantas). La cartografía del parque (PRUG 1993) no se ha podido leer.

---

## 1. "El museo"

### 1.1 Candidatos

| Candidato | Qué es | Dirección | Distancia al inicio de la Ruta Roja | Fuentes |
|---|---|---|---|---|
| **A. Centre d'Informació i de Visitants** ("Aula de la Natura") | Centro del parque: exposición (según la GVA, "la exposición del Centro de Visitantes"), información e inicio del sendero. Ocupa dos casas réplica inauguradas en 1992 (según `facts.json`, sin fuente). | C/ Illa de Formentera, s/n, 03710 Calp | Está en el inicio: el punto de partida del sendero | `gva-centro-visitantes` (fragmento de la copia IA 2026-08-28); spain.info (lectura 2026-10-11); `ecoticias` (2011, lectura 2026-10-11) |
| **B. Museu d'Història de Calp** (Casa de la Senyoreta) | Museo municipal de historia y arqueología. Casa del s. XVIII con 255 m² de salas, colección cronológica (Bronce del yacimiento de Cocentari; Iberia, con piezas de la ladera norte del Penyal), sala dedicada al vicus romano de Els Banys de la Reina y a la Pobla de Ifac, paneles y proyección audiovisual. | C/ Santísimo Cristo, 7, 03710 Calp | **No medida.** Está en el casco urbano, fuera del parque. | Fragmentos de búsqueda: calpe.es (`calpe.es/en/discover-calpe/museo-de-historia-y-arqueologia`, no leída), MACMA, agenda cultural de Calp (CTO_Junio), comunitatvalenciana.com |
| **C. La Pobla d'Ifac (sitio)** | No es museo. Yacimiento excavado por el MARQ; no hay espacio de interpretación ni restos visitables documentados [sin verificar]. Hay un proyecto de musealización anunciado por la Diputación. | — | Se ve desde el mirador de Ponent (`gva-ruta-roja`) | `gva-villa-ifac`, `marq-2024`; fragmentos de Alicante Plaza y MARQ (sin fecha de la noticia) |
| **D. Museu de Coleccionisme** (Torreó de la Peça, pl. de la Vila) | Museo de coleccionismo, **otro museo**. Citado aquí porque aparece en búsquedas con el de Historia. | Pl. de la Vila (casco antiguo) | No medida | Fragmento de búsqueda (comunitatvalenciana.com) |
| — | "Museu Fester": **no encontrado** en ninguna fuente. No se incluye. | — | — | — |

### 1.2 Lo que sabemos de cada uno

- **A. Centre d'Informació i de Visitants**
  - Nombre oficial en `gva-centro-visitantes` (`centre-name`). El mapa oficial lo rotula "Aula de la Natura" (`facts.json`, sin fuente); spain.info dice "Centro de Información o Aula de la Natura" (lectura 2026-10-11).
  - Horario (`centre-hours`, `gva-accesibilidad`): L–V 8:30–14:30; fines de semana y festivos 9:00–14:00. Coincide con una nota de 2018 vista en fragmento.
  - Un artículo de Ecoticias (2011) dice que la entrada a la exposición es gratuita y sin cola. Dato antiguo.
  - **Las dos casas réplica de 1992**: no hay fuente que las confirme. Lo más cercano es un artículo de *El Temps* de febrero de 1987 (fragmento de búsqueda, `eltemps.cat/documents/el-temps_1987_02_0137_0022_0023.pdf`). Describe dos casas en el peñón, una a medio derribar. Propone rehabilitar una como centro de estudios ecológicos. Es una propuesta de 1987, no prueba de una réplica. Wikipedia en catalán (lectura 2026-10-11, cita a sendasyleyendas.com) dice que a principios del s. XX se construyeron dos caminos por la vertiente norte y que uno "porta a la base, on s'hi van aixecar dos habitatges". **Hipótesis a confirmar**: las dos casas del acceso son las mismas que las de 1987. No se sabe qué replican.
- **B. Museu d'Història de Calp**
  - Horario **en conflicto** (fragmentos): la agenda del Ajuntament da invierno (oct–jun) martes–sábado 10:00–14:00 y 16:30–19:00; verano (jul–sep) miércoles–domingo 10:30–13:00 y 18:00–22:00. MACMA da verano 10:00–13:00 y 18:30–22:00, cerrado lunes y martes; invierno coincide con la agenda. Teléfono y correo del fragmento: +34 965 839 123, museo@ajcalp.es [sin verificar].
  - Precio de entrada: no encontrado.
  - Visitas guiadas: MACMA dice que no son posibles [fragmento].
- **C. Pobla d'Ifac**
  - Sin visitas regulares y musealización prevista: `pobla-visits` (ya "sin confirmar" en `facts.json`).
  - Fragmento de Alicante Plaza: la Diputación planea la musealización "en esta legislatura"; sin fecha de la noticia ni presupuesto. El fragmento de MARQ dice que la Diputación cede unas 50 piezas de la Pobla al nuevo Museu d'Història de Calp (sin fecha leída). **Conflicto de fechas**: la noticia de la musealización menciona a Carlos Mazón como presidente, y la de la cesión no tiene fecha visible. Los dos datos pueden ser de años distintos.
  - MARQ 2024 (`marq-2024`) dice que las excavaciones identifican un cobertizo del s. XIV. No se ha leído el plan del sitio.

### 1.3 Conclusión (sin decidir)

- Si con "museo" el usuario se refiere a **algo que se ve al llegar al Penyal**, lo más probable es el **Centre d'Informació** (A): es el edificio del acceso y tiene una exposición. Pero **no tenemos ninguna foto ni plano** para saber cómo se ve.
- Si se refiere a **un museo de verdad, con piezas**, es el **Museu d'Història de Calp** (B). Es el que tiene piezas de la Pobla.
- La Pobla (C) no es un museo. Si el usuario pregunta "dónde está el museo de la Pobla", la respuesta honesta es que no hay.
- **Qué confirmar con el usuario**: (1) ¿a qué edificio se refiere? (2) ¿ha visitado la exposición del centro o el museo de Calp? (3) ¿quiere modelar el edificio exterior, el interior o ninguno ahora?

---

## 2. Elementos construidos en el acceso y a lo largo de la ruta

Leyenda: **V** = verificado con fuente leída; **F** = solo fragmento de búsqueda; **N** = sin fuente encontrada.

### 2.1 Acceso y tramo piloto (Centro → ~420 m tras el torno)

| Elemento | Qué sabemos | Forma, materiales, dimensiones | Fuente | Estado |
|---|---|---|---|---|
| Centro de visitantes (edificio) | Dos casas réplica (`facts.json`) | Desconocidos | `gva-centro-visitantes` (F) | **N** en dimensiones, altura, materiales |
| Aseos | Hay aseos (nota de 2018, fragmento) | Desconocidos | Fragmento de búsqueda (fuente sin URL verificada) | F |
| Fuentes de agua | Solo al inicio (`access-safety`) | — | `gva-recomendaciones`, `gva-guia` | V |
| Área recreativa, merenderos | Hay merenderos y área recreativa (nota de 2018) | Desconocidos | Fragmento | F |
| Aparcamiento | Nota de 2018 (fragmento): solo para discapacitados. **Conflicto** con las reseñas de campers, no verificado. Reseñas: explanada de tierra y gravilla, cercada, pequeña, con pendiente, se llena en temporada alta | Gravilla, cercado, pendiente. Plazas: **N** | Fragmentos de búsqueda (sin fuente oficial) | **N** (plazas y superficie) |
| Calle de acceso | C/ Illa de Formentera, s/n (dirección del centro) | — | spain.info (V) | El nombre de la vía de acceso al aparcamiento: **N** |
| Acceso en coche | AP-7 y N-332 hasta Calpe | — | es.wikipedia Peñón de Ifach (V) | V |
| Torno y control de reserva | Reserva obligatoria, control de aforo (`access-booking`, `access-capacity`) | Ubicación del torno: **N** | `gva-park-home`, `gva-guia` | Ubicación **N** |
| Escalones con pasamanos (30 según OSM) | Dato del equipo (OSM), no lo hemos leído | — | OSM (tech lead) | **[sin verificar]** |
| Senda inicial | Camino hasta el túnel; más sencillo que el tramo posterior (fragmento) | Superficie: **N** (¿piedra, hormigón, tierra?) | Fragmento | **N** |
| Señalización e información | Panel y centro de información | Diseño: **N** | `gva-centro-visitantes` | **N** |

### 2.2 Resto de la ruta

| Elemento | Qué sabemos | Forma, materiales, dimensiones | Fuente | Estado |
|---|---|---|---|---|
| Restos ibéricos (parada oficial) | Lista oficial (`trail-stops`). Ubicación y restos: **N**. Hay material ibérico procedente de la ladera norte en el museo de Calp | — | `gva-ruta-roja` (V para la lista); museo de Calp (F) | Ubicación **N** |
| "Pinos tombats" (pinos caídos) | Parada oficial (`trail-stops`). Lo que es **N**; un blog lo interpreta como juego de palabras, no lo confirmamos | — | `gva-ruta-roja` (V para el nombre) | **N** |
| Área de descanso | Parada oficial | Banco, sombra: **N** | `gva-ruta-roja` | **N** |
| Mirador de Ponent | Vistas de la costa; desde aquí se ve la muralla de la Pobla (`pobla-viewpoint`). Barandilla: **N** | Restos de muro medieval (MACMA, F) | `gva-ruta-roja`, `macma-ruta` | Barandilla: **N** |
| Mirador del Botànic Cavanilles | Parada oficial. Ningún dato más | — | `gva-ruta-roja` | **N** |
| Subida al túnel | Tramo de roca y escalones (no verificado) | — | — | **N** |
| **Túnel** | 1918, por iniciativa de Vicente Paris Morlá para salvar la pared norte (`tunnel-built`). Longitud: 50 m (GVA folleto/Ruta Roja), 30 m (Ajuntament), **49,2 m (OSM, medición nuestra)**; un blog habla de unos 100 m (F, no fiable). Roca pulida y resbaladiza, dos cuerdas de apoyo, plataforma de salida (`tunnel-condition`). Sección y altura de bóveda: **N** | Roca natural, sin muros de obra visibles en fuentes | `gva-folleto`, `gva-ruta-roja`, `calp-penon`, `osm-way-26330275` | **Conflicto** en longitud. La sección: **N** |
| Bifurcación | Punto de bifurcación tras el túnel (`carabiners-what`) | — | `gva-ruta-roja` | V (lugar), **N** (forma) |
| Gaviota patiamarilla | Puede ser agresiva cerca de la bifurcación en primavera (`gull-breeding`) | — | `gva-fauna`, `gva-folleto` | V |
| Mirador de Carabiners | Ruinas de una plataforma de vigilancia de carabineros (`carabiners-what`). Medidas y materiales: **N** | Ruinas de obra; no hay plano | `gva-ruta-roja`, `gva-folleto`, `macma-ruta` | Forma **N** |
| Vista al mar desde Carabiners | Vistas al mar (MACMA, F) | — | Fragmento Barceló (F) | F |
| Cima (vértice geodésico) | Vértice geodésico de tercer orden (`summit-vertex`). Altitud **en conflicto** (332 m oficial; 325,8 m CV05; 328,07 m LiDAR, `summit-altitude`). Hay una ficha del IGN de un vértice "Mirador" (077051, ETRS89) que **no sabemos si es la cima** (F) | Estructura del vértice (altura, mástil, hito): **N** | `gva-ruta-roja`, `icv-cv05`, `icv-lidar-2016`; IGN (F) | Forma **N** |
| Ibiza desde la cima | No se confirma desde la cima; sí desde la plataforma del túnel (`ibiza-view`) | — | `gva-folleto` | V (la plataforma) |

### 2.3 La Pobla d'Ifac (restos y lo visible)

| Elemento | Dato | Fuente | Estado |
|---|---|---|---|
| Conjunto | Más de 70.000 m², más de 800 m de muralla, 11 torres, 3 puertas (`pobla-size`) | `ua-pobla` (V) | Verificado en fuente secundaria; **el plan del MARQ no se ha leído** |
| Muralla de Ponent y muralla Norte | Excavadas y documentadas (informe MARQ 2008) | `marq-2008` (**no leído**, 404/ECONNREFUSED) | **[sin verificar]** |
| Iglesia | Fecha en conflicto (1344 o 1320–1340, `pobla-church-date`). Forma y dimensiones: **N** | `gva-villa-ifac`, `marq-2008` | Conflicto; dimensiones **N** |
| Puerta del oeste | Hallazgo confirmado (Alicante Plaza, fragmento) | Alicante Plaza (F) | F |
| Casas, calles, cobertizo del s. XIV | Hallazgo de cobertizo (`marq-2024`) | `marq-2024` (V, lectura de la nota) | V |
| Materiales (piedra, mortero, tapial) | **N** | — | **N** |
| Ruinas visibles desde el sendero | La muralla se ve desde Ponent (`pobla-viewpoint`). Otras ruinas en los miradores: Barceló dice que algunos miradores se hicieron sobre las antiguas murallas (F, guía comercial) | `gva-ruta-roja`; Barceló (F) | V (Ponent), F (resto) |

### 2.4 Otros elementos visibles desde la base (sin fuente sólida)

| Elemento | Estado |
|---|---|
| Puerto deportivo, lonja, Club Náutico al pie | **N** en fuentes leídas. Pedido por el usuario; no lo hemos podido verificar |
| Casas de la base del peñón | es.wikipedia (lectura 2026-10-11, sección Flora): "la zona en torno a las casas de la base del peñón", sin más datos. Es la misma pregunta que el edificio del centro (ver 1.2) |

### 2.5 Fotos de referencia

- **Wikimedia Commons**: no accesible desde esta sesión (404 y búsqueda sin resultados de Commons). **Pendiente**. Hay que buscar "Penyal d'Ifac", "Peñón de Ifach", "Pobla d'Ifac", "Mirador de los Carabineros" y verificar la licencia de cada archivo (CC BY o CC0 para referencia; nunca como textura de un archivo CC BY-SA).
- **Mapillary**: no revisado. Hay que comprobar la cobertura en el sendero y la fecha de cada captura.
- **Fotos oficiales GVA/Ajuntament**: no accesibles. Si se usan, solo como referencia visual, no como textura.
- **Fotos del propio usuario (de Calp)**: la fuente más útil. Son "ojo local". Pueden servir de referencia con permiso y con la fecha.

---

## 3. Fuentes de geometría

| Fuente | Qué aporta | Acceso (2026-10-11) | Licencia | Estado |
|---|---|---|---|---|
| **Catastro, servicio INSPIRE de edificios (BU) WFS** | Edificios, partes de edificio y otras construcciones. Atributo de plantas: **sin verificar** (no se ha leído el DescribeFeatureType) | `http://ovc.catastro.meh.es/INSPIRE/wfsBU.aspx?` (fragmento de búsqueda, no probado: sandbox sin red) | Varias fuentes secundarias: CC BY 4.0 en el catálogo CODSI y uso de Catastro para el original. **Conflicto** en los metadatos | **[sin verificar]** |
| **Catastro, descarga ATOM por municipio** | Fichero GML completo de Calp (la descarga masiva recomendada; actualización dos veces al año según fragmento) | `http://www.catastro.minhap.es/INSPIRE/buildings/ES.SDGC.BU.atom.xml` (fragmento) | Igual | **[sin verificar]** |
| **Catastro, parcelas** | Límites de parcela del Centro y del aparcamiento | No revisado | Igual | Pendiente |
| **PRUG 1993** (`dogv-prug-1993`) | Zonificación, accesos y previsiones de obra del parque | DOGV (2026-10-10 según `sources.json`; hoy no hay red) | Público (DOGV) | **Pendiente**: la lectura de 2026-10-11 falló |
| **Plano del MARQ de la Pobla** | Planta de excavación | No encontrado en público; el informe 2008 (`marq-2008`) es PDF y no se ha leído | Por verificar | **N** |
| **Plan director de la Pobla / Baños de la Reina** | Anunciado por la Diputación y el MARQ (fragmento) | No publicado en las fuentes leídas | — | **N** |
| **IGN, datos geodésicos** | Ficha de vértice(s) con coordenadas ETRS89; ver si el vértice "Mirador" 077051 es la cima | `datos-geodesia.ign.es/Red_Geodesica/Hoja0770/077051.pdf` (fragmento) | Público (IGN) | Por verificar si es la cima |
| **ICV CV05 y LiDAR 2016** | Ya en `sources.json` (cota del punto de cima) | Ya citadas | Ya citada | Lo lleva el tech lead |
| **OSM** | Tags (escalones, túnel, vías) | Lo lleva el tech lead | ODbL | No duplicamos |

Notas para el modelado:

---

## 4. Propuesta de puntos de interés (POI)

Tipos: **Lugar** = anclado a una posición (hay que confirmarla). **Tema** = tarjeta sin posición (o con zona, no con punto).

### 4.1 Acceso (Centro → torno)

| POI | Tipo | Lo que se puede decir con fuente | Falta |
|---|---|---|---|
| Centre d'Informació i de Visitants | Lugar | Nombre oficial, horario, dirección, reserva, exposición (`centre-name`, `centre-hours`, `access-booking`) | Posición exacta, aspecto, historia de las casas de 1992 |
| Aparcamiento | Lugar | Hay aparcamiento; de tierra y gravilla (reseñas) | Plazas, superficie oficiales, ubicación |
| Torno y control de reserva | Lugar | Reserva obligatoria, 300 al día (`access-capacity`) | Ubicación del torno |
| Fuentes y aseos | Lugar | Fuentes al inicio (`access-safety`); aseos (fragmento) | Ubicación, estado |

### 4.2 Tramo piloto (Centro → ~420 m)

| POI | Tipo | Lo que se puede decir | Falta |
|---|---|---|---|
| Mirador de Ponent | Lugar | Vistas de la costa; desde aquí se ve la muralla de la Pobla (`pobla-viewpoint`); muro medieval (`macma-ruta`) | Posición; barandilla |
| Restos ibéricos | Lugar | Parada oficial (`trail-stops`) | Qué queda y dónde |
| Pinos tombats | Lugar | Parada oficial (`trail-stops`) | Qué son |
| Área de descanso | Lugar | Parada oficial | Banco, sombra |
| La Pobla d'Ifac (vista) | Tema (anclado al mirador de Ponent) | Cronología (`pobla-founding`, `pobla-destruction`), tamaño (`pobla-size`), excavación (`pobla-excavation`) | Dato de fecha de la iglesia (conflicto) y de las visitas (`pobla-visits`) |

### 4.3 Subida y túnel

| POI | Tipo | Lo que se puede decir | Falta |
|---|---|---|---|
| Túnel | Lugar | 1918 (`tunnel-built`); roca pulida, dos cuerdas, plataforma de salida (`tunnel-condition`); no seguir con lluvia o niebla (`access-safety`) | Longitud oficial (conflicto: 30/50/49,2 m) |
| Plataforma de salida del túnel | Lugar | Vista de Ibiza en días muy claros (`ibiza-view`) | Medidas, materiales |
| Mirador del Botànic Cavanilles | Lugar | Nombre oficial (`trail-stops`) | Todo lo demás |

### 4.4 Bifurcación y ramal sur

| POI | Tipo | Lo que se puede decir | Falta |
|---|---|---|---|
| Bifurcación | Lugar | Punto donde se separa el ramal de Carabiners; gaviota agresiva en primavera (`gull-breeding`) | Posición |
| Mirador de Carabiners | Lugar | Ruinas de una plataforma de vigilancia de carabineros (`carabiners-what`) | Dimensiones, fecha de construcción, planos |
| Gaviota patiamarilla | Tema (zona de la bifurcación) | Cría en el parque; agresiva en primavera (`gull-breeding`) | No dar nidos |
| Halcón peregrino | Tema | Cría en el parque; escalada prohibida en caras N y NO de abril a junio (`falcon-breeding`, `access-climbing-ban`) | Número de parejas (`bird-pair-counts`, sin verificar) |

### 4.5 Cima

| POI | Tipo | Lo que se puede decir | Falta |
|---|---|---|---|
| Vértice geodésico | Lugar | Tercer orden (`summit-vertex`); altitud en conflicto (`summit-altitude`) | Forma del vértice; confirmación de posición con el IGN |
| Vista de la cima | Tema | Ibiza no se confirma desde la cima (`ibiza-view`) | Qué se ve, con fuente |

### 4.6 Temas sin posición (tarjetas)

| Tema | Tipo | Lo que se puede decir | Cuidado |
|---|---|---|---|
| *Silene hifacensis* | Tema | Nombres, categorías en conflicto, ciclo, población restablecida (`silene-*`) | **No mostrar ninguna ubicación de planta**; no decir "aquí crece" |
| Flora rupícola (Teucrium hifacense, Centaurea rouyi, …) | Tema | `flora-rupicola` | Sin localizar |
| Geología (calizas del Eoceno, tómbolo, nummulites) | Tema | `park-geology` (**conflicto**: GVA frente a Ajuntament) | Mostrar las dos versiones |
| Salinas de Calp | Tema, fuera del parque | Antigua laguna de 18,76 ha, fuera de los límites (`salinas`) | Es fuera del parque; no mezclar |

---

## 5. Preguntas abiertas

### 5.1 Para el usuario (conocimiento local)

1. ¿Qué "museo" quieres decir: el edificio del centro al inicio, el Museu d'Història de Calp, o la Pobla?
2. ¿Has estado dentro de la exposición del centro? ¿Qué se ve? ¿Cómo son las dos casas (color, altura, pared de piedra o de enlucido)?
3. ¿Hay aparcamiento con plazas marcadas? ¿Dónde está y de qué material es?
4. ¿Dónde está el torno y la caseta de reserva? ¿Hay escalones, barandilla, pasamanos al empezar?
5. ¿El Mirador de Ponent está dentro del tramo piloto (decide la variante A o B de la ficha)?
6. ¿Tienes fotos propias del acceso y del túnel con fecha? Sirven como referencia de modelado.
7. ¿Hay algo visible en la base que no aparezca en esta lista (puerto, lonja, Club Náutico)?

### 5.2 Para el parque (GVA, Junta Rectora)

1. Plano o descripción del edificio del Centre d'Informació: año de construcción, plantas, materiales, relación con las casas de 1992 (y qué replican).
2. Número de plazas del aparcamiento, superficie y regulación (la nota de 2018 dice "solo discapacitados"; ¿sigue vigente?).
3. Ubicación del torno de control y del punto de reserva.
4. Longitud oficial del túnel (30, 50 o 49,2 m).
5. Estado del acceso a la Pobla: visitas hoy, plan de musealización, fecha, y si existe un plano público de la excavación.
6. Si el vértice "Mirador" del IGN (077051) es la cima.
7. Si el PRUG de 1993 tiene una zonificación cartográfica publicada en formato digital.
8. Edad mínima para pasar el túnel (16–18 años acompañados, o 18 años: conflicto en `access-minors-past-tunnel`).
9. Horario en vigor del centro (confirmar la nota de 2018 y la copia IA).

---

## 6. Fuentes

### 6.1 Ya en `content/sources.json` (usadas)

| ID | URL | Acceso | Nota |
|---|---|---|---|
| `gva-centro-visitantes` | https://parquesnaturales.gva.es/es/web/pn-penyal-d-ifac/centro-de-visitantes | 2026-10-10 (copia IA 2026-08-28) | Portal caído hoy; no releído |
| `gva-accesibilidad` | https://parquesnaturales.gva.es/es/web/pn-penyal-d-ifac/accessibilitat-al-parc | 2026-10-10 (copia IA 2026-08-28) | Horario |
| `gva-ruta-roja` | https://parquesnaturales.gva.es/va/web/pn-penyal-d-ifac/ruta-roja-descripcion | 2026-10-10 (copia IA 2022-08-08) | Paradas; **volver a comprobar en directo** |
| `gva-folleto` | https://parquesnaturales.gva.es/documents/80305041/83047539/38604-70929-Folleto/2a4650a0-c1e4-480c-84bb-1981248b3709?version=1.0 | 2026-10-10 | Sin fecha |
| `gva-recomendaciones` | https://parquesnaturales.gva.es/es/web/pn-penyal-d-ifac/recomendaciones-para-la-visita | 2026-10-10 (copia IA 2026-04-16) | Seguridad |
| `gva-villa-ifac` | https://parquesnaturales.gva.es/es/web/pn-penyal-d-ifac/la-villa-de-ifac | 2026-10-10 (copia IA 2025-09-12) | Pobla |
| `gva-proyecto-ifac` | https://parquesnaturales.gva.es/es/web/pn-penyal-d-ifac/proyecto-ifac | 2026-10-10 (copia IA 2026-02-16) | Pobla, excavación |
| `gva-historia` | https://parquesnaturales.gva.es/es/web/pn-penyal-d-ifac/historia | 2026-10-10 (copia IA 2025-11-11) | Túnel 1918 |
| `gva-fauna` | https://parquesnaturales.gva.es/es/web/pn-penyal-d-ifac/fauna | 2026-10-10 (copia IA 2026-04-11) | Gaviota, halcón |
| `gva-guia` | https://parquesnaturales.gva.es/documents/80305041/172756741/Gu%C3%ADa+Castellano+web.pdf | 2026-10-10 | Guía |
| `gva-reservas` | https://www.tramita.gva.es/ctt-att-atr/asistente/iniciarTramite.html?tramite=CITA_PREVIA_PARQUES&version=2&idioma=es&idProcGuc=20328&idCatGuc=PR | 2026-10-10 | Reserva |
| `dogv-prug-1993` | https://dogv.gva.es/datos/1994/01/21/pdf/1994_830310.pdf | 2026-10-10 | **No leído hoy** |
| `marq-2008` | https://www.marqalicante.com/contenido/int_arqueologicas/74%20Penyal%20d%27Ifac.%20Proyecto%20IFAC.%20Sectores%20Muralla%20de%20Poniente%2C%20Muralla%20Norte%20e%20Iglesia%20%28Calp%29.pdf | 2026-10-10 | **No leído hoy** (ECONNREFUSED) |
| `marq-2024` | https://www.marqalicante.com/en/las-excavaciones-del-marq-en-el-yacimiento-medieval-de-la-pobla-difac-identifican-un-cobertizo-del-siglo-xiv/ | 2026-10-10 | Publicada 2024-08-28 |
| `ua-pobla` | https://web.ua.es/va/sicos/pobla-medieval-d-ifach.html | 2026-10-10 | Lectura de 2026-10-11 de la sección Història (sin dimensiones) |
| `calp-penon` | https://www.calpe.es/es/descubre-calpe/espacios-naturales/pe%C3%B1on-de-ifach | 2026-10-10 | **No leído hoy** (ECONNREFUSED) |
| `calp-pobla` | https://www.calpe.es/es/descubre-calpe/turismo-cultural/museos-y-monumentos/monumentos/la-pobla-d-ifac | 2026-10-10 | **No leído hoy** |
| `macma-ruta` | https://macma.org/turisme/ruta/ruta-penyal-difac | 2026-10-10 | **No leído hoy** (fragmento de búsqueda) |
| `osm-way-26330275` | https://www.openstreetmap.org/way/26330275 | 2026-10-10 | Túnel (tech lead) |
| `icv-cv05`, `icv-lidar-2016` | Ver `sources.json` | 2026-10-10 | Cima (tech lead) |

### 6.2 Nuevas (proponer su alta en `sources.json` antes de usarlas en la ficha)

| Propuesta de ID | URL | Acceso | Qué aporta | Tipo de lectura |
|---|---|---|---|---|
| `spain-info-penon-es` | https://www.spain.info/es/naturaleza/parque-natural-penon-ifach/ | 2026-10-11 | "Centro de Información o Aula de la Natura"; dirección C/ Illa de Formentera, s/n; acceso libre con recomendación de pasar por el centro; cierre nocturno | Lectura |
| `es-wikipedia-penon` | https://es.wikipedia.org/wiki/Peñón_de_Ifach | 2026-10-11 | 332 m; vértice de tercer orden; acceso AP-7 y N-332 | Lectura (secundaria) |
| `ca-wikipedia-penyal` | https://ca.wikipedia.org/wiki/Penyal_d%27Ifac | 2026-10-11 | Dos caminos del s. XX por la norte; túnel 1918; dos habitatges en la base (cita sendasyleyendas.com) | Lectura (secundaria) |
| `ecoticias-2011` | https://www.ecoticias.com/naturaleza/46925_medio-ambiente-regula-el-acceso-al-parc-natural-del-penyal-d-ifac-con-motivo-de-la-semana-santa | 2026-10-11 | Regulación 150 personas, 20 cada 15 min (publicado 2011-04-19; **obsoleto**) | Lectura |
| `eltemps-1987` | https://www.eltemps.cat/documents/el-temps_1987_02_0137_0022_0023.pdf | Fragmento de búsqueda, 2026-10-11 | Dos casas en el peñón en 1987; propuesta de centro de estudios | Fragmento |
| `calpe-museo-historia` | https://calpe.es/en/discover-calpe/museo-de-historia-y-arqueologia | Fragmento de búsqueda, 2026-10-11 | Museo, dirección, Pobla de Ifac en la sala | Fragmento (fetch falló) |
| `macma-museo-calp` | https://macma.org/tourism/heritage/museu-dhistoria-de-calp | Fragmento de búsqueda, 2026-10-11 | Horarios que difieren de la agenda municipal | Fragmento |
| `calp-agenda-cto` | https://calpe.es/sites/default/files/CTO_Junio%20_ing.pdf | Fragmento de búsqueda, 2026-10-11 | Horario de invierno y verano del museo | Fragmento |
| `marq-diputacion-piezas` | https://www.marqalicante.com/en/la-diputacion-de-alicante-cede-medio-centenar-de-piezas-de-la-pobla-de-ifach-al-nuevo-museu-dhistoria-de-calp/ | Fragmento, 2026-10-11 | 50 piezas de la Pobla al museo de Calp; fecha no leída | Fragmento |
| `alicanteplaza-musealizacion` | https://alicanteplaza.es/alicanteplaza/la-diputacion-proyecta-para-esta-legislatura-la-musealizacion-de-la-pobla-medieval-de-ifach | Fragmento, 2026-10-11 | Musealización en la legislatura, sin fecha ni presupuesto | Fragmento |
| `barcelo-penyal` | https://www.barcelo.com/guia-turismo/en/spain/alicante/things-to-do/penon-de-ifach/ | Fragmento, 2026-10-11 | Algunos miradores sobre murallas; altitud 337 m (conflicto) | Fragmento (guía comercial, baja prioridad) |
| `ign-geodesia-077051` | https://datos-geodesia.ign.es/Red_Geodesica/Hoja0770/077051.pdf | Fragmento, 2026-10-11 | Vértice "Mirador" ETRS89 (¿es la cima?) | Fragmento |
| `catastro-bu-inspire` | https://www.catastro.hacienda.gob.es/webinspire/index.html | No leído (ECONNREFUSED) | WFS BU y ATOM por municipio; licencia en conflicto | Fragmento de búsqueda |
| `catastro-bu-wfs-doc` | https://www.catastro.hacienda.gob.es/webinspire/documentos/inspire-bu-WFS_en.pdf | No leído (ECONNREFUSED) | Atributos; límites 4 km² y 5000 entidades | Fragmento |

---

## 7. Conflictos entre fuentes (listados todos)

| Dato | Versión A | Versión B | Versión C | Qué hacer |
|---|---|---|---|---|
| Longitud del túnel | 50 m (`gva-folleto`, `gva-ruta-roja`) | 30 m (`calp-penon`) | 49,2 m (OSM, medición propia); ~100 m (blog, fragmento) | Medir sobre el MDT o el LiDAR; mostrar rango |
| Horario del museo de Calp (verano) | 10:30–13:00 y 18:00–22:00, miércoles a domingo (agenda municipal) | 10:00–13:00 y 18:30–22:00, cerrado lunes y martes (MACMA) | — | Preguntar al museo |
| Aparcamiento | Solo para discapacitados (nota de 2018, fragmento) | Uso general con reseñas de explanada cercada (campers) | — | Preguntar al parque |
| Acceso a la cima: edad | 16–18 años acompañados (`gva-ruta-roja`) | No se permite a menores de 18 (`gva-recomendaciones`) | 18 años mínimo (blog, fragmento) | Ya en `facts.json`; no resolver aquí |
| Regulación de aforo | 300 al día y reserva (`gva-park-home`, `gva-guia`) | 150 simultáneos y 20 cada 15 min (ecoticias, 2011) | — | La de 2011 parece obsoleta; confirmar |
| Altitud de la cima | 332 m (oficial) | 337 m (Barceló, fragmento) | 325,8 m (CV05), 328,07 m (LiDAR) | Ya en `facts.json` (`summit-altitude`) |
| Fecha de las dos casas | 1992, réplicas (`facts.json`, nota sin fuente) | Casas existentes en 1987 (*El Temps*, fragmento) | — | Preguntar al parque |
| Fecha de la musealización de la Pobla | "En esta legislatura" (Alicante Plaza, sin fecha) | Cesión de 50 piezas al museo de Calp (MARQ, sin fecha) | — | Buscar la fecha de cada noticia |
| Licencia de datos de Catastro | CC BY 4.0 (catálogo CODSI, fragmento) | Uso de Catastro para el original y CC BY 4.0 solo en lo derivado (trabajo académico, fragmento) | — | Leer el texto vigente antes de usar |
| Tipo de vértice (IGN "Mirador") | No sabemos si es la cima | — | — | Consultar al IGN |

---


## Addendum del responsable técnico (11/10/2026)

Verificado después del informe, usando el relé NAT64 del proyecto: varios portales oficiales solo tienen IPv4.

- **Dos equipamientos, no uno.** La página del parque, en la copia de Internet Archive del 2026-08-28 (`gva-centro-visitantes`), dice que "el Centro de Información y el Centro de Visitantes están emplazados en la cara Norte del Penyal". Tienen un único horario y la dirección C/ Illa de Formentera, s/n.
  - Encaja con los dos edificios del inventario: OSM `way/26330271`, 651 m², etiquetado "Centro de Interpretación" (`tourism=museum`), y `way/26330272`, 483 m². Ver `003-inventario-datos-propios.md`.
  - **Sin verificar:** cuál de los dos edificios es cada equipamiento. La página no describe la exposición: su contenido son imágenes.
  - La web en vivo de la GVA no respondió ni siquiera por NAT64.
- **Catastro INSPIRE, edificios.** El servicio WFS responde por NAT64 (`ovc.catastro.meh.es/INSPIRE/wfsBU.aspx`, GetCapabilities 2.0.0) y publica `bu:Building`, `bu:BuildingPart` y `bu:OtherConstruction`.
  - Sus capacidades no declaran licencia.
  - La web del Catastro presenta un certificado que no valida con la cadena de confianza local, y no se ha forzado la conexión.
  - **Licencia sin verificar:** no se usa hasta leerla en la fuente.
- Los identificadores de datos que cita este informe (`tunnel-built`, `tunnel-condition`, `ibiza-view`, `carabiners-what`, `summit-vertex`, `salinas`…) existen en `content/facts.json` con estado `verified`. Los que faltan son fuentes nuevas que el propio informe propone dar de alta (§6.2).
